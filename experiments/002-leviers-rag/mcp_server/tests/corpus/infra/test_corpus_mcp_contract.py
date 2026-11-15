"""Le contrat MCP des deux outils, par un client MCP en mémoire (comme la 001)."""

import json
from collections.abc import AsyncIterator
from typing import Any

import numpy as np
import pytest
from mcp import Client
from mcp.types import CallToolResult, TextContent

from ailab_rag.corpus import passages
from ailab_rag.retrieval import Index
from exp002_mcp_server.corpus.application.corpus_tools import CorpusTools
from exp002_mcp_server.corpus.infra.outbound.ailab_rag_corpus import (
    IndexArticleSearch,
    InMemoryArticleCatalog,
)
from exp002_mcp_server.server import create_server

pytestmark = pytest.mark.anyio

ARTICLES = [
    {
        "id": f"LEGIARTI{i}",
        "num": f"L221-{i}",
        "path": ["Partie législative", "Livre II"],
        "text": f"Texte de l'article {i}.",
    }
    for i in range(1, 9)
]


class OneHotEmbedder:
    """L'article i a le vecteur e_i ; une requête qui contient « i » vise l'article i."""

    def embed(self, texts: list[str]) -> np.ndarray:
        rows = []
        for text in texts:
            v = np.zeros(10)
            for i in range(1, 9):
                if str(i) in text:
                    v[i] = 1.0
            rows.append(v / (np.linalg.norm(v) or 1.0))
        return np.array(rows)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def corpus(max_calls: int = 6) -> CorpusTools:
    embedder = OneHotEmbedder()
    chunks = passages(ARTICLES)
    index = Index(chunks, embedder.embed([p.indexed_text for p in chunks]))
    return CorpusTools(
        IndexArticleSearch(index, embedder, ARTICLES),
        InMemoryArticleCatalog(ARTICLES),
        max_calls=max_calls,
        k=5,
    )


@pytest.fixture
async def client() -> AsyncIterator[Client]:
    async with Client(create_server(corpus()), mode="legacy") as connected:
        yield connected


def text(result: CallToolResult) -> str:
    return "".join(c.text for c in result.content if isinstance(c, TextContent))


async def call(client: Client, name: str, arguments: dict[str, Any]) -> CallToolResult:
    return await client.call_tool(name, arguments)


async def test_lists_the_two_tools_in_a_fixed_order(client):
    names = [t.name for t in (await client.list_tools()).tools]

    assert names == ["consommation_get_article", "consommation_search_articles"]


async def test_each_tool_asks_for_one_described_string(client):
    tools = {t.name: t for t in (await client.list_tools()).tools}

    for name, param in (
        ("consommation_search_articles", "query"),
        ("consommation_get_article", "num"),
    ):
        schema = tools[name].input_schema
        assert schema["required"] == [param]
        assert schema["properties"][param]["type"] == "string"
        assert schema["properties"][param]["description"]
        assert tools[name].annotations.read_only_hint is True


async def test_a_search_returns_five_passages_structured_and_as_json_text(client):
    result = await call(client, "consommation_search_articles", {"query": "article 3"})

    assert result.is_error is False
    assert len(result.structured_content["passages"]) == 5
    assert result.structured_content["passages"][0]["num"] == "L221-3"
    assert json.loads(text(result)) == result.structured_content


async def test_an_article_is_read_as_the_model_writes_its_number(client):
    result = await call(client, "consommation_get_article", {"num": "Article L. 221-4"})

    assert result.structured_content == {
        "id": "LEGIARTI4",
        "num": "L221-4",
        "path": ["Partie législative", "Livre II"],
        "text": "Texte de l'article 4.",
    }


@pytest.mark.parametrize(
    ("name", "arguments", "message"),
    [
        ("consommation_search_articles", {"query": "  "}, "La requête est vide"),
        ("consommation_get_article", {"num": "221-4"}, "n'est pas un numéro d'article"),
        ("consommation_get_article", {"num": "L999-9"}, "Aucun article L999-9"),
    ],
)
async def test_a_domain_error_is_an_execution_error_the_model_can_read(
    client, name, arguments, message
):
    result = await call(client, name, arguments)

    assert result.is_error is True
    assert message in text(result)


async def test_after_the_budget_the_server_asks_to_answer():
    async with Client(create_server(corpus(max_calls=2)), mode="legacy") as client:
        for _ in range(2):
            assert (
                await call(client, "consommation_search_articles", {"query": "1"})
            ).is_error is False

        result = await call(client, "consommation_search_articles", {"query": "1"})

    assert result.is_error is True
    assert "plafond de 2 appels" in text(result)
