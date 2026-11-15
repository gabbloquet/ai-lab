"""Le RAG agentique de l'étape 8 de la 002, avec un faux modèle et de faux outils : ni coût ni
hasard. Les outils ont les noms et les réponses du serveur MCP du dépôt."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.toolsets import FunctionToolset

from ailab_evals.rag_qa_v2 import score_execution
from ailab_rag.agentic import AGENTIC_VARIANT, run_agentic_item

pytestmark = pytest.mark.anyio

GOLD, OTHER = "LEGIARTI000032226842", "LEGIARTI000032221377"
ITEM = {
    "id": "rq-001",
    "split": "dev",
    "mode": "direct",
    "answerable": True,
    "question": "Achat en ligne : combien de temps pour me rétracter ?",
    "expected": {
        "facts": [{"accepted": ["quatorze jours", "14 jours"]}],
        "articles": [{"id": GOLD, "num": "L221-18"}],
    },
    "evidence": [{"article": GOLD, "quote": "quatorze jours"}],
}
SCHEMA = json.loads(
    (Path(__file__).resolve().parents[3] / "evals/spec/rag-qa/v2/execution.schema.json").read_text()
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def fake_tools() -> FunctionToolset:
    tools = FunctionToolset()

    @tools.tool_plain(name="consommation_search_articles")
    def search(query: str) -> dict:
        return {
            "passages": [
                {"id": OTHER, "num": "L221-23", "path": [], "text": "Renvoi."},
                {"id": GOLD, "num": "L221-18", "path": [], "text": "Quatorze jours."},
            ]
        }

    @tools.tool_plain(name="consommation_get_article")
    def get_article(num: str) -> dict:
        return {"id": GOLD, "num": "L221-18", "path": [], "text": "Quatorze jours."}

    return tools


def scripted(*steps: tuple[str, dict]) -> FunctionModel:
    """Un modèle qui appelle les outils dans l'ordre donné, puis répond « 14 jours »."""

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        done = sum(
            isinstance(p, ToolReturnPart)
            for m in messages
            if isinstance(m, ModelRequest)
            for p in m.parts
        )
        if done < len(steps):
            name, args = steps[done]
            return ModelResponse(parts=[ToolCallPart(name, args)])
        answer = {"answer": "Vous avez 14 jours.", "abstained": False, "cited": ["L221-18"]}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, answer)])

    return FunctionModel(respond, model_name="fake-model")


async def test_the_context_is_every_article_the_tools_returned_in_order() -> None:
    model = scripted(
        ("consommation_search_articles", {"query": "rétractation"}),
        ("consommation_get_article", {"num": "L. 221-18"}),
    )

    execution = await run_agentic_item(ITEM, model=model, repeat=0, toolsets=lambda: [fake_tools()])

    assert execution["variant"] == AGENTIC_VARIANT
    assert execution["tool_calls"] == 2
    assert (execution["extra"]["search_calls"], execution["extra"]["get_calls"]) == (1, 1)
    assert execution["context"] == [OTHER, GOLD, GOLD]
    assert list(Draft202012Validator(SCHEMA).iter_errors(execution)) == []
    score = score_execution(ITEM, execution)
    assert score["correct"] is True and score["all_evidence"] is True
    assert score["evidence_recall@1"] is None  # plusieurs appels : pas de classement unique


async def test_answering_without_searching_has_an_empty_context() -> None:
    execution = await run_agentic_item(
        ITEM, model=scripted(), repeat=0, toolsets=lambda: [fake_tools()]
    )

    assert (execution["tool_calls"], execution["context"]) == (0, [])


async def test_the_question_goes_alone_and_the_instructions_explain_the_tools() -> None:
    seen: list[str] = []
    prompts: list[str] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(info.instructions or "")
        prompts.extend(
            str(p.content)
            for m in messages
            if isinstance(m, ModelRequest)
            for p in m.parts
            if type(p).__name__ == "UserPromptPart"
        )
        answer = {"answer": "", "abstained": True, "cited": []}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, answer)])

    await run_agentic_item(
        ITEM, model=FunctionModel(respond), repeat=0, toolsets=lambda: [fake_tools()]
    )

    assert prompts == [f"Question : {ITEM['question']}"]
    assert "consommation_search_articles" in seen[0] and "abstained" in seen[0]
