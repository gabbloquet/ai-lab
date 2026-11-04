"""Lancer une campagne de la 001 : chaque item d'un split, k fois, sur chaque variante.

Les serveurs se lancent à part, un par variante (le serveur Java, --lab.variant=intent|rest).
Chaque exécution est écrite dès qu'elle finit : un run interrompu reprend avec --run-id.

Le split test n'est accepté qu'avec --final, sur un dépôt sans modification non commitée ;
il n'affiche alors aucun résultat item par item (CLAUDE.md, discipline d'itération).

Exemple, cycle dev :
    PYDANTIC_AI_NO_BANNER=1 uv run --env-file .env python \\
        experiments/001-mcp-outils-par-intention/python/agent/scripts/run_campaign.py \\
        --split dev --intent-url http://127.0.0.1:8082/mcp --rest-url http://127.0.0.1:8083/mcp
"""

import argparse
import hashlib
import json
import math
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio
from scipy import stats

from ailab_evals.tool_selection import PairedScore, aggregate
from exp001_agent import loop
from exp001_agent.campaign import Record, run_campaign
from exp001_agent.golden import load_items
from exp001_agent.langfuse_setup import check_reachable, credentials
from exp001_agent.summary import summarize
from exp001_agent.tracing import NO_TRACING, LangfuseTracing, Tracer

ROOT = Path(__file__).resolve().parents[5]
EXPERIMENT = ROOT / "experiments/001-mcp-outils-par-intention"
GOLDENS = ROOT / "domains/magasin/golden/tool-selection"
DEFAULT_GOLDEN = "v2"
SPEC = "evals/spec/tool-selection/v1"
SYSTEM_PROMPT = EXPERIMENT / "python/prompts/system.md"
LANGFUSE_INFRA_ENV = ROOT / "infra/langfuse/.env"
DEFAULT_MODEL = "mistral:mistral-small-2603"
N_TEST = 100
S_D_ALERT = 0.4


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def metadata(args: argparse.Namespace, servers: dict[str, str]) -> dict[str, Any]:
    golden = GOLDENS / args.golden
    manifest = json.loads((golden / "MANIFEST.json").read_text(encoding="utf-8"))
    items_sha = sha256(golden / "items.jsonl")
    if items_sha != manifest["files"]["items.jsonl"]:
        raise SystemExit("Le golden set ne correspond plus à son MANIFEST : run refusé.")
    return {
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain")),
        "split": args.split,
        "model": args.model,
        "repeats": args.repeats,
        "servers": servers,
        "golden": {"version": manifest["version"], "items_sha256": items_sha},
        "spec": SPEC,
        "uv_lock_sha256": sha256(ROOT / "uv.lock"),
        "system_prompt_sha256": sha256(SYSTEM_PROMPT),
        "loop": {
            "max_tool_calls": loop.MAX_TOOL_CALLS,
            "max_retries": loop.MAX_RETRIES,
            "tool_error_behavior": loop.TOOL_ERROR_BEHAVIOR,
            "temperature": loop.TEMPERATURE,
        },
    }


def read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def as_line(record: Record) -> dict[str, Any]:
    return {
        "execution": record.execution.to_spec(),
        "score": asdict(record.score),
        "attempts": record.attempts,
        "answer": record.execution.answer,
    }


