"""La campagne de la 005 : RAG à 20 passages denses (A) contre 50 candidats reclassés par Cohere,
dont les 5 mieux notés vont au générateur (B).

A est exactement le B gelé de la 004 : le RAG naïf de la 002 avec top-k = 20. B cherche avec la
même question dans le même index, reclasse les 50 premiers passages (`ailab_rag.reranking`) et
garde les 5 mieux notés. Les classements de B sont calculés d'avance, avant la campagne, et
gardés en cache.

    uv run --env-file .env python -m exp005_rag.campaign \\
        --split dev --model mistral:mistral-small-2603
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path
from typing import Any

from ailab_rag import cli
from ailab_rag.answering import TOP_K, Retriever
from ailab_rag.campaign import durations, read_jsonl, run_campaign, summarize
from ailab_rag.corpus import Passage
from ailab_rag.embeddings import Embedder
from ailab_rag.reranking import POOL, CohereReranker, Reranker, RerankingRetriever
from ailab_rag.retrieval import Index
from ailab_rag.tracing import NO_TRACING, LangfuseTracing, Tracer

ROOT = Path(__file__).resolve().parents[5]
EXPERIMENT_DIR = ROOT / "experiments" / "005-reclassement"
GOLDEN_DIR = ROOT / "domains/droit-consommation/golden/rag-qa/v1"
ARTICLES = ROOT / "domains/droit-consommation/data/v1/articles.jsonl"
CACHE_DIR = ROOT / ".cache" / "ailab_rag"
# Délai laissé à Langfuse pour recevoir les dernières traces, une fois le résumé écrit.
FLUSH_SECONDS = 120.0

# Redéclarés plutôt qu'importés d'exp004_rag : une expérience ne dépend pas du code d'une autre.
BASELINE = "top_k_20"
BASELINE_TOP_K = 20
VARIANT = "rerank_cohere"
# Modèle retenu par la pré-étude (README) ; il ne change pas pendant l'itération.
RERANKER = "rerank-v5.0-pro"


def build_retrievers(
    index: Index, embedder: Embedder, reranker: Reranker, cache_dir: Path
) -> dict[str, Retriever]:
    def dense(question: str) -> list[Passage]:
        return index.search(embedder.embed([question])[0], BASELINE_TOP_K)

    return {
        BASELINE: dense,
        VARIANT: RerankingRetriever(index, embedder, reranker, cache_dir=cache_dir),
    }


def rerank_all(retrievers: dict[str, Retriever], questions: Iterable[str]) -> None:
    """Reclasse chaque question une fois, avant la campagne : ensuite, B lit le cache, et le
    modèle de reclassement n'est plus appelé pendant les exécutions."""
    for question in dict.fromkeys(questions):
        retrievers[VARIANT](question)


def _write_summary(run_dir: Path, summary: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(
    argv: list[str] | None = None,
    git_is_clean: Callable[[], bool] = lambda: cli.git_is_clean(ROOT),
) -> None:
    parser = argparse.ArgumentParser(description="Campagne de la 005")
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--final", action="store_true", help="le run unique sur le test")
    parser.add_argument("--model", required=True, help="générateur, ex. mistral:mistral-small-2603")
    parser.add_argument("--k", type=int, default=3, help="répétitions par item et variante")
    parser.add_argument("--golden", type=Path, default=None)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--langfuse", action="store_true", help="tracer le run dans Langfuse")
    args = parser.parse_args(argv)

    if args.split == "test" and not args.final:
        sys.exit("le split test ne se lance qu'une fois, pour le run final : ajoutez --final")
    if args.final and not git_is_clean():
        sys.exit("run final refusé : l'arbre git n'est pas propre, faites d'abord le commit de gel")
    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        sys.exit("COHERE_API_KEY manque : le reclassement de B passe par l'API Cohere (.env)")

    from ailab_rag.corpus import passages
    from ailab_rag.embeddings import CachedEmbedder, MistralEmbedder
    from ailab_rag.retrieval import build_index

    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    commit = cli.current_commit(ROOT)
    golden = args.golden or GOLDEN_DIR / (
        "items-dev.jsonl" if args.split == "dev" else "items.jsonl"
    )
    items = [i for i in read_jsonl(golden) if i["split"] == args.split]
    embedder = CachedEmbedder(MistralEmbedder(), CACHE_DIR / "embeddings")
    index = build_index(passages(read_jsonl(ARTICLES)), embedder)
    reranker = CohereReranker(RERANKER, api_key=api_key)
    retrievers = build_retrievers(index, embedder, reranker, CACHE_DIR / "rerank")
    rerank_all(retrievers, [i["question"] for i in items])

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
            retrievers=retrievers,
            out=run_dir / "executions.jsonl",
            concurrency=args.concurrency,
            tracer=tracer,
        )
    )
    summary = summarize(items, executions, split=args.split, baseline=BASELINE, variant=VARIANT)
    summary["run"] = {
        "model": args.model,
        "k": args.k,
        "baseline_top_k": BASELINE_TOP_K,
        "reranker": reranker.name,
        "pool": POOL,
        "variant_top_k": TOP_K,
        # Appels à Cohere de ce run (questions absentes du cache), attente de rythme exclue.
        "rerank_calls": len(reranker.latencies),
        "rerank_s": durations(reranker.latencies),
        "golden": cli.display_path(golden, ROOT),
        "langfuse": args.langfuse,
        "commit": commit,
        "final": args.final,
    }
    # Le résumé s'écrit avant l'envoi à Langfuse, qui peut bloquer (003).
    _write_summary(run_dir, summary)
    print(json.dumps(summary["comparison"], ensure_ascii=False), flush=True)

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
            # Les gestionnaires de sortie de Langfuse rebloqueraient le processus.
            os._exit(0)


if __name__ == "__main__":
    main()
