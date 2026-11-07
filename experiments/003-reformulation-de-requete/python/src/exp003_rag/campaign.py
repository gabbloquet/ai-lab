"""La campagne de la 003 : RAG naïf (A) contre RAG qui reformule la question avant la recherche (B).

A est exactement le RAG naïf de la 002 (briques `ailab_rag`). B passe la question au réécrivain,
puis lance la même recherche dense ; le générateur reçoit dans les deux cas la question d'origine.
Les réécritures sont calculées d'avance, avant la campagne, et gardées en cache.

    uv run --env-file .env python -m exp003_rag.campaign \\
        --split dev --model mistral:mistral-small-2603
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

from ailab_rag.answering import NAIVE_RAG, TOP_K, Retriever
from ailab_rag.campaign import read_jsonl, run_campaign, summarize
from ailab_rag.corpus import Passage
from ailab_rag.embeddings import Embedder
from ailab_rag.retrieval import Index
from ailab_rag.rewriting import REFORMULATE, QueryRewriter
from ailab_rag.tracing import NO_TRACING, LangfuseTracing, Tracer

ROOT = Path(__file__).resolve().parents[5]
EXPERIMENT_DIR = ROOT / "experiments" / "003-reformulation-de-requete"
GOLDEN_DIR = ROOT / "domains/droit-consommation/golden/rag-qa/v1"
ARTICLES = ROOT / "domains/droit-consommation/data/v1/articles.jsonl"
CACHE_DIR = ROOT / ".cache" / "ailab_rag"

BASELINE = NAIVE_RAG
VARIANT = "query_rewrite"
REWRITER = "google:gemini-3.8-flash"


def build_retrievers(
    index: Index, embedder: Embedder, rewriter: QueryRewriter, k: int = TOP_K
) -> dict[str, Retriever]:
    def naive(question: str) -> list[Passage]:
        return index.search(embedder.embed([question])[0], k)

    def rewriting(question: str) -> list[Passage]:
        return index.search(embedder.embed([rewriter.rewrite(question)])[0], k)

    return {BASELINE: naive, VARIANT: rewriting}


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    return str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _git_is_clean() -> bool:
    return _git("status", "--porcelain") == ""


def _langfuse_tracer(run_id: str, split: str, model: str) -> LangfuseTracing:
    from langfuse import Langfuse

    from ailab_evals.langfuse_setup import check_reachable, credentials

    base_url, public_key, secret_key = credentials(ROOT / "infra/langfuse/.env")
    check_reachable(base_url)
    client = Langfuse(public_key=public_key, secret_key=secret_key, base_url=base_url)
    return LangfuseTracing(client, run_id=run_id, split=split, model=model)


def main(argv: list[str] | None = None, git_is_clean: Callable[[], bool] = _git_is_clean) -> None:
    parser = argparse.ArgumentParser(description="Campagne de la 003")
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--final", action="store_true", help="le run unique sur le test")
    parser.add_argument("--model", required=True, help="générateur, ex. mistral:mistral-small-2603")
    parser.add_argument("--rewriter", default=REWRITER)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--golden", type=Path, default=None)
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
    golden = args.golden or GOLDEN_DIR / (
        "items-dev.jsonl" if args.split == "dev" else "items.jsonl"
    )
    items = [i for i in read_jsonl(golden) if i["split"] == args.split]
    embedder = CachedEmbedder(MistralEmbedder(), CACHE_DIR / "embeddings")
    index = build_index(passages(read_jsonl(ARTICLES)), embedder)
    rewriter = QueryRewriter(args.rewriter, REFORMULATE, CACHE_DIR / "rewrites")
    rewriter.rewrite_all([i["question"] for i in items])

    slug = args.model.replace(":", "-").replace("/", "-")
    run_dir = args.run_dir or EXPERIMENT_DIR / "runs" / f"{date.today()}-{slug}-{args.split}"
    tracer: Tracer = NO_TRACING
    if args.langfuse:
        tracer = _langfuse_tracer(run_dir.name, args.split, args.model)
    executions = asyncio.run(
        run_campaign(
            items,
            variants=[BASELINE, VARIANT],
            model=args.model,
            repeats=args.k,
            retrievers=build_retrievers(index, embedder, rewriter),
            out=run_dir / "executions.jsonl",
            concurrency=args.concurrency,
            tracer=tracer,
        )
    )
    if isinstance(tracer, LangfuseTracing):
        tracer.flush()
    summary = summarize(items, executions, split=args.split, baseline=BASELINE, variant=VARIANT)
    summary["run"] = {
        "model": args.model,
        "rewriter": args.rewriter,
        "k": args.k,
        "golden": _display_path(golden),
        "langfuse": args.langfuse,
        "commit": _git("rev-parse", "HEAD"),
        "final": args.final,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary["comparison"], ensure_ascii=False))


if __name__ == "__main__":
    main()
