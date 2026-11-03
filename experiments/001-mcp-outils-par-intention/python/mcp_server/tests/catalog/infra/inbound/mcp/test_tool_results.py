from dataclasses import dataclass
from decimal import Decimal

from mcp.types import CallToolResult, TextContent

from exp001_mcp_server.catalog.domain.errors import CatalogError, ProductNotFoundError
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.infra.inbound.mcp.tool_results import ToolResults, to_json


@dataclass(frozen=True)
class Sample:
    sku: str
    store_id: str
    available: int
    price: Decimal
    hint: str | None = None


def texts(result: CallToolResult) -> list[str]:
    return [content.text for content in result.content if isinstance(content, TextContent)]


TOOL_RESULTS = ToolResults(lambda error: f"message for {type(error).__name__}")


def test_returns_the_response_as_compact_json_in_a_single_text_block():
    result = TOOL_RESULTS.run(lambda: Sample("P-15695", "S01", 3, Decimal("101.99")))

    assert result.is_error is not True
    assert texts(result) == ['{"sku":"P-15695","storeId":"S01","available":3,"price":101.99}']
    assert result.structured_content is None


def test_names_fields_in_camel_case_and_omits_absent_ones():
    assert to_json(Sample("P-1", "S01", 0, Decimal("157.0"))) == (
        '{"sku":"P-1","storeId":"S01","available":0,"price":157.0}'
    )
    assert '"hint":"h"' in to_json(Sample("P-1", "S01", 0, Decimal("1.0"), hint="h"))


def test_keeps_accented_characters_as_they_are():
    assert to_json(["Cafetière"]) == '["Cafetière"]'


def test_translates_a_domain_error_with_the_messages_of_the_variant():
    def tool() -> object:
        raise ProductNotFoundError(SkuCode("P-00000"))

    result = TOOL_RESULTS.run(tool)

    assert result.is_error is True
    assert texts(result) == ["message for ProductNotFoundError"]


def test_hides_the_details_of_an_unexpected_error():
    def tool() -> object:
        raise RuntimeError("connection to db-prod-07 refused")

    [text] = texts(TOOL_RESULTS.run(tool))

    assert "db-prod-07" not in text
    assert "Internal error" in text


def test_treats_a_value_error_from_a_bug_as_unexpected():
    def tool() -> object:
        raise ValueError("index 42 out of bounds for internal-cache")

    [text] = texts(TOOL_RESULTS.run(tool))

    assert "internal-cache" not in text
    assert "Internal error" in text


def test_only_domain_errors_reach_the_variant_messages():
    seen: list[CatalogError] = []

    def messages(error: CatalogError) -> str:
        seen.append(error)
        return "x"

    def tool() -> object:
        raise KeyError("boom")

    ToolResults(messages).run(tool)

    assert seen == []
