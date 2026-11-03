import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from mcp import Client
from mcp.types import CallToolResult, TextContent, Tool

from exp001_mcp_server.server import create_server

pytestmark = pytest.mark.anyio

KNOWN_STORES = (
    "Known stores: S01 (Lyon), S02 (Nantes), S03 (Lille), S04 (Bordeaux), S05 (Strasbourg)."
)
UNKNOWN_PRODUCT = "Product not found: P-00000. Use search_catalog to find the SKU of a product."


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client(pytestconfig) -> AsyncIterator[Client]:
    server = create_server(pytestconfig.rootpath / "domains/magasin/data/v1")
    async with Client(server, mode="legacy") as connected:
        yield connected


async def tool(client: Client, name: str) -> Tool:
    return next(t for t in (await client.list_tools()).tools if t.name == name)


async def call(client: Client, name: str, arguments: dict[str, Any]) -> CallToolResult:
    return await client.call_tool(name, arguments)


def texts(result: CallToolResult) -> list[str]:
    return [content.text for content in result.content if isinstance(content, TextContent)]


async def test_exposes_only_the_intent_tools_in_a_fixed_order(client):
    assert [t.name for t in (await client.list_tools()).tools] == [
        "check_availability",
        "find_in_stock_alternative",
        "find_stores_with_stock",
        "get_product_details",
        "search_catalog",
    ]


async def test_asks_for_a_query_and_an_optional_category_to_search(client):
    schema = (await tool(client, "search_catalog")).input_schema

    assert set(schema["properties"]) == {"query", "category"}
    assert schema["required"] == ["query"]


async def test_asks_for_the_sku_as_a_plain_string(client):
    schema = (await tool(client, "get_product_details")).input_schema

    assert set(schema["properties"]) == {"sku"}
    assert schema["properties"]["sku"]["type"] == "string"
    assert schema["required"] == ["sku"]


async def test_declares_every_tool_as_read_only_on_a_closed_domain(client):
    for t in (await client.list_tools()).tools:
        annotations = t.annotations
        assert annotations is not None, t.name
        assert annotations.read_only_hint is True, t.name
        assert annotations.destructive_hint is False, t.name
        assert annotations.idempotent_hint is True, t.name
        assert annotations.open_world_hint is False, t.name


async def test_publishes_no_output_schema(client):
    assert all(t.output_schema is None for t in (await client.list_tools()).tools)


async def test_searches_every_word_ignoring_case_and_accents(client):
    result = await call(client, "search_catalog", {"query": "CAFETIERE pellisse"})

    assert result.is_error is not True
    assert texts(result) == [
        '{"total":2,"products":['
        '{"sku":"P-14165","name":"Pellisse Cafetière F5","brand":"Pellisse","department":"Maison",'
        '"type":"Cafetière","price":157.0,"currency":"EUR"},'
        '{"sku":"P-13905","name":"Pellisse Cafetière G9","brand":"Pellisse","department":"Maison",'
        '"type":"Cafetière","price":101.99,"currency":"EUR"}]}'
    ]
    assert result.structured_content is None


async def test_filters_the_search_on_a_category(client):
    result = await call(client, "search_catalog", {"query": "veldric", "category": "audio"})

    assert texts(result) == [
        '{"total":2,"products":['
        '{"sku":"P-15695","name":"Veldric Casque K8","brand":"Veldric","department":"Audio",'
        '"type":"Casque","price":100.0,"currency":"EUR"},'
        '{"sku":"P-23396","name":"Veldric Écouteurs R7","brand":"Veldric","department":"Audio",'
        '"type":"Écouteurs","price":76.5,"currency":"EUR"}]}'
    ]


async def test_explains_an_empty_search_instead_of_answering_with_nothing(client):
    result = await call(client, "search_catalog", {"query": "audio"})

    assert result.is_error is not True
    assert texts(result) == [
        '{"total":0,"products":[],'
        '"hint":"No product matches every word of the query. The query searches product names,'
        ' brands and types; use category to restrict to a department."}'
    ]


async def test_returns_ten_products_at_most_but_counts_every_match(client):
    summary = json.loads(texts(await call(client, "search_catalog", {"query": "e"}))[0])

    assert summary["total"] == 49
    assert len(summary["products"]) == 10


async def test_tells_the_model_to_refine_the_search_when_results_are_capped(client):
    description = (await tool(client, "search_catalog")).description or ""

    assert (
        "If total is greater than the number of products returned,"
        " refine the query or use a category." in description
    )


