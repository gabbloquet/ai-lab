"""Étape 7 de la 002 : le générateur comme levier (plan de la 002, décisions du 2026-11-12).

Le registre des générateurs, avec leurs réglages, et un smoke test : quelques items `dev` passés
par `top_k_20` pour chaque générateur, sur le chemin réel de la campagne (sortie structurée, schéma
v2, réflexion). Le smoke test ne mesure rien : c'est le contrôle d'intégration avant le protocole.

Identifiants, disponibilité et tarifs vérifiés le 2026-11-12 sur docs.mistral.ai et
aistudio.google.com (plan de la 002).

    uv run --env-file .env python -m exp002_leviers.step7 --smoke
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


def main(argv: list[str] | None = None) -> None:
    from exp002_leviers.paths import EXPERIMENT_DIR

    parser = argparse.ArgumentParser(description="Étape 7 de la 002")
    parser.add_argument("--smoke", action="store_true", help="contrôle d'intégration, 3 items dev")
    args = parser.parse_args(argv)
    if args.smoke:
        os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
        out = EXPERIMENT_DIR / "runs" / "step7-smoke" / "executions.jsonl"
        for row in _smoke(out):
            print(json.dumps(row, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
