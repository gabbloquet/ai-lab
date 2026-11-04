from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.usage import RequestUsage

from exp001_agent.loop import emitted_calls, usage_of


def response(*parts, input_tokens=0, output_tokens=0) -> ModelResponse:
    return ModelResponse(
        parts=list(parts),
        usage=RequestUsage(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def test_lists_every_emitted_call_in_order_including_rejected_ones():
    messages = [
        ModelRequest(parts=[UserPromptPart("question")]),
        response(
            ToolCallPart("search_catalog", {"query": "casque"}),
            ToolCallPart("get_stock_level", {"sku": "P-15695"}),
        ),
        ModelRequest(parts=[ToolReturnPart("search_catalog", "{}", tool_call_id="1")]),
        response(ToolCallPart("check_availability", '{"sku": "P-15695", "storeId": "S01"}')),
        response(TextPart("fin")),
    ]

    assert emitted_calls(messages) == [
        {"tool": "search_catalog", "args": {"query": "casque"}},
        {"tool": "get_stock_level", "args": {"sku": "P-15695"}},
        {"tool": "check_availability", "args": {"sku": "P-15695", "storeId": "S01"}},
    ]


def test_keeps_malformed_arguments_as_an_unparsed_string():
    messages = [response(ToolCallPart("get_product_details", '{"sku": "P-1'))]

    assert emitted_calls(messages) == [
        {"tool": "get_product_details", "args": {"_unparsed": '{"sku": "P-1'}}
    ]


def test_sums_the_tokens_of_every_model_response():
    messages = [
        response(TextPart("a"), input_tokens=100, output_tokens=10),
        ModelRequest(parts=[UserPromptPart("b")]),
        response(TextPart("c"), input_tokens=150, output_tokens=20),
    ]

    assert usage_of(messages) == {"input_tokens": 250, "output_tokens": 30}


def test_fixes_the_temperature_at_zero_where_the_provider_accepts_it():
    from exp001_agent.loop import model_settings

    assert model_settings("mistral:mistral-small-2603") == {"temperature": 0.0}
    assert model_settings("google:gemini-3.5-flash-lite") == {"temperature": 0.0}


def test_leaves_the_temperature_unset_for_claude_which_rejects_it():
    from exp001_agent.loop import model_settings

    assert model_settings("anthropic:claude-haiku-5-5") == {}
