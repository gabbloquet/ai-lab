"""Les deux outils MCP du serveur. Une erreur du domaine devient une erreur d'exécution
(`isError`) que le modèle lit et peut corriger ; le résultat porte son `structuredContent` et le
même JSON en texte (référentiel MCP du dépôt, § 2)."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from exp002_mcp_server.corpus.application.corpus_tools import CorpusTools
from exp002_mcp_server.corpus.domain.entities import Article, FoundPassage
from exp002_mcp_server.corpus.domain.errors import (
    DOMAIN_ERRORS,
    CallBudgetExhausted,
    DomainError,
    InvalidArticleNumber,
    InvalidQuery,
    UnknownArticle,
)
from exp002_mcp_server.corpus.domain.vo.search_query import MAX_QUERY_CHARS

SEARCH_TOOL = "consommation_search_articles"
GET_TOOL = "consommation_get_article"
INTERNAL_ERROR = "Erreur interne pendant l'exécution de l'outil. Réessaie plus tard."
READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, destructive_hint=False, open_world_hint=False
)

logger = logging.getLogger(__name__)

Query = Annotated[
    str,
    Field(
        description="Ce que tu cherches dans le Code de la consommation, en français : une "
        f"question ou des mots-clés ({MAX_QUERY_CHARS} caractères au plus)."
    ),
]
Number = Annotated[
    str,
    Field(description="Numéro de l'article, tel que le code l'écrit : par exemple « L. 221-18 »."),
]


def error_message(error: DomainError) -> str:
    """Ce que le modèle lit pour chaque erreur, avec ce qu'il peut faire ensuite."""
    match error:
        case InvalidQuery(reason="empty"):
            return "La requête est vide. Écris ce que tu cherches."
        case InvalidQuery():
            return f"La requête dépasse {MAX_QUERY_CHARS} caractères. Raccourcis-la."
        case InvalidArticleNumber():
            return (
                f"« {error.written} » n'est pas un numéro d'article du code. "
                "Écris-le comme « L. 221-18 », ou cherche l'article avec "
                f"{SEARCH_TOOL}."
            )
        case UnknownArticle():
            return (
                f"Aucun article {error.number} dans le Code de la consommation. "
                f"Cherche-le avec {SEARCH_TOOL}."
            )
        case CallBudgetExhausted():
            return (
                f"Tu as atteint le plafond de {error.max_calls} appels d'outil pour cette "
                "question. Réponds maintenant avec ce que tu as trouvé, ou abstiens-toi."
            )
    return INTERNAL_ERROR


def _passage(p: FoundPassage) -> dict[str, Any]:
    return {"id": p.article_id, "num": p.num, "path": list(p.path), "text": p.text}


def _article(a: Article) -> dict[str, Any]:
    return {"id": a.article_id, "num": a.num, "path": list(a.path), "text": a.text}


def _run(tool: Callable[[], dict[str, Any]]) -> CallToolResult:
    try:
        payload = tool()
    except DOMAIN_ERRORS as error:
        return CallToolResult(
            content=[TextContent(type="text", text=error_message(error))], is_error=True
        )
    except Exception:
        logger.exception("Erreur inattendue pendant l'exécution d'un outil")
        return CallToolResult(
            content=[TextContent(type="text", text=INTERNAL_ERROR)], is_error=True
        )
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=payload)


def register_corpus_tools(server: MCPServer, corpus: CorpusTools) -> None:
    # Enregistrés dans un ordre fixe : `tools/list` reste déterministe (révision 2026-07-28).
    @server.tool(
        name=GET_TOOL,
        description="Rend le texte complet d'un article du Code de la consommation, à partir de "
        "son numéro. Utile pour lire un article cité par un autre, ou un article dont la "
        "recherche n'a montré qu'un passage.",
        annotations=READ_ONLY,
    )
    def get_article(num: Number) -> CallToolResult:
        return _run(lambda: _article(corpus.get_article(num)))

    @server.tool(
        name=SEARCH_TOOL,
        description="Cherche dans le Code de la consommation les 5 passages les plus proches de "
        "la requête, par similarité de sens. Chaque passage donne le numéro de son article, sa "
        "place dans le code et son texte. Reformule et relance si les passages ne répondent pas.",
        annotations=READ_ONLY,
    )
    def search_articles(query: Query) -> CallToolResult:
        return _run(lambda: {"passages": [_passage(p) for p in corpus.search_articles(query)]})
