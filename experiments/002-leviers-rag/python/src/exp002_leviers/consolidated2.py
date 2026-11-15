"""Le run consolidé 2 de la 002 sur le `test` v5 (README, « Run consolidé 2 »).

Quatre blocs, chacun relançable : les exécutions enregistrées sont reprises, sans nouvel appel.
- A : étapes 1 à 6, avec les trois générateurs de la série (`exp002_leviers.campaign --spec v2`).
- B : étape 7, `top_k_20` avec les quatre candidats.
- C : étape 8, RAG agentique gelé (cycle 2) avec Large 4, et avec Carbon (secondaire, C').
- report : les verdicts réunis dans un seul `summary.json`.

    uv run --env-file .env python -m exp002_leviers.consolidated2 --final --block A
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

BLOCK_A_MODELS = (
    "mistral:mistral-small-2603",
    "mistral:ministral-14b-2512",
    "google:gemini-3.5-flash-lite",
)
AGENTIC_GENERATORS = {"mistral-large-4-0": "mistral_large_4", "gemini-4-carbon": "gemini_4_carbon"}
RUN_NAME = "consolidated2-test"


def _paths() -> tuple[Path, Path]:
    from exp002_leviers.paths import EXPERIMENT_DIR

    run_dir = EXPERIMENT_DIR / "runs" / RUN_NAME
    return run_dir, EXPERIMENT_DIR


def _test_items() -> tuple[list[dict], list[dict], list[str]]:
    from ailab_rag.campaign import read_jsonl
    from exp002_leviers.paths import AUDIT, GOLDEN_V5
    from exp006_rag.campaign import excluded_items

    excluded = sorted(excluded_items(AUDIT))
    all_items = read_jsonl(GOLDEN_V5)
    items = [i for i in all_items if i["split"] == "test" and i["id"] not in set(excluded)]
    return all_items, items, excluded


def _block_a(run_dir: Path) -> None:
    from exp002_leviers.campaign import main as campaign

    for model in BLOCK_A_MODELS:
        slug = model.replace(":", "-").replace("/", "-")
        campaign(
            [
                "--split",
                "test",
                "--final",
                "--spec",
                "v2",
                "--model",
                model,
                "--run-dir",
                str(run_dir / "A" / slug),
            ]
        )


def _top_k_20_retriever():
    from ailab_rag.campaign import read_jsonl
    from ailab_rag.corpus import passages
    from ailab_rag.embeddings import CachedEmbedder, MistralEmbedder
    from ailab_rag.retrieval import build_index
    from exp002_leviers.configurations import TOP_K_20
    from exp002_leviers.paths import ARTICLES, CACHE_DIR
    from exp004_rag.campaign import build_retrievers as step3_retrievers

    embedder = CachedEmbedder(MistralEmbedder(), CACHE_DIR / "embeddings")
    index = build_index(passages(read_jsonl(ARTICLES)), embedder)
    return step3_retrievers(index, embedder)[TOP_K_20]


def _block_b(run_dir: Path) -> None:
    from ailab_rag.campaign import run_campaign
    from exp002_leviers.step7 import BASELINE, VARIANTS, generators

    _, items, _ = _test_items()
    retrieve = _top_k_20_retriever()
    for name, generator in generators().items():
        if name == BASELINE:
            continue
        variant = VARIANTS[name]
        gemma = name == "gemma-4-31b-it"
        rows = asyncio.run(
            run_campaign(
                items,
                variants=[variant],
                model=generator.model,
                repeats=3,
                retrievers={variant: retrieve},
                out=run_dir / "B" / f"executions-{variant}.jsonl",
                concurrency=1 if gemma else 4,
                max_attempts=30 if gemma else 5,
                canonical="v2",
                settings=generator.settings,
            )
        )
        print(f"bloc B, {name} : {len(rows)} exécutions", flush=True)


def _block_c(run_dir: Path) -> None:
    from ailab_rag.agentic import AGENTIC_VARIANT, run_agentic_item
    from ailab_rag.campaign import run_campaign
    from exp002_leviers.step7 import generators
    from exp002_leviers.step8 import FROZEN_CYCLE, GUIDANCES

    _, items, _ = _test_items()
    guidance = GUIDANCES[FROZEN_CYCLE]
    for name in AGENTIC_GENERATORS:
        generator = generators()[name]

        async def runner(item: dict, variant: str, repeat: int, *, reraise, g=generator) -> dict:
            return await run_agentic_item(
                item,
                model=g.model,
                repeat=repeat,
                settings=g.settings,
                reraise=reraise,
                guidance=guidance,
            )

        rows = asyncio.run(
            run_campaign(
                items,
                variants=[AGENTIC_VARIANT],
                model=generator.model,
                repeats=3,
                out=run_dir / "C" / f"executions-{name}.jsonl",
                concurrency=4,
                canonical="v2",
                runner=runner,
            )
        )
        print(f"bloc C, {name} : {len(rows)} exécutions", flush=True)


def assemble(
    items: list[dict],
    step7_executions: list[dict],
    agentic: dict[str, list[dict]],
    *,
    block_a: dict[str, Any],
    excluded: list[str],
    day: str,
) -> dict[str, Any]:
    """Les verdicts des étapes 7 et 8 sur le `test`, à côté des résumés du bloc A."""
    from exp002_leviers.step7 import analyze_step7, choose_step8, cost_usd
    from exp002_leviers.step8 import analyze_step8

    costed = []
    for e in step7_executions:
        name = next((n for n, v in _variants().items() if v == e["variant"]), "mistral-small-2603")
        costed.append({**e, "cost_usd": cost_usd(e, name, day=day)})
    step7 = analyze_step7(items, costed, split="test", excluded=excluded)
    step7["step8_rule_on_test"] = choose_step8(step7["baseline"], step7["candidates"])
    results: dict[str, Any] = {"block_a": block_a, "step7": step7}
    for name, key in (
        ("mistral-large-4-0", "step8"),
        ("gemini-4-carbon", "step8_carbon_secondary"),
    ):
        baseline_variant = AGENTIC_GENERATORS[name]
        baseline = [e for e in step7_executions if e["variant"] == baseline_variant]
        results[key] = analyze_step8(
            items,
            baseline + agentic[name],
            split="test",
            excluded=excluded,
            day=day,
            generator=name,
            baseline_variant=baseline_variant,
        )
    return results


def _variants() -> dict[str, str]:
    from exp002_leviers.step7 import VARIANTS

    return VARIANTS


def _report(run_dir: Path) -> dict[str, Any]:
    from ailab_rag import cli
    from ailab_rag.campaign import read_jsonl
    from exp002_leviers.configurations import TOP_K_20
    from exp002_leviers.paths import GOLDEN_V5, ROOT

    all_items, _, excluded = _test_items()
    block_a = {}
    for model in BLOCK_A_MODELS:
        slug = model.replace(":", "-").replace("/", "-")
        block_a[model] = json.loads((run_dir / "A" / slug / "summary.json").read_text("utf-8"))
    small = run_dir / "A" / "mistral-mistral-small-2603" / "executions.jsonl"
    step7 = [e for e in read_jsonl(small) if e["variant"] == TOP_K_20]
    for variant in _variants().values():
        step7 += read_jsonl(run_dir / "B" / f"executions-{variant}.jsonl")
    agentic = {n: read_jsonl(run_dir / "C" / f"executions-{n}.jsonl") for n in AGENTIC_GENERATORS}
    day = date.today().isoformat()
    summary = assemble(all_items, step7, agentic, block_a=block_a, excluded=excluded, day=day)
    summary["run"] = {
        "day": day,
        "commit": cli.current_commit(ROOT),
        "golden": cli.display_path(GOLDEN_V5, ROOT),
        "spec": "evals/spec/rag-qa/v2",
        "k": 3,
        "final": True,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main(
    argv: list[str] | None = None,
    git_is_clean: Callable[[], bool] | None = None,
) -> None:
    parser = argparse.ArgumentParser(description="Run consolidé 2 de la 002 (test v5)")
    parser.add_argument("--final", action="store_true", help="le run unique sur le test v5")
    parser.add_argument("--block", choices=["A", "B", "C", "report"], required=True)
    args = parser.parse_args(argv)
    if not args.final:
        raise SystemExit("le test v5 ne se lance qu'une fois, pour le run final : ajoutez --final")
    if git_is_clean is None:
        from ailab_rag import cli
        from exp002_leviers.paths import ROOT

        def git_is_clean() -> bool:
            return cli.git_is_clean(ROOT)

    if not git_is_clean():
        raise SystemExit(
            "run final refusé : l'arbre git n'est pas propre, faites d'abord le commit de gel"
        )
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    run_dir, _ = _paths()
    {"A": _block_a, "B": _block_b, "C": _block_c, "report": _report}[args.block](run_dir)


if __name__ == "__main__":
    main()
