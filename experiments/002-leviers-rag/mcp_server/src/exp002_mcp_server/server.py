"""Le serveur MCP de l'étape 8 de la 002, en stdio : un processus par question, donc un plafond
d'appels par question (protocole de l'étape 8). Les identifiants (MISTRAL_API_KEY, pour les
embeddings des requêtes) viennent de l'environnement : pas d'OAuth en stdio.

    uv run --env-file .env exp002-mcp-server
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from exp002_mcp_server.corpus.application.corpus_tools import CorpusTools
from exp002_mcp_server.corpus.infra.inbound.mcp.corpus_mcp_tools import register_corpus_tools

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_ARTICLES = ROOT / "domains/droit-consommation/data/v1/articles.jsonl"
DEFAULT_CACHE = ROOT / ".cache/ailab_rag/embeddings"
MAX_CALLS = 6
K = 5


def create_server(corpus: CorpusTools) -> MCPServer:
    server = MCPServer(name="consommation-mcp", version="0.1.0")
    register_corpus_tools(server, corpus)
    return server


def corpus_from_files(
    articles_path: Path, cache_dir: Path, *, max_calls: int, k: int
) -> CorpusTools:
    from ailab_rag.corpus import passages
    from ailab_rag.embeddings import CachedEmbedder, MistralEmbedder
    from ailab_rag.retrieval import build_index
    from exp002_mcp_server.corpus.infra.outbound.ailab_rag_corpus import (
        IndexArticleSearch,
        InMemoryArticleCatalog,
    )

    articles = [json.loads(line) for line in articles_path.read_text("utf-8").splitlines() if line]
    embedder = CachedEmbedder(MistralEmbedder(), cache_dir)
    index = build_index(passages(articles), embedder)
    return CorpusTools(
        IndexArticleSearch(index, embedder, articles),
        InMemoryArticleCatalog(articles),
        max_calls=max_calls,
        k=k,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serveur MCP de l'étape 8 de la 002 (stdio)")
    parser.add_argument("--articles", type=Path, default=DEFAULT_ARTICLES)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--max-calls", type=int, default=MAX_CALLS)
    parser.add_argument("--k", type=int, default=K)
    args = parser.parse_args(argv)
    # stdout porte le protocole : les journaux vont sur stderr.
    logging.basicConfig(level=logging.WARNING)
    corpus = corpus_from_files(args.articles, args.cache_dir, max_calls=args.max_calls, k=args.k)
    create_server(corpus).run("stdio")


if __name__ == "__main__":
    main()
