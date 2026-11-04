"""Boucle d'agent de la 001 : une question, un serveur MCP, tous les appels émis enregistrés."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, capture_run_messages
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits

# Paramètres fixés par le protocole de la 001 (README, section « Boucle d'agent »).
MAX_TOOL_CALLS = 10
MAX_RETRIES = 2
TOOL_ERROR_BEHAVIOR = "failed"
TEMPERATURE = 0.0
# Garde-fou seulement : le plafond réel est MAX_TOOL_CALLS, compté par la boucle.
SAFETY_REQUEST_LIMIT = 30

TOOL_CALL_LIMIT_ERROR = f"tool_call_limit: more than {MAX_TOOL_CALLS} tool calls"


@dataclass(frozen=True)
class Execution:
    """Exécution observée, dans la forme canonique de la spec tool-selection v1 (§ 3.2)."""

    item_id: str
    variant: str
    model: str
    repeat: int
    calls: list[dict[str, Any]]
    usage: dict[str, int]
    error: str | None
    answer: str | None

    def to_spec(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "variant": self.variant,
            "model": self.model,
            "repeat": self.repeat,
            "calls": self.calls,
            "usage": self.usage,
            "error": self.error,
        }


async def run_item(
    *,
    item_id: str,
    question: str,
    store_id: str,
    variant: str,
    url: str,
    model: str | Model,
    system_prompt: str,
    repeat: int = 0,
    reraise: Callable[[BaseException], bool] = lambda error: False,
) -> Execution:
    """`reraise` laisse passer une erreur d'infrastructure (limite de débit) au lieu de la noter."""
    toolset = MCPToolset(url, tool_error_behavior=TOOL_ERROR_BEHAVIOR, max_retries=MAX_RETRIES)
    agent = Agent(
        model,
        toolsets=[toolset],
        # Un outil inconnu est rejeté par l'agent, pas par le toolset : même budget des deux côtés.
        retries=MAX_RETRIES,
        instructions=system_prompt.format(store_id=store_id),
        model_settings=ModelSettings(temperature=TEMPERATURE),
    )
    error: str | None = None
    answer: str | None = None
    emitted = 0
    # capture_run_messages garde l'historique même si le run lève une exception.
    with capture_run_messages() as messages:
        try:
            limits = UsageLimits(request_limit=SAFETY_REQUEST_LIMIT)
            async with agent.iter(question, usage_limits=limits) as run:
                async for node in run:
                    if Agent.is_call_tools_node(node):
                        emitted += _count_calls(node.model_response)
                        if emitted > MAX_TOOL_CALLS:
                            # On sort avant d'exécuter les appels de cette réponse.
                            error = TOOL_CALL_LIMIT_ERROR
                            break
                if error is None and run.result is not None:
                    answer = str(run.result.output)
        except Exception as exc:
            if reraise(exc):
                raise
            error = f"{type(exc).__name__}: {exc}"
    return Execution(
        item_id=item_id,
        variant=variant,
        model=model if isinstance(model, str) else model.model_name,
        repeat=repeat,
        calls=emitted_calls(messages),
        usage=usage_of(messages),
        error=error,
        answer=answer,
    )


def emitted_calls(messages: list[ModelMessage]) -> list[dict[str, Any]]:
    """Tous les appels émis par le modèle, dans l'ordre, y compris ceux qui ont été rejetés."""
    return [
        {"tool": part.tool_name, "args": _args(part)}
        for message in messages
        if isinstance(message, ModelResponse)
        for part in message.parts
        if isinstance(part, ToolCallPart)
    ]


def usage_of(messages: list[ModelMessage]) -> dict[str, int]:
    responses = [message for message in messages if isinstance(message, ModelResponse)]
    return {
        "input_tokens": sum(response.usage.input_tokens for response in responses),
        "output_tokens": sum(response.usage.output_tokens for response in responses),
    }


def _count_calls(response: ModelResponse) -> int:
    return sum(isinstance(part, ToolCallPart) for part in response.parts)


def _args(part: ToolCallPart) -> dict[str, Any]:
    if isinstance(part.args, str):
        try:
            parsed = json.loads(part.args)
        except json.JSONDecodeError:
            # La spec ne prévoit pas ce cas : on garde le texte, qui ne satisfait aucun motif.
            return {"_unparsed": part.args}
        return parsed if isinstance(parsed, dict) else {"_unparsed": part.args}
    return dict(part.args or {})
