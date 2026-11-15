"""Les adaptateurs du domaine sur le corpus et l'index d'`ailab_rag` : la même recherche dense
que `top_k_20` (index `mistral-embed`, un passage par article, cosinus exact)."""

from __future__ import annotations

from typing import Any

from ailab_evals.rag_qa_v2 import normalize_citation
from ailab_rag.embeddings import Embedder
from ailab_rag.retrieval import Index
from exp002_mcp_server.corpus.domain.entities import Article, FoundPassage
from exp002_mcp_server.corpus.domain.vo.article_number import ArticleNumber
from exp002_mcp_server.corpus.domain.vo.search_query import SearchQuery


def _article(raw: dict[str, Any]) -> Article:
    return Article(raw["id"], raw["num"], tuple(raw["path"]), raw["text"])


class IndexArticleSearch:
    def __init__(self, index: Index, embedder: Embedder, articles: list[dict[str, Any]]) -> None:
        self._index = index
        self._embedder = embedder
        self._paths = {a["id"]: tuple(a["path"]) for a in articles}

    def search(self, query: SearchQuery, k: int) -> list[FoundPassage]:
        passages = self._index.search(self._embedder.embed([query.text])[0], k)
        return [
            FoundPassage(p.article_id, p.num, self._paths.get(p.article_id, ()), p.text)
            for p in passages
        ]


class InMemoryArticleCatalog:
    """Les articles du corpus, retrouvés par leur numéro normalisé (normalisation C)."""

    def __init__(self, articles: list[dict[str, Any]]) -> None:
        self._by_number = {normalize_citation(a["num"]): _article(a) for a in articles}

    def get(self, number: ArticleNumber) -> Article | None:
        return self._by_number.get(number.value)
