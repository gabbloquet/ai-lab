import pytest

from exp002_mcp_server.corpus.application.corpus_tools import CorpusTools
from exp002_mcp_server.corpus.domain.entities import Article, FoundPassage
from exp002_mcp_server.corpus.domain.errors import (
    CallBudgetExhausted,
    InvalidQuery,
    UnknownArticle,
)
from exp002_mcp_server.corpus.domain.vo.article_number import ArticleNumber
from exp002_mcp_server.corpus.domain.vo.search_query import SearchQuery

ARTICLE = Article(
    article_id="LEGIARTI000032226842",
    num="L221-18",
    path=("Partie législative", "Livre II"),
    text="Le consommateur dispose d'un délai de quatorze jours.",
)


class FakeSearch:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def search(self, query: SearchQuery, k: int) -> list[FoundPassage]:
        self.calls.append((query.text, k))
        return [FoundPassage(ARTICLE.article_id, ARTICLE.num, ARTICLE.path, ARTICLE.text)] * k


class FakeCatalog:
    def get(self, number: ArticleNumber) -> Article | None:
        return ARTICLE if number.value == "L221-18" else None


def tools(max_calls: int = 6, k: int = 5) -> tuple[CorpusTools, FakeSearch]:
    search = FakeSearch()
    return CorpusTools(search, FakeCatalog(), max_calls=max_calls, k=k), search


def test_a_search_returns_k_passages_for_the_parsed_query():
    corpus, search = tools()

    passages = corpus.search_articles("  délai  ")

    assert len(passages) == 5 and search.calls == [("délai", 5)]


def test_an_article_is_read_by_its_number_as_the_model_writes_it():
    corpus, _ = tools()

    assert corpus.get_article("Article L. 221-18") == ARTICLE


def test_an_unknown_article_is_a_domain_error():
    corpus, _ = tools()

    with pytest.raises(UnknownArticle):
        corpus.get_article("L999-99")


def test_every_call_counts_against_the_budget_even_an_invalid_one():
    """Protocole de l'étape 8 : 6 appels au plus par question, valides ou non."""
    corpus, _ = tools(max_calls=2)
    with pytest.raises(InvalidQuery):
        corpus.search_articles("")
    corpus.get_article("L221-18")

    with pytest.raises(CallBudgetExhausted):
        corpus.search_articles("délai")
    assert corpus.calls == 3
