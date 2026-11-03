from decimal import Decimal

from exp001_mcp_server.catalog.domain.entities.alternative import Alternative
from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.entities.store import Store
from exp001_mcp_server.catalog.domain.entities.store_stock import StoreStock
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.availability import Availability
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.catalog_search_results import (
    CatalogSearchResults,
)
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.in_stock_alternatives import (
    InStockAlternatives,
)
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.product_details import ProductDetails
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.stores_with_stock import (
    StoresWithStock,
)
from exp001_mcp_server.catalog.infra.inbound.mcp.tool_results import to_json

LYON = Store(StoreId("S01"), "Magasin Lyon", "Lyon")


def product(i: int, price: str = "10.0") -> Product:
    return Product(
        sku=SkuCode(f"P-{i:05d}"),
        name=f"Produit {i}",
        brand="Marque",
        department="Audio",
        type="Casque",
        price=Decimal(price),
    )


def test_details_a_product_with_its_currency():
    assert to_json(ProductDetails.of(product(1, "101.99"))) == (
        '{"sku":"P-00001","name":"Produit 1","brand":"Marque","department":"Audio",'
        '"type":"Casque","price":101.99,"currency":"EUR"}'
    )


def test_says_a_product_is_in_stock_only_with_units_available():
    assert Availability.of(product(1), LYON, 2).in_stock is True
    assert to_json(Availability.of(product(1), LYON, 0)) == (
        '{"sku":"P-00001","name":"Produit 1","storeId":"S01","storeName":"Magasin Lyon",'
        '"available":0,"inStock":false}'
    )


def test_lists_the_stores_with_their_city_and_units():
    stores = StoresWithStock.of(product(1), [StoreStock(LYON, 8)])

    assert to_json(stores) == (
        '{"sku":"P-00001","name":"Produit 1","stores":'
        '[{"storeId":"S01","name":"Magasin Lyon","city":"Lyon","available":8}]}'
    )


def test_offers_alternatives_without_repeating_the_requested_sku_or_store():
    alternatives = InStockAlternatives.of([Alternative(product(2, "80.0"), 4)])

    assert to_json(alternatives) == (
        '{"alternatives":[{"sku":"P-00002","name":"Produit 2","brand":"Marque",'
        '"price":80.0,"currency":"EUR","available":4}]}'
    )


def test_gives_every_match_when_there_are_few():
    matches = [product(i) for i in range(1, 4)]

    assert CatalogSearchResults.of(matches) == CatalogSearchResults(
        3, [ProductDetails.of(p) for p in matches]
    )


def test_caps_the_products_at_ten_but_counts_every_match():
    results = CatalogSearchResults.of([product(i) for i in range(1, 13)])

    assert results.total == 12
    assert [p.sku for p in results.products] == [f"P-{i:05d}" for i in range(1, 11)]
    assert results.hint is None


def test_explains_an_empty_search():
    assert to_json(CatalogSearchResults.of([])) == (
        '{"total":0,"products":[],'
        '"hint":"No product matches every word of the query. The query searches product names,'
        ' brands and types; use category to restrict to a department."}'
    )
