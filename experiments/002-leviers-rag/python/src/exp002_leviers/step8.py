"""Étape 8 de la 002 : le RAG agentique (README de la 002, « Étape 8 »).

A est `top_k_20` avec Mistral Large 4, repris du run `dev` de l'étape 7 (mêmes réglages gelés).
B est `agentic_rag` : le même générateur, qui cherche par les outils MCP du serveur
`exp002_mcp_server`. Deux cycles `dev` au plus, sur la seule consigne d'usage des outils et les
descriptions des outils ; le verdict viendra du run consolidé 2.

    uv run --env-file .env python -m exp002_leviers.step8 --split dev --cycle 1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from ailab_rag.agentic import AGENTIC_GUIDANCE, AGENTIC_VARIANT, MAX_CALLS

GENERATOR = "mistral-large-4-0"
# A : la variante de Large 4 au run `dev` de l'étape 7 (top_k_20, réflexion low).
BASELINE_VARIANT = "mistral_large_4"
BASELINE_RUN = "2026-11-12-step7-dev"
# Une consigne par cycle `dev` (protocole : 2 cycles au plus, sur la consigne et les descriptions).
GUIDANCES: dict[int, str] = {
    1: AGENTIC_GUIDANCE,
    # Cycle 2 (2026-11-15), après le cycle 1 : les questions sans réponse prenaient 5,4 appels
    # en moyenne, et 16 % des questions touchaient le plafond. Une règle d'arrêt de la recherche,
    # sans consigne nouvelle sur l'abstention.
    2: AGENTIC_GUIDANCE.replace(
        "Réponds à partir de ce que les outils t'ont rendu ;",
        "Arrête de chercher dès qu'un passage donne la valeur demandée pour la situation de la "
        "question. Si trois recherches reformulées ne la font pas apparaître, ne cherche plus. "
        "Réponds à partir de ce que les outils t'ont rendu ;",
    ),
}


def tool_stats(executions: list[dict]) -> dict[str, Any]:
    """`tool_calls` (moyenne, médiane, distribution), part des questions au plafond, part des
    appels qui lisent un article."""
    calls = [e["tool_calls"] for e in executions if e["tool_calls"] is not None]
    if not calls:
        return {"executions": 0}
    gets = sum(e.get("extra", {}).get("get_calls", 0) for e in executions)
    return {
        "executions": len(calls),
        "mean": statistics.fmean(calls),
        "median": float(statistics.median(calls)),
        "distribution": {str(k): v for k, v in sorted(Counter(calls).items())},
        "at_cap_share": sum(c >= MAX_CALLS for c in calls) / len(calls),
        "get_article_share": gets / sum(calls) if sum(calls) else 0.0,
    }


def _with_cost(executions: list[dict], day: str) -> list[dict]:
    from exp002_leviers.step7 import cost_usd

    return [{**e, "cost_usd": cost_usd(e, GENERATOR, day=day)} for e in executions]


def analyze_step8(
    items: list[dict],
    executions: list[dict],
    *,
    split: str,
    excluded: list[str],
    day: str = "2026-11-15",
) -> dict[str, Any]:
    """`correct` (critère, § 8.1, une seule comparaison), réponses inventées, agrégats et
    statistiques d'outils. Le coût suit le barème gelé de l'étape 7."""
    from ailab_evals import rag_qa_v2

    executions = _with_cost(executions, day)
    common = {"split": split, "excluded": excluded}
    baseline = [e for e in executions if e["variant"] == BASELINE_VARIANT]
    agentic = [e for e in executions if e["variant"] == AGENTIC_VARIANT]
    kept = {i["id"] for i in items if i["split"] == split and i["id"] not in set(excluded)}
    return {
        "split": split,
        "excluded": excluded,
        "correct": rag_qa_v2.compare(
            items,
            executions,
            baseline=BASELINE_VARIANT,
            variant=AGENTIC_VARIANT,
            metric="correct",
            direction="higher_better",
            **common,
        ),
        "hallucination": rag_qa_v2.compare(
            items,
            executions,
            baseline=BASELINE_VARIANT,
            variant=AGENTIC_VARIANT,
            metric="hallucination",
            direction="lower_better",
            **common,
        ),
        "baseline": rag_qa_v2.variant_aggregates(items, baseline, **common),
        "agentic": rag_qa_v2.variant_aggregates(items, agentic, **common),
        "tools": tool_stats([e for e in agentic if e["item_id"] in kept]),
    }


def _run_dev(cycle: int, run_dir: Path) -> dict[str, Any]:
    from ailab_rag import cli
    from ailab_rag.agentic import run_agentic_item
    from ailab_rag.campaign import read_jsonl, run_campaign
    from exp002_leviers.campaign import invalid_v2_executions
    from exp002_leviers.paths import AUDIT, EXPERIMENT_DIR, GOLDEN_V5, ROOT
    from exp002_leviers.step7 import generators
    from exp006_rag.campaign import excluded_items

    day = date.today().isoformat()
    excluded = sorted(excluded_items(AUDIT))
    all_items = read_jsonl(GOLDEN_V5)
    items = [i for i in all_items if i["split"] == "dev" and i["id"] not in set(excluded)]
    baseline = read_jsonl(
        EXPERIMENT_DIR / "runs" / BASELINE_RUN / f"executions-{BASELINE_VARIANT}.jsonl"
    )
    generator = generators()[GENERATOR]
    guidance = GUIDANCES[cycle]

    async def runner(item: dict, variant: str, repeat: int, *, reraise) -> dict:
        return await run_agentic_item(
            item,
            model=generator.model,
            repeat=repeat,
            settings=generator.settings,
            reraise=reraise,
            guidance=guidance,
        )

    agentic = asyncio.run(
        run_campaign(
            items,
            variants=[AGENTIC_VARIANT],
            model=generator.model,
            repeats=3,
            out=run_dir / "executions.jsonl",
            concurrency=4,
            canonical="v2",
            runner=runner,
        )
    )
    executions = baseline + agentic
    invalid = invalid_v2_executions(_with_cost(executions, day))
    if invalid:
        raise SystemExit(f"{len(invalid)} exécutions hors du schéma v2 (rangs {invalid[:10]})")
    summary = analyze_step8(all_items, executions, split="dev", excluded=excluded, day=day)
    summary["run"] = {
        "day": day,
        "cycle": cycle,
        "guidance": guidance,
        "commit": cli.current_commit(ROOT),
        "generator": GENERATOR,
        "settings": generator.settings,
        "baseline_run": f"runs/{BASELINE_RUN}",
        "golden": cli.display_path(GOLDEN_V5, ROOT),
        "spec": "evals/spec/rag-qa/v2",
        "k": 3,
        "max_calls": MAX_CALLS,
        "passages_per_search": 5,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> None:
    from exp002_leviers.paths import EXPERIMENT_DIR

    parser = argparse.ArgumentParser(description="Étape 8 de la 002 : RAG agentique")
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--cycle", type=int, default=1)
    args = parser.parse_args(argv)
    if args.split == "test":
        raise SystemExit(
            "le verdict de l'étape 8 vient du run consolidé 2 (README, « Étape 8 ») : "
            "pas de run test propre à l'étape"
        )
    if args.cycle not in GUIDANCES:
        raise SystemExit(f"cycle {args.cycle} inconnu : cycles écrits {sorted(GUIDANCES)}")
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    run_dir = EXPERIMENT_DIR / "runs" / f"{date.today()}-step8-dev-cycle{args.cycle}"
    s = _run_dev(args.cycle, run_dir)
    c, b, a, t = s["correct"], s["baseline"], s["agentic"], s["tools"]
    print(
        f"cycle {args.cycle} : correct {b['correct']:.3f} → {a['correct']:.3f} "
        f"({c['delta']:+.3f} [{c['ci_low']:+.3f} ; {c['ci_high']:+.3f}], {c['verdict']}) ; "
        f"inventées {b['hallucination_rate']:.3f} → {a['hallucination_rate']:.3f} ; "
        f"appels {t['mean']:.2f} (plafond {t['at_cap_share']:.1%}) ; "
        f"coût {b['cost_usd_mean']:.4f} → {a['cost_usd_mean']:.4f} $ ; "
        f"latence {b['latency_s_median']:.1f} → {a['latency_s_median']:.1f} s",
        flush=True,
    )


if __name__ == "__main__":
    main()
