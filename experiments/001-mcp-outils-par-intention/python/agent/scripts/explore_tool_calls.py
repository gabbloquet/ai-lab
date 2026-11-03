"""Test exploratoire de la 001 : comment Pydantic AI enregistre-t-il les appels d'outils MCP ?

Un faux modèle (FunctionModel) émet des appels choisis à l'avance vers un vrai serveur MCP.
On vérifie que l'historique garde chaque appel émis, y compris ceux qui sont rejetés, et ce que
voit le modèle en retour. Aucun appel à un vrai modèle, donc ni coût ni hasard.

Usage, avec un serveur lancé à part (par défaut le serveur Java, variante intent) :
    PYDANTIC_AI_NO_BANNER=1 uv run python \
        experiments/001-mcp-outils-par-intention/python/agent/scripts/explore_tool_calls.py \
        --url http://127.0.0.1:8082/mcp
"""

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import anyio
from pydantic_ai import Agent, capture_run_messages
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.usage import UsageLimits

# Les paramètres que le protocole de la 001 fixe pour la boucle d'agent.
TOOL_ERROR_BEHAVIOR = "failed"
MAX_RETRIES = 1
REQUEST_LIMIT = 10


@dataclass(frozen=True)
class Scenario:
    name: str
    calls: list[ToolCallPart]
    repeat_last_call: bool = False


SCENARIOS = [
    Scenario("argument requis absent", [ToolCallPart("get_product_details", {})]),
    Scenario("argument du mauvais type", [ToolCallPart("get_product_details", {"sku": 42})]),
    Scenario("arguments JSON mal formés", [ToolCallPart("get_product_details", '{"sku": "P-1')]),
    Scenario("outil inventé", [ToolCallPart("get_stock_level", {"sku": "P-15695"})]),
    Scenario(
        "erreur métier du serveur",
        [ToolCallPart("check_availability", {"sku": "P-38893", "storeId": "S99"})],
    ),
    Scenario(
        "budget épuisé : le même appel invalide, sans fin",
        [ToolCallPart("get_product_details", {})],
        repeat_last_call=True,
    ),
    Scenario(
        "budget de correction épuisé : le même outil inventé, sans fin",
        [ToolCallPart("get_stock_level", {"sku": "P-15695"})],
        repeat_last_call=True,
    ),
]


def scripted(scenario: Scenario) -> Callable[[list[ModelMessage], AgentInfo], ModelResponse]:
    """Joue les appels du scénario, un par tour du modèle, puis répond « fin »."""

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        turn = sum(isinstance(message, ModelResponse) for message in messages)
        if turn < len(scenario.calls):
            return ModelResponse(parts=[scenario.calls[turn]])
        if scenario.repeat_last_call:
            last = scenario.calls[-1]
            return ModelResponse(parts=[ToolCallPart(last.tool_name, last.args)])
        return ModelResponse(parts=[TextPart("fin")])

    return respond


def describe(part: Any) -> str:
    detail = getattr(part, "args", None)
    if detail is None:
        detail = getattr(part, "content", "")
    extra = f" outcome={part.outcome}" if hasattr(part, "outcome") else ""
    return f"{type(part).__name__:<16} {getattr(part, 'tool_name', '') or '':<22}{extra} {detail!r}"


async def explore(url: str, scenario: Scenario) -> None:
    toolset = MCPToolset(url, tool_error_behavior=TOOL_ERROR_BEHAVIOR, max_retries=MAX_RETRIES)
    agent = Agent(FunctionModel(scripted(scenario)), toolsets=[toolset])
    print(f"\n=== {scenario.name}")
    with capture_run_messages() as messages:
        try:
            result = await agent.run(
                "question", usage_limits=UsageLimits(request_limit=REQUEST_LIMIT)
            )
            print(f"fin du run : {result.output!r}")
        except Exception as error:
            print(f"le run lève {type(error).__name__} : {error}")
    for message in messages:
        for part in message.parts:
            print(f"  {type(message).__name__:<14} {describe(part)[:220]}")
    emitted = sum(
        isinstance(part, ToolCallPart)
        for message in messages
        if isinstance(message, ModelResponse)
        for part in message.parts
    )
    print(f"  -> appels émis dans l'historique : {emitted}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8082/mcp")
    args = parser.parse_args()
    for scenario in SCENARIOS:
        await explore(args.url, scenario)


if __name__ == "__main__":
    anyio.run(main)
