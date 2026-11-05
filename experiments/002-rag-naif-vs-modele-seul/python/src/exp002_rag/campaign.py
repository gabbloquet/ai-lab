"""La campagne de la 002 : chaque item × chaque variante × k répétitions, puis le résumé.

Chaque exécution est ajoutée à `executions.jsonl` dès qu'elle est finie : une campagne
interrompue reprend sans refaire ni repayer ce qui est déjà enregistré. Une erreur passagère du
fournisseur (limite de débit, panne) relance l'exécution au lieu de la compter comme fausse.

    uv run --env-file .env python -m exp002_rag.campaign \\
        --split dev --model mistral:mistral-small-2603
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from collections.abc import Awaitable, Callable
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models import Model

from ailab_evals.rag_qa import KS, PairedScore, aggregate, score_execution
from exp002_rag.answering import CLOSED_BOOK, NAIVE_RAG, TOP_K, Retriever, run_item
from exp002_rag.tracing import NO_TRACING, LangfuseTracing, Tracer

ROOT = Path(__file__).resolve().parents[5]
EXPERIMENT_DIR = ROOT / "experiments" / "002-rag-naif-vs-modele-seul"
GOLDEN = ROOT / "domains/droit-consommation/golden/rag-qa/v1/items.jsonl"
ARTICLES = ROOT / "domains/droit-consommation/data/v1/articles.jsonl"
TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
FAILURES = ("correct", "retrieval_miss", "generation_miss", "error")


def is_transient(error: BaseException) -> bool:
    return isinstance(error, ModelHTTPError) and error.status_code in TRANSIENT_STATUSES


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _key(execution: dict) -> tuple[str, str, int]:
    return execution["item_id"], execution["variant"], execution["repeat"]


# --- Campagne -----------------------------------------------------------------------------------


async def run_campaign(
    items: list[dict],
    *,
    variants: list[str],
    model: str | Model,
    repeats: int,
    retrieve: Retriever,
    out: Path,
    concurrency: int = 4,
    max_attempts: int = 5,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    tracer: Tracer = NO_TRACING,
) -> list[dict]:
    done = {_key(e): e for e in _read_jsonl(out)}
    plan = [(item, v, r) for item in items for v in variants for r in range(repeats)]
    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    out.parent.mkdir(parents=True, exist_ok=True)

    async def one(item: dict, variant: str, repeat: int) -> dict:
        async with semaphore:
            with tracer.execution(item=item, variant=variant, repeat=repeat) as observe:
                for attempt in range(1, max_attempts + 1):
                    try:
                        execution = await run_item(
                            item,
                            variant=variant,
                            model=model,
                            repeat=repeat,
                            retrieve=retrieve,
                            reraise=is_transient,
                        )
                        break
                    except ModelHTTPError as error:
                        if not is_transient(error) or attempt == max_attempts:
                            raise
                        await sleep(min(2.0**attempt, 60.0))
                observe(execution, score_execution(item, execution).as_dict())
        async with lock:
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(execution, ensure_ascii=False) + "\n")
        return execution

    todo = [(i, v, r) for i, v, r in plan if (i["id"], v, r) not in done]
    for execution in await asyncio.gather(*(one(i, v, r) for i, v, r in todo)):
        done[_key(execution)] = execution
    return [done[(i["id"], v, r)] for i, v, r in plan]


# --- Résumé -------------------------------------------------------------------------------------


def _mean(values: list[Any]) -> float | None:
    present = [float(v) for v in values if v is not None]
    return mean(present) if present else None


def _variant_summary(rows: list[tuple[dict, dict, dict]]) -> dict[str, Any]:
    """Agrégats d'une variante (spec § 7). `rows` : (item, exécution, score)."""
    scores = [s for _, _, s in rows]
    failures = [s["failure"] for s in scores if s["failure"] is not None]
    by_mode: dict[str, list[bool]] = {}
    for item, _, s in rows:
        by_mode.setdefault(item["mode"], []).append(s["correct"])
    summary: dict[str, Any] = {
        "n_executions": len(rows),
        "correct": _mean([s["correct"] for s in scores]),
        "correct_answerable": _mean([s["correct"] for i, _, s in rows if i["answerable"]]),
        "false_abstention": _mean([s["false_abstention"] for s in scores]),
        "hallucination": _mean([s["hallucination"] for s in scores]),
        "error_rate": _mean([e["error"] is not None for _, e, _ in rows]),
        "failure": ({f: failures.count(f) / len(failures) for f in FAILURES} if failures else None),
        "by_mode": {mode: _mean(values) for mode, values in sorted(by_mode.items())},
        "citation_precision": _mean([s["citation_precision"] for s in scores]),
        "citation_recall": _mean([s["citation_recall"] for s in scores]),
        "context_size": _mean([s["context_size"] for s in scores]),
        "tokens": _mean([sum(e["usage"].values()) for _, e, _ in rows]),
    }
    for k in KS:
        summary[f"evidence_recall@{k}"] = _mean([s[f"evidence_recall@{k}"] for s in scores])
        summary[f"all_evidence@{k}"] = _mean([s[f"all_evidence@{k}"] for s in scores])
    return summary