def report(split: str, lines: list[dict[str, Any]]) -> None:
    scored = [{**line["execution"], "success": line["score"]["success"]} for line in lines]
    summary = summarize(scored)
    print(f"\n=== {len(lines)} exécutions, split {split}")
    for variant, rate in sorted(summary.success.items()):
        print(f"success {variant:<6} : {rate:.3f}")
    errors = sum(line["execution"]["error"] is not None for line in lines)
    print(f"exécutions en erreur : {errors}")
    if summary.delta is None:
        return
    if split == "test":
        paired = [
            PairedScore(item_id=item_id, split="test", p_a=p_a, p_b=p_b)
            for item_id, (p_a, p_b) in summary.per_item.items()
        ]
        result = aggregate(paired)
        print(
            f"delta B − A = {result.delta:+.3f}, IC 95 % [{result.ci_low:+.3f} ; "
            f"{result.ci_high:+.3f}], n = {result.n}, verdict : {result.verdict}"
        )
        return
    print(f"delta B − A (dev, indicatif) = {summary.delta:+.3f}")
    if summary.s_d is not None:
        mde = (stats.t.ppf(0.975, N_TEST - 1) + stats.t.ppf(0.80, N_TEST - 1)) * summary.s_d
        print(
            f"s_d (dev) = {summary.s_d:.3f}, MDE attendu sur {N_TEST} items test = "
            f"{mde / math.sqrt(N_TEST) * 100:.1f} points"
        )
        if summary.s_d > S_D_ALERT:
            print(f"ALERTE : s_d > {S_D_ALERT}, à noter dans les Limites avant le run test.")
    print("\npᵢ(A)  pᵢ(B)  item")
    for item_id, (p_a, p_b) in summary.per_item.items():
        print(f"{p_a:5.2f}  {p_b:5.2f}  {item_id}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--final", action="store_true", help="run final sur le split test")
    parser.add_argument("--intent-url")
    parser.add_argument("--rest-url")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--golden", default=DEFAULT_GOLDEN, help="version du golden set")
    parser.add_argument("--repeats", "-k", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--runs-dir", type=Path, default=EXPERIMENT / "runs")
    parser.add_argument("--run-id", help="reprendre un run existant")
    parser.add_argument(
        "--items", help="ids séparés par des virgules (dev seulement), pour un essai"
    )
    parser.add_argument("--langfuse", action="store_true", help="tracer dans le Langfuse local")
    args = parser.parse_args()

    servers = {
        variant: url
        for variant, url in (("intent", args.intent_url), ("rest", args.rest_url))
        if url
    }
    if not servers:
        raise SystemExit("Donner au moins --intent-url ou --rest-url.")

    items = load_items(GOLDENS / args.golden / "items.jsonl", args.split, final=args.final)
    if args.items:
        if args.split != "dev":
            raise SystemExit("--items ne sert qu'aux essais sur le dev.")
        wanted = set(args.items.split(","))
        items = [item for item in items if item["id"] in wanted]
    meta = metadata(args, servers)
    if args.final and meta["git_dirty"]:
        raise SystemExit("Run final refusé : des modifications ne sont pas commitées (gel).")

    run_id = args.run_id or f"{meta['created'][:19].replace(':', '')}-{args.split}"
    tracer: Tracer = NO_TRACING
    langfuse = None
    if args.langfuse:
        from langfuse import Langfuse

        base_url, public_key, secret_key = credentials(LANGFUSE_INFRA_ENV)
        check_reachable(base_url)
        langfuse = Langfuse(public_key=public_key, secret_key=secret_key, base_url=base_url)
        tracer = LangfuseTracing(langfuse, run_id=run_id, split=args.split, model=args.model)
        meta["langfuse"] = {"base_url": base_url, "session_id": run_id}
    run_dir = args.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if not (run_dir / "run.json").exists():
        (run_dir / "run.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    records_path = run_dir / "records.jsonl"
    previous = read_records(records_path)
    done = {
        (line["execution"]["item_id"], line["execution"]["variant"], line["execution"]["repeat"])
        for line in previous
    }
    total = len(items) * len(servers) * args.repeats
    print(f"run {run_id} : {total} exécutions, {len(done)} déjà faites")

    def save(record: Record) -> None:
        with records_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(as_line(record), ensure_ascii=False) + "\n")
        execution = record.execution
        if args.split == "dev":
            print(
                f"  {execution.item_id} {execution.variant:<6} #{execution.repeat}"
                f" success={record.score.success} n_calls={record.score.n_calls}"
            )

    await run_campaign(
        items=items,
        servers=servers,
        model=args.model,
        repeats=args.repeats,
        system_prompt=SYSTEM_PROMPT.read_text(encoding="utf-8"),
        done=done,
        concurrency=args.concurrency,
        on_record=save,
        tracer=tracer,
    )
    if langfuse is not None:
        langfuse.flush()
    report(args.split, read_records(records_path))
    shown = run_dir.relative_to(ROOT) if run_dir.is_relative_to(ROOT) else run_dir
    print(f"\nrésultats : {shown}")


if __name__ == "__main__":
    anyio.run(main)
