"""Étape 7 de la 002 : le générateur comme levier (plan de la 002, décisions du 2026-11-12).

Le registre des générateurs, avec leurs réglages, et un smoke test : quelques items `dev` passés
par `top_k_20` pour chaque générateur, sur le chemin réel de la campagne (sortie structurée, schéma
v2, réflexion). Le smoke test ne mesure rien : c'est le contrôle d'intégration avant le protocole.

Identifiants, disponibilité et tarifs vérifiés le 2026-11-12 sur docs.mistral.ai et
aistudio.google.com (plan de la 002).

    uv run --env-file .env python -m exp002_leviers.step7 --smoke
    uv run --env-file .env python -m exp002_leviers.step7 --split dev
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASELINE = "mistral-small-2603"
CANDIDATES = (
    "mistral-large-4-0",
    "gemini-4-carbon",
    "gemma-4-31b-it",
    "mistral-small-2603-reasoning",
)
# Un item par type de difficulté du dev v5 : valeur simple, comparaison ancrée, sans réponse.
SMOKE_MODES = ("direct", "comparison", "unanswerable")


# Nom de variante de chaque candidat dans les exécutions (spec v2, § 3.2 : `^[a-z][a-z0-9_]*$`).
VARIANTS = {
    "mistral-large-4-0": "mistral_large_4",
    "gemini-4-carbon": "gemini_4_carbon",
    "gemma-4-31b-it": "gemma_4_31b",
    "mistral-small-2603-reasoning": "mistral_small_reasoning",
}
# Barème en dollars par million de tokens (entrée, sortie), relevé le 2026-11-12 sur
# https://docs.mistral.ai/inference/pricing et https://aistudio.google.com/docs/pricing.
# Chaque prix vaut à partir de sa date. Gemma n'est servi que sur le palier gratuit : pas de coût.
PRICES: dict[str, list[tuple[str, float, float]]] = {
    "mistral-small-2603": [("2026-03-16", 0.15, 0.60)],
    "mistral-small-2603-reasoning": [("2026-03-16", 0.15, 0.60)],
    "mistral-large-4-0": [("2026-11-05", 0.70, 2.10)],
    "gemini-4-carbon": [("2026-11-10", 2.00, 10.00), ("2026-12-01", 4.00, 20.00)],
    "gemma-4-31b-it": [],
}
PRICE_SOURCES = {
    "checked": "2026-11-12",
    "mistral": "https://docs.mistral.ai/inference/pricing",
    "google": "https://aistudio.google.com/docs/pricing",
}
# Règle de choix du générateur de l'étape 8 (README, « Étape 7 », Protocole).
MAX_ERROR_RATE = 0.01
MAX_HALLUCINATION_CI_HIGH = 0.10
TIE_POINTS = 0.02


def cost_usd(execution: dict, generator: str, *, day: str) -> float | None:
    """Tokens × barème en vigueur le jour du run ; `None` sans barème ou sans tokens."""
    prices = [p for p in PRICES[generator] if p[0] <= day]
    usage = execution["usage"]
    if not prices or usage["input_tokens"] is None or usage["output_tokens"] is None:
        return None
    _, price_in, price_out = prices[-1]
    return (usage["input_tokens"] * price_in + usage["output_tokens"] * price_out) / 1_000_000


def analyze_step7(
    items: list[dict], executions: list[dict], *, split: str, excluded: list[str]
) -> dict:
    """Les deux critères de chaque candidat contre A (`top_k_20`), chacun avec sa famille de
    Holm sur les candidats présents (spec v2, § 8.1 et § 8.3), et les agrégats (§ 7)."""
    from ailab_evals import rag_qa_v2
    from exp002_leviers.configurations import TOP_K_20

    present = [name for name, v in VARIANTS.items() if any(e["variant"] == v for e in executions)]
    common = {"split": split, "excluded": excluded}
    results: dict[str, dict] = {name: {} for name in present}
    for metric, direction in (("correct", "higher_better"), ("hallucination", "lower_better")):
        members = []
        for name in present:
            comparison = rag_qa_v2.compare(
                items,
                executions,
                baseline=TOP_K_20,
                variant=VARIANTS[name],
                metric=metric,
                direction=direction,
                **common,
            )
            results[name][metric] = comparison
            members.append(
                rag_qa_v2.FamilyMember(
                    name, direction, _pairs(items, executions, VARIANTS[name], metric, common)
                )
            )
        for name, corrected in zip(present, rag_qa_v2.holm_family(members), strict=True):
            results[name][metric] |= {
                "p_holm": corrected["p_holm"],
                "verdict_holm": corrected["verdict_holm"],
            }
    configurations = {
        variant: rag_qa_v2.variant_aggregates(
            items, [e for e in executions if e["variant"] == variant], **common
        )
        for variant in (TOP_K_20, *(VARIANTS[n] for n in present))
    }
    for name in present:
        results[name]["aggregates"] = configurations[VARIANTS[name]]
    return {
        "split": split,
        "excluded": excluded,
        "candidates": results,
        "baseline": {"aggregates": configurations[TOP_K_20]},
        "configurations": {
            TOP_K_20: configurations[TOP_K_20],
            **{name: configurations[VARIANTS[name]] for name in present},
        },
    }


def _pairs(items, executions, variant, metric, common) -> list:
    """Les pᵢ de A et de B pour la famille de Holm, avec la même règle que `compare` (§ 8.1)."""
    from ailab_evals import rag_qa_v2
    from exp002_leviers.configurations import TOP_K_20

    kept = {
        i["id"]: i
        for i in items
        if i["split"] == common["split"] and i["id"] not in set(common["excluded"])
    }
    values: dict[tuple[str, str], list[float]] = {}
    for e in executions:
        if e["variant"] in (TOP_K_20, variant) and e["item_id"] in kept:
            value = rag_qa_v2.score_execution(kept[e["item_id"]], e)[metric]
            if value is not None:
                values.setdefault((e["item_id"], e["variant"]), []).append(float(value))
    return [
        rag_qa_v2.PairedScore(
            item_id,
            "test",
            sum(values[(item_id, TOP_K_20)]) / len(values[(item_id, TOP_K_20)]),
            sum(values[(item_id, variant)]) / len(values[(item_id, variant)]),
        )
        for item_id in kept
        if (item_id, TOP_K_20) in values and (item_id, variant) in values
    ]


def choose_step8(baseline: dict, candidates: dict[str, dict]) -> dict:
    """La règle fixée au protocole : parmi les générateurs fiables (erreurs sous 1 %) qui
    n'inventent pas plus que A (borne haute du delta sous +0,10), le meilleur `correct` ; à moins
    de 2 points du meilleur, le moins cher (un coût inconnu passe en dernier)."""
    eligible = {BASELINE: baseline["aggregates"]}
    excluded = {}
    for name, c in candidates.items():
        agg = c["aggregates"]
        reasons = []
        if agg["error_rate"] is None or agg["error_rate"] >= MAX_ERROR_RATE:
            reasons.append("taux d'erreur")
        ci_high = c["hallucination"]["ci_high"]
        if ci_high is not None and ci_high >= MAX_HALLUCINATION_CI_HIGH:
            reasons.append("réponses inventées")
        if reasons:
            excluded[name] = reasons
        else:
            eligible[name] = agg
    best = max(a["correct"] for a in eligible.values())
    close = [n for n, a in eligible.items() if a["correct"] >= best - TIE_POINTS]
    chosen = min(
        close,
        key=lambda n: (eligible[n]["cost_usd_mean"] is None, eligible[n]["cost_usd_mean"] or 0.0),
    )
    return {"chosen": chosen, "close_to_best": close, "excluded": excluded}


@dataclass(frozen=True)
class Generator:
    name: str
    model: Any  # identifiant Pydantic AI ou instance de modèle
    settings: dict


def generators(*, api_keys: bool = True) -> dict[str, Generator]:
    """La baseline et les quatre candidats. `api_keys=False` construit les modèles Mistral avec une
    clé factice, pour les tests."""
    from pydantic_ai.providers.mistral import MistralProvider

    from ailab_rag.generators import MistralEffortModel

    key = os.environ.get("MISTRAL_API_KEY") if api_keys else "test"
    provider = MistralProvider(api_key=key)
    return {
        BASELINE: Generator(BASELINE, f"mistral:{BASELINE}", {"temperature": 0.0}),
        # Plus gros, même famille. Réflexion toujours active : niveau le plus bas.
        "mistral-large-4-0": Generator(
            "mistral-large-4-0",
            MistralEffortModel("mistral-large-4-0", effort="low", provider=provider),
            {"temperature": 0.0},
        ),
        # Modèle de pointe. temperature ignorée par Google : elle n'est pas envoyée.
        "gemini-4-carbon": Generator(
            "gemini-4-carbon",
            "google:gemini-4-carbon",
            {"google_thinking_config": {"thinking_level": "low"}},
        ),
        # Open-weight d'une autre famille (Apache 2.0), servi par l'API Gemini, palier gratuit.
        # L'effet de temperature n'y est pas documenté : elle est envoyée, comme à la baseline.
        "gemma-4-31b-it": Generator(
            "gemma-4-31b-it",
            "google:gemma-4-31b-it",
            {"temperature": 0.0, "google_thinking_config": {"thinking_level": "minimal"}},
        ),
        # Raisonnement activé sur la baseline elle-même.
        "mistral-small-2603-reasoning": Generator(
            "mistral-small-2603-reasoning",
            MistralEffortModel(BASELINE, effort="high", provider=provider),
            {"temperature": 0.0},
        ),
    }


def _smoke(out: Path) -> list[dict[str, Any]]:
    from ailab_rag.answering import run_item
    from ailab_rag.campaign import read_jsonl
    from ailab_rag.corpus import passages
    from ailab_rag.embeddings import CachedEmbedder, MistralEmbedder
    from ailab_rag.retrieval import build_index
    from exp002_leviers.campaign import invalid_v2_executions
    from exp002_leviers.configurations import TOP_K_20
    from exp002_leviers.paths import ARTICLES, CACHE_DIR, GOLDEN_V5
    from exp004_rag.campaign import build_retrievers as step3_retrievers

    items = [i for i in read_jsonl(GOLDEN_V5) if i["split"] == "dev"]
    chosen = [next(i for i in items if i["mode"] == mode) for mode in SMOKE_MODES]
    embedder = CachedEmbedder(MistralEmbedder(), CACHE_DIR / "embeddings")
    index = build_index(passages(read_jsonl(ARTICLES)), embedder)
    retrieve = step3_retrievers(index, embedder)[TOP_K_20]

    async def run() -> list[dict]:
        rows = []
        for generator in generators().values():
            for item in chosen:
                execution = await run_item(
                    item,
                    variant=TOP_K_20,
                    model=generator.model,
                    repeat=0,
                    retrieve=retrieve,
                    canonical="v2",
                    settings=generator.settings,
                )
                execution["model"] = generator.name
                rows.append(execution)
        return rows

    rows = asyncio.run(run())
    invalid = set(invalid_v2_executions(rows))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    from ailab_evals.rag_qa_v2 import score_execution

    by_id = {i["id"]: i for i in chosen}
    report = []
    for index_, r in enumerate(rows):
        report.append(
            {
                "generator": r["model"],
                "item": r["item_id"],
                "mode": by_id[r["item_id"]]["mode"],
                "error": r["error"],
                "schema_ok": index_ not in invalid,
                "correct": score_execution(by_id[r["item_id"]], r)["correct"],
                "output_tokens": r["usage"]["output_tokens"],
                "latency_s": round(r["latency_s"], 2),
            }
        )
    return report


# A sur le `dev` : la configuration top_k_20 du run de contrôle (README, « Étape 7 », Protocole).
BASELINE_RUN = "2026-11-12-mistral-mistral-small-2603-dev"


def _run_dev(run_dir: Path) -> dict:
    from datetime import date

    from ailab_rag import cli
    from ailab_rag.campaign import read_jsonl, run_campaign
    from ailab_rag.corpus import passages
    from ailab_rag.embeddings import CachedEmbedder, MistralEmbedder
    from ailab_rag.retrieval import build_index
    from exp002_leviers.campaign import invalid_v2_executions
    from exp002_leviers.configurations import TOP_K_20
    from exp002_leviers.paths import ARTICLES, AUDIT, CACHE_DIR, EXPERIMENT_DIR, GOLDEN_V5, ROOT
    from exp004_rag.campaign import build_retrievers as step3_retrievers
    from exp006_rag.campaign import excluded_items

    day = date.today().isoformat()
    excluded = sorted(excluded_items(AUDIT))
    all_items = read_jsonl(GOLDEN_V5)
    items = [i for i in all_items if i["split"] == "dev" and i["id"] not in set(excluded)]
    baseline = [
        e
        for e in read_jsonl(EXPERIMENT_DIR / "runs" / BASELINE_RUN / "executions.jsonl")
        if e["variant"] == TOP_K_20
    ]
    embedder = CachedEmbedder(MistralEmbedder(), CACHE_DIR / "embeddings")
    index = build_index(passages(read_jsonl(ARTICLES)), embedder)
    retrieve = step3_retrievers(index, embedder)[TOP_K_20]

    executions = [{**e, "cost_usd": cost_usd(e, BASELINE, day=day)} for e in baseline]
    for name, generator in generators().items():
        if name == BASELINE:
            continue
        variant = VARIANTS[name]
        rows = asyncio.run(
            run_campaign(
                items,
                variants=[variant],
                model=generator.model,
                repeats=3,
                retrievers={variant: retrieve},
                out=run_dir / f"executions-{variant}.jsonl",
                concurrency=2 if name == "gemma-4-31b-it" else 4,
                canonical="v2",
                settings=generator.settings,
            )
        )
        executions += [{**e, "cost_usd": cost_usd(e, name, day=day)} for e in rows]
        print(f"{name} : {len(rows)} exécutions", flush=True)

    invalid = invalid_v2_executions(executions)
    if invalid:
        raise SystemExit(f"{len(invalid)} exécutions hors du schéma v2 (rangs {invalid[:10]})")
    summary = analyze_step7(all_items, executions, split="dev", excluded=excluded)
    summary["step8"] = choose_step8(summary["baseline"], summary["candidates"])
    summary["run"] = {
        "day": day,
        "commit": cli.current_commit(ROOT),
        "baseline_run": f"runs/{BASELINE_RUN}",
        "golden": cli.display_path(GOLDEN_V5, ROOT),
        "spec": "evals/spec/rag-qa/v2",
        "k": 3,
        "prices": PRICES,
        "price_sources": PRICE_SOURCES,
        "settings": {name: g.settings for name, g in generators(api_keys=False).items()},
        "reasoning_effort_sent": {
            "mistral-large-4-0": "low",
            "mistral-small-2603-reasoning": "high",
        },
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def _fmt(value: float | None, spec: str) -> str:
    return "—" if value is None else format(value, spec)


def main(argv: list[str] | None = None) -> None:
    from exp002_leviers.paths import EXPERIMENT_DIR

    parser = argparse.ArgumentParser(description="Étape 7 de la 002")
    parser.add_argument("--smoke", action="store_true", help="contrôle d'intégration, 3 items dev")
    parser.add_argument("--split", choices=["dev", "test"], help="le run dev des candidats")
    args = parser.parse_args(argv)
    if args.split == "test":
        raise SystemExit(
            "le verdict de l'étape 7 vient du run consolidé 2 (README, « Étape 7 ») : "
            "pas de run test propre à l'étape"
        )
    if args.split == "dev":
        from datetime import date

        os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
        run_dir = EXPERIMENT_DIR / "runs" / f"{date.today()}-step7-dev"
        summary = _run_dev(run_dir)
        a = summary["baseline"]["aggregates"]
        print(f"A (mistral-small-2603) : correct {a['correct']:.3f}", flush=True)
        for name, c in summary["candidates"].items():
            k, h = c["correct"], c["hallucination"]
            print(
                f"{name} : correct {c['aggregates']['correct']:.3f} "
                f"({_fmt(k['delta'], '+.3f')}, p_holm {_fmt(k['p_holm'], '.3f')}, "
                f"{k['verdict_holm']}) ; inventées {_fmt(h['delta'], '+.3f')} "
                f"(p_holm {_fmt(h['p_holm'], '.3f')}, {h['verdict_holm']}) ; "
                f"erreurs {c['aggregates']['error_rate']:.3f} ; "
                f"coût {_fmt(c['aggregates']['cost_usd_mean'], '.5f')} $",
                flush=True,
            )
        print(f"étape 8 : {summary['step8']}", flush=True)
        return
    if args.smoke:
        os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
        out = EXPERIMENT_DIR / "runs" / "step7-smoke" / "executions.jsonl"
        for row in _smoke(out):
            print(json.dumps(row, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
