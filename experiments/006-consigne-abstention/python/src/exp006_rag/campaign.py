"""La campagne de la 006 : le RAG à 20 passages de la 004 (A) contre le même RAG avec une phrase
d'ancrage plus exigeante (B).

A et B cherchent avec la même question dans le même index et reçoivent les mêmes 20 passages ;
seule la phrase d'ancrage du message change (`ailab_rag.prompting.rag_message`). Le verdict suit la
règle à deux critères du README (réponses inventées, garde sur les abstentions à tort), sur les
items valides : ceux que l'audit de la v1 trouve répondus par le code sont écartés.

    uv run --env-file .env python -m exp006_rag.campaign \\
        --split dev --model mistral:mistral-small-2603
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from ailab_rag import cli
from ailab_rag.answering import Retriever
from ailab_rag.campaign import abstention_comparison, read_jsonl, run_campaign, summarize
from ailab_rag.corpus import Passage
from ailab_rag.embeddings import Embedder
from ailab_rag.prompting import GROUNDING
from ailab_rag.retrieval import Index
from ailab_rag.tracing import NO_TRACING, LangfuseTracing, Tracer

ROOT = Path(__file__).resolve().parents[5]
EXPERIMENT_DIR = ROOT / "experiments" / "006-consigne-abstention"
GOLDEN = ROOT / "domains/droit-consommation/golden/rag-qa/v3/items.jsonl"
AUDIT = ROOT / "domains/droit-consommation/golden/rag-qa/audit/v1-unanswerable.jsonl"
ARTICLES = ROOT / "domains/droit-consommation/data/v1/articles.jsonl"
CACHE_DIR = ROOT / ".cache" / "ailab_rag"
FLUSH_SECONDS = 120.0

BASELINE = "top_k_20"
VARIANT = "abstain_strict"
TOP_K = 20
# Hausse tolérée des abstentions à tort (garde du verdict), fixée avant le premier run (README).
GUARD_MARGIN = 0.03
# Phrase d'ancrage de B, cycle 1 (2026-11-09). Au run 0 du dev, les réponses inventées appliquaient
# une règle écrite pour un cas voisin (frais de dossier d'un crédit immobilier, corps huit du contrat
# de crédit) ; la consigne de départ (« un extrait sur un cas voisin ne suffit pas ») ne les arrêtait
# pas. Le cycle 1 fait vérifier le champ d'application de la règle, exemples à l'appui.
STRICT_GROUNDING = (
    GROUNDING
    + " La valeur doit valoir pour la situation exacte de la question : même type de contrat ou "
    "de produit, même professionnel, même étape. Une règle écrite pour un autre cas (un crédit "
    "immobilier quand la question porte sur un autre produit, un contrat de crédit quand elle "
    "porte sur une multipropriété) ne répond pas : mets alors `abstained` à vrai, même si la règle "
    "semble proche."
)
GROUNDINGS = {VARIANT: STRICT_GROUNDING}


def build_retrievers(index: Index, embedder: Embedder) -> dict[str, Retriever]:
    def dense(question: str) -> list[Passage]:
        return index.search(embedder.embed([question])[0], TOP_K)

    return {BASELINE: dense, VARIANT: dense}


def excluded_items(audit: Path = AUDIT) -> set[str]:
    """Les items sans réponse que l'audit de la v1 trouve répondus par le code."""
    return {row["id"] for row in read_jsonl(audit) if row["verdict"] == "a_une_reponse"}


def _write_summary(run_dir: Path, summary: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(
    argv: list[str] | None = None,
    git_is_clean: Callable[[], bool] = lambda: cli.git_is_clean(ROOT),
) -> None:
    parser = argparse.ArgumentParser(description="Campagne de la 006")
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--final", action="store_true", help="le run unique sur le test")
    parser.add_argument("--model", required=True, help="générateur, ex. mistral:mistral-small-2603")
    parser.add_argument("--k", type=int, default=3, help="répétitions par item et variante")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--langfuse", action="store_true", help="tracer le run dans Langfuse")
    args = parser.parse_args(argv)

    if args.split == "test" and not args.final:
        sys.exit("le split test ne se lance qu'une fois, pour le run final : ajoutez --final")
    if args.final and not git_is_clean():
        sys.exit("run final refusé : l'arbre git n'est pas propre, faites d'abord le commit de gel")

    from ailab_rag.corpus import passages
    from ailab_rag.embeddings import CachedEmbedder, MistralEmbedder
    from ailab_rag.retrieval import build_index

    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    commit = cli.current_commit(ROOT)
    excluded = excluded_items()
    # Les items écartés ne tournent pas : ils ne sont ni notés ni lus pendant l'itération.
    items = [
        i for i in read_jsonl(args.golden) if i["split"] == args.split and i["id"] not in excluded
    ]
    all_items = [i for i in read_jsonl(args.golden) if i["split"] == args.split]
    embedder = CachedEmbedder(MistralEmbedder(), CACHE_DIR / "embeddings")
    index = build_index(passages(read_jsonl(ARTICLES)), embedder)

    slug = args.model.replace(":", "-").replace("/", "-")
    run_dir = args.run_dir or EXPERIMENT_DIR / "runs" / f"{date.today()}-{slug}-{args.split}"
    tracer: Tracer = NO_TRACING
    if args.langfuse:
        tracer = cli.langfuse_tracer(ROOT, run_id=run_dir.name, split=args.split, model=args.model)
    executions = asyncio.run(
        run_campaign(
            items,
            variants=[BASELINE, VARIANT],
            model=args.model,
            repeats=args.k,
            retrievers=build_retrievers(index, embedder),
            groundings=GROUNDINGS,
            out=run_dir / "executions.jsonl",
            concurrency=args.concurrency,
            tracer=tracer,
        )
    )
    summary = summarize(
        all_items,
        executions,
        split=args.split,
        baseline=BASELINE,
        variant=VARIANT,
        exclude=excluded,
    )
    summary["abstention"] = abstention_comparison(
        all_items,
        executions,
        baseline=BASELINE,
        variant=VARIANT,
        guard_margin=GUARD_MARGIN,
        split=args.split,
        exclude=excluded,
    )
    summary["run"] = {
        "model": args.model,
        "k": args.k,
        "top_k": TOP_K,
        "variant_grounding": STRICT_GROUNDING,
        "golden": cli.display_path(args.golden, ROOT),
        "audit": cli.display_path(AUDIT, ROOT),
        "langfuse": args.langfuse,
        "commit": commit,
        "final": args.final,
    }
    # Le résumé s'écrit avant l'envoi à Langfuse, qui peut bloquer (003).
    _write_summary(run_dir, summary)
    print(json.dumps(summary["abstention"], ensure_ascii=False), flush=True)

    if isinstance(tracer, LangfuseTracing):
        flushed = cli.flush_with_deadline(tracer.flush, seconds=FLUSH_SECONDS)
        summary["run"]["langfuse_flushed"] = flushed
        _write_summary(run_dir, summary)
        if not flushed:
            print(
                f"Langfuse n'a pas tout reçu en {FLUSH_SECONDS:.0f} s : traces incomplètes, "
                "les exécutions et le résumé sont écrits.",
                file=sys.stderr,
                flush=True,
            )
            os._exit(0)


if __name__ == "__main__":
    main()