async def test_reports_a_blank_search_query(client):
    result = await call(client, "search_catalog", {"query": "  "})

    assert result.is_error is True
    assert texts(result) == [
        "Search query must not be blank. Provide at least one word of a product name, brand or"
        " type. To narrow the results to a department, use category."
    ]


async def test_reports_an_unknown_category_with_the_known_ones(client):
    result = await call(client, "search_catalog", {"query": "casque", "category": "Hifi"})

    assert result.is_error is True
    assert texts(result) == [
        "Category not found: Hifi. Known categories: Audio, Informatique, Maison, Sport."
    ]


async def test_returns_the_product_details_as_json_in_a_single_text_block(client):
    result = await call(client, "get_product_details", {"sku": "p-13905"})

    assert result.is_error is not True
    assert texts(result) == [
        '{"sku":"P-13905","name":"Pellisse Cafetière G9","brand":"Pellisse","department":"Maison",'
        '"type":"Cafetière","price":101.99,"currency":"EUR"}'
    ]


async def test_reports_an_unknown_product_once_with_what_to_do_next(client):
    result = await call(client, "get_product_details", {"sku": "P-00000"})

    assert result.is_error is True
    assert texts(result) == [UNKNOWN_PRODUCT]


async def test_reports_a_blank_sku_as_an_invalid_argument(client):
    result = await call(client, "get_product_details", {"sku": "   "})

    assert result.is_error is True
    assert texts(result) == ["SKU must not be blank"]


async def test_reports_a_malformed_sku_with_the_expected_format(client):
    result = await call(client, "get_product_details", {"sku": "80284"})

    assert result.is_error is True
    assert texts(result) == ["Invalid SKU: 80284. A SKU is P- followed by 5 digits."]


async def test_gives_the_quantity_available_for_sale_net_of_reservations(client):
    result = await call(client, "check_availability", {"sku": "P-38893", "storeId": "s04"})

    assert result.is_error is not True
    assert texts(result) == [
        '{"sku":"P-38893","name":"Zorvane Souris E8","storeId":"S04",'
        '"storeName":"Magasin Bordeaux","available":0,"inStock":false}'
    ]


async def test_reports_an_unknown_store_with_the_known_ones(client):
    result = await call(client, "check_availability", {"sku": "P-38893", "storeId": "S99"})

    assert result.is_error is True
    assert texts(result) == [f"Store not found: S99. {KNOWN_STORES}"]


async def test_lists_the_stores_that_can_sell_a_product_with_their_units(client):
    result = await call(client, "find_stores_with_stock", {"sku": "P-15695"})

    assert result.is_error is not True
    assert texts(result) == [
        '{"sku":"P-15695","name":"Veldric Casque K8","stores":['
        '{"storeId":"S01","name":"Magasin Lyon","city":"Lyon","available":8},'
        '{"storeId":"S04","name":"Magasin Bordeaux","city":"Bordeaux","available":11},'
        '{"storeId":"S05","name":"Magasin Strasbourg","city":"Strasbourg","available":7}]}'
    ]


async def test_answers_with_no_store_when_the_product_is_out_of_stock_everywhere(client):
    result = await call(client, "find_stores_with_stock", {"sku": "P-13478"})

    assert texts(result) == ['{"sku":"P-13478","name":"Tisanor Écran B6","stores":[]}']


async def test_reports_an_unknown_product_when_looking_for_stores(client):
    result = await call(client, "find_stores_with_stock", {"sku": "P-00000"})

    assert result.is_error is True
    assert texts(result) == [UNKNOWN_PRODUCT]


async def test_offers_alternatives_at_both_bounds_of_the_price_band(client):
    result = await call(client, "find_in_stock_alternative", {"sku": "P-15695", "storeId": "S02"})

    assert result.is_error is not True
    assert texts(result) == [
        '{"alternatives":['
        '{"sku":"P-26361","name":"Zorvane Casque P2","brand":"Zorvane","price":80.0,'
        '"currency":"EUR","available":4},'
        '{"sku":"P-44671","name":"Ostrane Casque N4","brand":"Ostrane","price":120.0,'
        '"currency":"EUR","available":4}]}'
    ]


async def test_offers_no_alternative_when_none_is_available_in_the_store(client):
    result = await call(client, "find_in_stock_alternative", {"sku": "P-22280", "storeId": "S03"})

    assert texts(result) == ['{"alternatives":[]}']


async def test_reports_an_unknown_store_when_looking_for_alternatives(client):
    result = await call(client, "find_in_stock_alternative", {"sku": "P-15695", "storeId": "S99"})

    assert result.is_error is True
    assert texts(result) == [f"Store not found: S99. {KNOWN_STORES}"]
