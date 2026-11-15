"""Les deux ports du domaine : chercher des passages, lire un article."""

from __future__ import annotations

from typing import Protocol

from exp002_mcp_server.corpus.domain.entities import Article, FoundPassage
from exp002_mcp_server.corpus.domain.vo.article_number import ArticleNumber
from exp002_mcp_server.corpus.domain.vo.search_query import SearchQuery


class ArticleSearch(Protocol):
    def search(self, query: SearchQuery, k: int) -> list[FoundPassage]: ...


class ArticleCatalog(Protocol):
    def get(self, number: ArticleNumber) -> Article | None: ...
