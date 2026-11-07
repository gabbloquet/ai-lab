"""La campagne de la 002 : ligne de commande, chemins et garde-fous du run final. La boucle de
campagne et le résumé sont dans `ailab_rag.campaign`, partagés par la série.

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
from collections.abc import Callable
from datetime import date
from pathlib import Path

from ailab_rag.answering import CLOSED_BOOK, NAIVE_RAG, TOP_K, Retriever
from ailab_rag.campaign import read_jsonl as _read_jsonl
from ailab_rag.campaign import run_campaign, summarize
from ailab_rag.tracing import NO_TRACING, LangfuseTracing, Tracer

ROOT = Path(__file__).resolve().parents[5]
EXPERIMENT_DIR = ROOT / "experiments" / "002-rag-naif-vs-modele-seul"
GOLDEN_DIR = ROOT / "domains/droit-consommation/golden/rag-qa/v1"
ARTICLES = ROOT / "domains/droit-consommation/data/v1/articles.jsonl"


def display_path(path: Path) -> str:
    """Le chemin à citer dans un rapport : relatif au dépôt quand il y est."""
    resolved = path.resolve()
    return str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)


def default_golden(split: str) -> Path:
    """Le dev itère sur `items-dev.jsonl`, publié dès sa relecture ; le run final lit
    `items.jsonl`, qui n'existe qu'une fois les 200 items relus."""
    return GOLDEN_DIR / ("items-dev.jsonl" if split == "dev" else "items.jsonl")


def current_commit() -> str:
    """Le commit sur lequel tourne un run : le rapport du run final cite le commit de gel."""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return head.stdout.strip()


def _git_is_clean() -> bool:
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return status.stdout.strip() == ""


def _retriever() -> Retriever:
    from ailab_rag.corpus import passages
    from ailab_rag.embeddings import CachedEmbedder, MistralEmbedder
    from ailab_rag.retrieval import build_index

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
    parser.add_argument("--golden", type=Path, default=None)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--langfuse", action="store_true", help="tracer le run dans Langfuse")
    args = parser.parse_args(argv)

    if args.split == "test" and not args.final:
        sys.exit("le split test ne se lance qu'une fois, pour le run final : ajoutez --final")
    if args.final and not git_is_clean():
        sys.exit("run final refusé : l'arbre git n'est pas propre, faites d'abord le commit de gel")

    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    golden = args.golden or default_golden(args.split)
    if not golden.exists():
        sys.exit(f"{golden} n'existe pas : publiez d'abord le golden set de ce split")
    items = [i for i in _read_jsonl(golden) if i["split"] == args.split]
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
        "golden": display_path(golden),
        "langfuse": args.langfuse,
        "commit": current_commit(),
        "final": args.final,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary["comparison"], ensure_ascii=False))


if __name__ == "__main__":
    main()
