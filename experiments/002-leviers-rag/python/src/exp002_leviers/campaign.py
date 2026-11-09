"""Le lanceur du run consolidé de la 002 : les six configurations gelées des étapes, sur le même
golden set (`rag-qa/v4`), pour un générateur.

Avant tout appel payant : garde-fous du run final, puis contrôle de reproduction sur les caches
seuls. Ensuite, les seuls appels hors générateur : les embeddings, les reformulations
(`gemini-3.8-flash`) et les notes de reclassement (Cohere) des questions absentes des caches,
faits d'avance. Les items que l'audit de la v1 trouve répondus ne tournent pas.

    uv run --env-file .env python -m exp002_leviers.campaign \\
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
from ailab_rag.campaign import read_jsonl, run_campaign
from ailab_rag.tracing import NO_TRACING, LangfuseTracing, Tracer
from exp002_leviers.analysis import analyze
from exp002_leviers.configurations import CONFIGURATIONS, GROUNDINGS, build_retrievers
from exp002_leviers.paths import ARTICLES, AUDIT, CACHE_DIR, EXPERIMENT_DIR, GOLDEN, ROOT
from exp002_leviers.reproduction import reproduces as offline_reproduction
from exp003_rag.campaign import REWRITE_PROMPT, REWRITER
from exp005_rag.campaign import RERANKER, rerank_all
from exp006_rag.campaign import excluded_items

# Délai laissé à Langfuse pour recevoir les dernières traces, une fois le résumé écrit.
FLUSH_SECONDS = 120.0


def _write_summary(run_dir: Path, summary: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(
    argv: list[str] | None = None,
    git_is_clean: Callable[[], bool] = lambda: cli.git_is_clean(ROOT),
    reproduces: Callable[[], bool] = offline_reproduction,
) -> None:
    parser = argparse.ArgumentParser(description="Run consolidé de la 002")
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--final", action="store_true", help="le run unique sur le test")
    parser.add_argument("--model", required=True, help="générateur, ex. mistral:mistral-small-2603")
    parser.add_argument("--k", type=int, default=3, help="répétitions par item et configuration")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
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
        sys.exit("COHERE_API_KEY manque : rerank_cohere passe par l'API Cohere (.env)")
    if not reproduces():
        sys.exit("run refusé : le contrôle de reproduction des configurations gelées échoue")

    from ailab_rag.corpus import passages
    from ailab_rag.embeddings import CachedEmbedder, MistralEmbedder
    from ailab_rag.reranking import CohereReranker
    from ailab_rag.retrieval import build_index
    from ailab_rag.rewriting import QueryRewriter

    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    commit = cli.current_commit(ROOT)
    excluded = excluded_items(AUDIT)
    all_items = read_jsonl(args.golden)
    items = [i for i in all_items if i["split"] == args.split and i["id"] not in excluded]
    questions = [i["question"] for i in items]

    embedder = CachedEmbedder(MistralEmbedder(), CACHE_DIR / "embeddings")
    index = build_index(passages(read_jsonl(ARTICLES)), embedder)
    rewriter = QueryRewriter(REWRITER, REWRITE_PROMPT, CACHE_DIR / "rewrites")
    rewriter.rewrite_all(questions)
    reranker = CohereReranker(RERANKER, api_key=api_key)
    retrievers = build_retrievers(index, embedder, rewriter, reranker, CACHE_DIR / "rerank")
    rerank_all(retrievers, questions)

    slug = args.model.replace(":", "-").replace("/", "-")
    run_dir = args.run_dir or EXPERIMENT_DIR / "runs" / f"{date.today()}-{slug}-{args.split}"
    tracer: Tracer = NO_TRACING
    if args.langfuse:
        tracer = cli.langfuse_tracer(ROOT, run_id=run_dir.name, split=args.split, model=args.model)
    executions = asyncio.run(
        run_campaign(
            items,
            variants=list(CONFIGURATIONS),
            model=args.model,
            repeats=args.k,
            retrievers=retrievers,
            groundings=GROUNDINGS,
            out=run_dir / "executions.jsonl",
            concurrency=args.concurrency,
            tracer=tracer,
        )
    )
    summary = analyze(all_items, executions, split=args.split, exclude=excluded)
    summary["run"] = {
        "model": args.model,
        "k": args.k,
        "configurations": list(CONFIGURATIONS),
        "rewriter": REWRITER,
        "reranker": f"cohere:{RERANKER}",
        "golden": cli.display_path(args.golden, ROOT),
        "audit": cli.display_path(AUDIT, ROOT),
        "langfuse": args.langfuse,
        "commit": commit,
        "final": args.final,
    }
    # Le résumé s'écrit avant l'envoi à Langfuse, qui peut bloquer (003).
    _write_summary(run_dir, summary)
    for c in summary["comparisons"]:
        print(
            f"{c['variant']} − {c['baseline']} : {c['delta']:+.3f} "
            f"[{c['ci_low']:+.3f} ; {c['ci_high']:+.3f}] p_holm={c['p_holm']:.3f} "
            f"{c['verdict_holm']}",
            flush=True,
        )
    print(f"abstention : {summary['abstention']['verdict']}", flush=True)

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
