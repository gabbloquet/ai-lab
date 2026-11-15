"""Les deux cas d'usage du serveur, et le plafond d'appels d'une session (protocole de l'étape 8 :
6 appels au plus par question, chaque processus stdio servant une seule question)."""

from __future__ import annotations

from exp002_mcp_server.corpus.domain.entities import Article, FoundPassage
from exp002_mcp_server.corpus.domain.errors import CallBudgetExhausted, UnknownArticle
from exp002_mcp_server.corpus.domain.port.corpus_ports import ArticleCatalog, ArticleSearch
from exp002_mcp_server.corpus.domain.vo.article_number import ArticleNumber
from exp002_mcp_server.corpus.domain.vo.search_query import SearchQuery


class CorpusTools:
    def __init__(
        self, search: ArticleSearch, catalog: ArticleCatalog, *, max_calls: int, k: int
    ) -> None:
        self._search = search
        self._catalog = catalog
        self._max_calls = max_calls
        self._k = k
        self.calls = 0

    def _count(self) -> None:
        """Tout appel compte, même invalide : le plafond borne le coût, pas les seuls succès."""
        self.calls += 1
        if self.calls > self._max_calls:
            raise CallBudgetExhausted(self._max_calls)

    def search_articles(self, query: str) -> list[FoundPassage]:
        self._count()
        return self._search.search(SearchQuery.parse(query), self._k)

    def get_article(self, number: str) -> Article:
        self._count()
        parsed = ArticleNumber.parse(number)
        article = self._catalog.get(parsed)
        if article is None:
            raise UnknownArticle(parsed.value)
        return article
