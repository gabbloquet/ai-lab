"""La boucle contre un vrai serveur MCP (le jumeau Python, en HTTP), avec un faux modèle."""

import socket
import threading
import time
from collections.abc import Iterator

import pytest
import uvicorn
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from exp001_agent.loop import MAX_TOOL_CALLS, TOOL_CALL_LIMIT_ERROR, Execution, run_item
from exp001_mcp_server.server import create_server

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="module")
def url(pytestconfig) -> Iterator[str]:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    app = create_server(pytestconfig.rootpath / "domains/magasin/data/v1").streamable_http_app(
        host="127.0.0.1"
    )
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/mcp"
    server.should_exit = True
    thread.join(timeout=5)


def model(*calls: ToolCallPart, forever: bool = False) -> FunctionModel:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        turn = sum(isinstance(message, ModelResponse) for message in messages)
        if turn < len(calls):
            return ModelResponse(parts=[calls[turn]])
        if forever:
            return ModelResponse(parts=[ToolCallPart(calls[-1].tool_name, calls[-1].args)])
        return ModelResponse(parts=[TextPart("fin")])

    return FunctionModel(respond)


async def run(url: str, fake: FunctionModel):
    return await run_item(
        item_id="ts-test",
        question="question",
        store_id="S01",
        variant="intent",
        url=url,
        model=fake,
        system_prompt="Magasin {store_id}.",
    )


async def test_records_the_calls_and_the_answer(url):
    execution = await run(
        url,
        model(
            ToolCallPart("get_product_details", {"sku": "P-13905"}),
            ToolCallPart("check_availability", {"sku": "P-13905", "storeId": "S99"}),
        ),
    )

    assert execution.calls == [
        {"tool": "get_product_details", "args": {"sku": "P-13905"}},
        {"tool": "check_availability", "args": {"sku": "P-13905", "storeId": "S99"}},
    ]
    assert execution.error is None
    assert execution.answer == "fin"


async def test_stops_after_the_tenth_call_and_flags_it(url):
    execution = await run(url, model(ToolCallPart("get_product_details", {}), forever=True))

    assert len(execution.calls) == MAX_TOOL_CALLS + 1
    assert execution.error == TOOL_CALL_LIMIT_ERROR
    assert execution.answer is None


async def test_keeps_the_calls_when_the_correction_budget_runs_out(url):
    execution = await run(url, model(ToolCallPart("get_stock_level", {}), forever=True))

    assert [call["tool"] for call in execution.calls] == ["get_stock_level"] * 3
    assert execution.error is not None
    assert execution.error.startswith("UnexpectedModelBehavior")


def test_the_spec_form_has_no_answer_field():
    execution = Execution("i", "intent", "m", 0, [], {}, None, "x")

    assert set(execution.to_spec()) == {
        "item_id",
        "variant",
        "model",
        "repeat",
        "calls",
        "usage",
        "error",
    }
