import pytest

from exp002_mcp_server.corpus.domain.errors import InvalidArticleNumber, InvalidQuery
from exp002_mcp_server.corpus.domain.vo.article_number import ArticleNumber
from exp002_mcp_server.corpus.domain.vo.search_query import MAX_QUERY_CHARS, SearchQuery


@pytest.mark.parametrize(
    "written", ["L221-18", "L. 221-18", "l221-18", "Article L. 221-18", "art. L221-18", " L221-18 "]
)
def test_reads_the_ways_a_model_writes_an_article_number(written):
    assert ArticleNumber.parse(written).value == "L221-18"


@pytest.mark.parametrize("written", ["R313-2", "D312-19", "L242-18-8", "L132-24-1"])
def test_keeps_the_numbers_of_the_code(written):
    assert ArticleNumber.parse(written).value == written


@pytest.mark.parametrize("written", ["", "221-18", "X221-18", "L", "L221-18; DROP", "L-221"])
def test_rejects_what_is_not_an_article_number(written):
    with pytest.raises(InvalidArticleNumber):
        ArticleNumber.parse(written)


def test_a_query_keeps_its_words_without_the_surrounding_spaces():
    assert SearchQuery.parse("  délai de rétractation  ").text == "délai de rétractation"


@pytest.mark.parametrize("written", ["", "   ", "x" * (MAX_QUERY_CHARS + 1)])
def test_rejects_an_empty_or_too_long_query(written):
    with pytest.raises(InvalidQuery):
        SearchQuery.parse(written)


def test_accepts_a_query_at_the_length_limit():
    assert len(SearchQuery.parse("x" * MAX_QUERY_CHARS).text) == MAX_QUERY_CHARS
