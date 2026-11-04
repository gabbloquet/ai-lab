"""Le lanceur contre le jumeau Python en HTTP, avec un faux modèle : ni coût ni hasard."""

import pytest
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from exp001_agent.campaign import run_campaign

pytestmark = pytest.mark.anyio

ITEMS = [
    {
        "id": "ts-x",
        "split": "dev",
        "question": "Fiche du P-13905 ?",
        "context": {"storeId": "S01"},
        "expected": {
            "intent": {
                "required": [{"tool": "get_product_details", "args": {"sku": ["P-13905"]}}],
                "tolerated": [],
            }
        },
    }
]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def answering() -> FunctionModel:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if sum(isinstance(m, ModelResponse) for m in messages) == 0:
            return ModelResponse(parts=[ToolCallPart("get_product_details", {"sku": "P-13905"})])
        return ModelResponse(parts=[TextPart("fin")])

    return FunctionModel(respond)


async def test_runs_every_item_k_times_per_variant_and_scores_it(server_url):
    records = await run_campaign(
        items=ITEMS,
        servers={"intent": server_url},
        model=answering(),
        repeats=3,
        system_prompt="Magasin {store_id}.",
    )

    assert [(r.execution.repeat, r.score.success) for r in records] == [
        (0, True),
        (1, True),
        (2, True),
    ]


async def test_skips_the_executions_already_done(server_url):
    records = await run_campaign(
        items=ITEMS,
        servers={"intent": server_url},
        model=answering(),
        repeats=2,
        system_prompt="Magasin {store_id}.",
        done={("ts-x", "intent", 0)},
    )

    assert [r.execution.repeat for r in records] == [1]


async def test_retries_a_rate_limited_execution_instead_of_scoring_it_as_a_failure(server_url):
    calls = {"count": 0}

    def flaky(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        calls["count"] += 1
        if calls["count"] == 1:
            raise ModelHTTPError(429, "fake", retry_after=0)
        return answering().function(messages, info)  # type: ignore[misc]

    [record] = await run_campaign(
        items=ITEMS,
        servers={"intent": server_url},
        model=FunctionModel(flaky),
        repeats=1,
        system_prompt="Magasin {store_id}.",
        backoff_seconds=0,
    )

    assert record.attempts == 2
    assert record.execution.error is None
    assert record.score.success is True
