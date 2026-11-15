"""Le RAG agentique de l'étape 8 de la 002 : le modèle cherche lui-même, par les outils MCP du
serveur `exp002_mcp_server`, puis répond dans le même format que les autres variantes.

Le contexte noté est la suite des articles que les outils ont rendus, dans l'ordre des appels
(spec rag-qa v2, § 3.2), et `tool_calls` le nombre d'appels à ces outils. Le prompt système est
celui des autres variantes, suivi d'une consigne sur les outils : c'est la seule différence
d'instruction avec `top_k_20` (README de la 002, « Étape 8 »).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, capture_run_messages
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from ailab_rag.answering import ModelAnswer, _usage
from ailab_rag.prompting import SYSTEM_PROMPT, question_line

AGENTIC_VARIANT = "agentic_rag"
SEARCH_TOOL = "consommation_search_articles"
GET_TOOL = "consommation_get_article"
TOOL_NAMES = frozenset({SEARCH_TOOL, GET_TOOL})
MAX_CALLS = 6
ROOT = Path(__file__).resolve().parents[3]

# Cycle 1 de l'étape 8 : la consigne d'usage des outils, écrite avant tout run `dev`.
AGENTIC_GUIDANCE = (
    f"Tu n'as pas le texte du code sous les yeux : cherche-le avec l'outil {SEARCH_TOOL}, qui "
    "rend les 5 passages les plus proches de ta requête. Si les passages ne répondent pas, "
    f"reformule et relance. Pour lire un article cité ou coupé, utilise {GET_TOOL}. Tu as "
    f"{MAX_CALLS} appels d'outil au plus. Réponds à partir de ce que les outils t'ont rendu ; "
    "si tu n'y trouves pas la valeur demandée, mets `abstained` à vrai."
)


def stdio_toolsets() -> list[Any]:
    """Le serveur MCP du dépôt, lancé dans un processus neuf pour chaque question : le plafond
    d'appels vaut donc par question. Les identifiants passent par l'environnement."""
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport
    from pydantic_ai.mcp import MCPToolset

    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "exp002_mcp_server.server"],
        env=dict(os.environ),
        cwd=str(ROOT),
        keep_alive=False,
    )
    return [MCPToolset(Client(transport))]


def _returned_articles(content: Any) -> list[str]:
    """Les `id` d'articles d'un résultat d'outil : un dict, son JSON, ou une liste de blocs."""
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            return []
    if isinstance(content, list):
        return [a for block in content for a in _returned_articles(block)]
    if not isinstance(content, dict):
        text = getattr(content, "text", None)
        return _returned_articles(text) if isinstance(text, str) else []
    if "passages" in content:
        return [p["id"] for p in content["passages"] if isinstance(p, dict) and "id" in p]
    return [content["id"]] if isinstance(content.get("id"), str) else []


async def run_agentic_item(
    item: dict,
    *,
    model: str | Model,
    repeat: int,
    toolsets: Callable[[], Sequence[Any]] = stdio_toolsets,
    settings: ModelSettings | None = None,
    reraise: Callable[[BaseException], bool] = lambda error: False,
    clock: Callable[[], float] = time.perf_counter,
    guidance: str = AGENTIC_GUIDANCE,
) -> dict[str, Any]:
    """Une exécution agentique, à la forme canonique de la spec rag-qa v2 (§ 3.2). Les outils
    ont droit à `MAX_CALLS` relances (une erreur d'outil revient au modèle) ; la sortie, comme
    pour les autres variantes, n'a pas de seconde chance."""
    agent = Agent(
        model,
        output_type=ModelAnswer,
        instructions=f"{SYSTEM_PROMPT}\n\n{guidance}",
        retries={"tools": MAX_CALLS, "output": 0},
        toolsets=list(toolsets()),
        model_settings=settings,
    )
    output: ModelAnswer | None = None
    error: str | None = None
    with capture_run_messages() as messages:
        started = clock()
        try:
            output = (await agent.run(question_line(item["question"]))).output
        except Exception as exc:
            if reraise(exc):
                raise
            error = f"{type(exc).__name__}: {exc}"
        latency = clock() - started

    called = [
        part.tool_name
        for message in messages
        if isinstance(message, ModelResponse)
        for part in message.parts
        if isinstance(part, ToolCallPart) and part.tool_name in TOOL_NAMES
    ]
    calls = len(called)
    context = [
        article
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, ToolReturnPart) and part.tool_name in TOOL_NAMES
        for article in _returned_articles(part.content)
    ]
    return {
        "item_id": item["id"],
        "variant": AGENTIC_VARIANT,
        "model": model if isinstance(model, str) else model.model_name,
        "repeat": repeat,
        "answer": output.answer if output else "",
        "abstained": output.abstained if output else False,
        "cited": list(output.cited) if output else [],
        "context": context,
        "usage": _usage(messages),
        "latency_s": latency,
        "cost_usd": None,
        "tool_calls": calls,
        "error": error,
        "extra": {
            "search_calls": called.count(SEARCH_TOOL),
            "get_calls": called.count(GET_TOOL),
            "guidance_sha256": hashlib.sha256(guidance.encode()).hexdigest()[:12],
        },
    }