def summarize(
    items: list[dict],
    executions: list[dict],
    *,
    split: str,
    baseline: str = CLOSED_BOOK,
    variant: str = NAIVE_RAG,
) -> dict[str, Any]:
    by_id = {i["id"]: i for i in items if i["split"] == split}
    rows: dict[str, list[tuple[dict, dict, dict]]] = {}
    for e in executions:
        if e["item_id"] in by_id:
            item = by_id[e["item_id"]]
            rows.setdefault(e["variant"], []).append((item, e, score_execution(item, e).as_dict()))

    comparison = None
    if baseline in rows and variant in rows:

        def p(name: str, item_id: str) -> float:
            return mean(float(s["correct"]) for i, _, s in rows[name] if i["id"] == item_id)

        # La règle de la spec (§ 8) ne garde que les items `test` ; sur le dev, on applique la
        # même règle aux items dev, et le résumé le signale par son champ `split`.
        paired = [
            PairedScore(item_id, "test", p(baseline, item_id), p(variant, item_id))
            for item_id in by_id
        ]
        if len(paired) >= 2:
            comparison = aggregate(paired).as_dict()

    return {
        "split": split,
        "n_items": len(by_id),
        "baseline": baseline,
        "variant": variant,
        "variants": {name: _variant_summary(r) for name, r in rows.items()},
        "comparison": comparison,
    }


# --- Ligne de commande --------------------------------------------------------------------------


def display_path(path: Path) -> str:
    """Le chemin à citer dans un rapport : relatif au dépôt quand il y est."""
    resolved = path.resolve()
    return str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)


def _git_is_clean() -> bool:
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return status.stdout.strip() == ""


def _retriever() -> Retriever:
    from exp002_rag.corpus import passages
    from exp002_rag.embeddings import CachedEmbedder, MistralEmbedder
    from exp002_rag.retrieval import build_index

    embedder = CachedEmbedder(MistralEmbedder(), EXPERIMENT_DIR / ".cache" / "embeddings")
    index = build_index(passages(_read_jsonl(ARTICLES)), embedder)
    return lambda question: index.search(embedder.embed([question])[0], TOP_K)


def _langfuse_tracer(run_id: str, split: str, model: str) -> LangfuseTracing:
    from langfuse import Langfuse

    from ailab_evals.langfuse_setup import check_reachable, credentials

    base_url, public_key, secret_key = credentials(ROOT / "infra/langfuse/.env")
    check_reachable(base_url)
    client = Langfuse(public_key=public_key, secret_key=secret_key, base_url=base_url)
    return LangfuseTracing(client, run_id=run_id, split=split, model=model)


def main(argv: list[str] | None = None, git_is_clean: Callable[[], bool] = _git_is_clean) -> None:
    parser = argparse.ArgumentParser(description="Campagne de la 002")
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--final", action="store_true", help="le run unique sur le test")
    parser.add_argument("--model", required=True, help="ex. mistral:mistral-small-2603")
    parser.add_argument("--variants", nargs="+", default=[CLOSED_BOOK, NAIVE_RAG])
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--langfuse", action="store_true", help="tracer le run dans Langfuse")
    args = parser.parse_args(argv)

    if args.split == "test" and not args.final:
        sys.exit("le split test ne se lance qu'une fois, pour le run final : ajoutez --final")
    if args.final and not git_is_clean():
        sys.exit("run final refusé : l'arbre git n'est pas propre, faites d'abord le commit de gel")

    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    items = [i for i in _read_jsonl(args.golden) if i["split"] == args.split]
    slug = args.model.replace(":", "-").replace("/", "-")
    run_dir = args.run_dir or EXPERIMENT_DIR / "runs" / f"{date.today()}-{slug}-{args.split}"
    tracer: Tracer = NO_TRACING
    if args.langfuse:
        tracer = _langfuse_tracer(run_dir.name, args.split, args.model)
    executions = asyncio.run(
        run_campaign(
            items,
            variants=args.variants,
            model=args.model,
            repeats=args.k,
            retrieve=_retriever(),
            out=run_dir / "executions.jsonl",
            concurrency=args.concurrency,
            tracer=tracer,
        )
    )
    if isinstance(tracer, LangfuseTracing):
        tracer.flush()
    summary = summarize(items, executions, split=args.split)
    summary["run"] = {
        "model": args.model,
        "k": args.k,
        "golden": display_path(args.golden),
        "langfuse": args.langfuse,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary["comparison"], ensure_ascii=False))


if __name__ == "__main__":
    main()
