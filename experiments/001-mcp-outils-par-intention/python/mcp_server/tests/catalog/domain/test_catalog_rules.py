from decimal import Decimal

import pytest

from exp001_mcp_server.catalog.domain.catalog import Catalog
from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.entities.stock_line import StockLine
from exp001_mcp_server.catalog.domain.entities.store import Store
from exp001_mcp_server.catalog.domain.errors import (
    DepartmentNotFoundError,
    InvalidSearchQueryError,
)
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId
from exp001_mcp_server.catalog.infra.outbound.memory.in_memory_catalog import in_memory_catalog

STORE = StoreId("S01")


def product(sku: str, price: str, type: str = "Casque") -> Product:
    return Product(
        sku=SkuCode(sku),
        name=f"Produit {sku}",
        brand="Marque",
        department="Audio",
        type=type,
        price=Decimal(price),
    )


def stock(sku: str, on_hand: int, reserved: int) -> StockLine:
    return StockLine(SkuCode(sku), STORE, on_hand=on_hand, reserved=reserved)


def catalog(products: list[Product], stock_lines: list[StockLine]) -> Catalog:
    return in_memory_catalog(products, [Store(STORE, "Magasin test", "Lyon")], stock_lines)


def similar_of(catalog: Catalog, sku: str) -> list[str]:
    return [p.sku.value for p in catalog.similar(SkuCode(sku))]


def alternatives_of(catalog: Catalog, sku: str) -> list[str]:
    return [a.product.sku.value for a in catalog.alternatives(SkuCode(sku), STORE)]


class TestSimilar:
    def test_are_the_same_type_within_the_price_band_whatever_the_stock(self):
        c = catalog(
            [
                product("P-00001", "100.00"),
                product("P-00011", "80.00"),
                product("P-00010", "120.00"),
                product("P-00002", "100.00", "Enceinte"),
                product("P-00012", "120.01"),
            ],
            [stock("P-00011", 0, 0)],
        )

        assert sorted(similar_of(c, "P-00001")) == ["P-00010", "P-00011"]

    def test_are_sorted_by_price_gap_then_sku_without_cap(self):
        c = catalog(
            [
                product("P-00001", "100.00"),
                product("P-00034", "110.00"),
                product("P-00033", "90.00"),
                product("P-00032", "95.00"),
                product("P-00031", "119.00"),
            ],
            [],
        )

        assert similar_of(c, "P-00001") == ["P-00032", "P-00033", "P-00034", "P-00031"]

    def test_do_not_exist_for_an_unknown_product(self):
        assert similar_of(catalog([product("P-00011", "100.00")], []), "P-99999") == []


class TestAlternatives:
    def test_include_both_bounds_of_the_price_band(self):
        c = catalog(
            [
                product("P-00001", "100.00"),
                product("P-00011", "80.00"),
                product("P-00010", "120.00"),
            ],
            [stock("P-00011", 1, 0), stock("P-00010", 1, 0)],
        )

        assert alternatives_of(c, "P-00001") == ["P-00010", "P-00011"]

    def test_exclude_prices_just_outside_the_band(self):
        c = catalog(
            [
                product("P-00001", "100.00"),
                product("P-00011", "79.99"),
                product("P-00010", "120.01"),
            ],
            [stock("P-00011", 1, 0), stock("P-00010", 1, 0)],
        )

        assert alternatives_of(c, "P-00001") == []

    def test_exclude_the_product_itself(self):
        c = catalog([product("P-00001", "100.00")], [stock("P-00001", 5, 0)])

        assert alternatives_of(c, "P-00001") == []

    def test_require_the_same_type(self):
        c = catalog(
            [product("P-00001", "100.00"), product("P-00002", "100.00", "Enceinte")],
            [stock("P-00002", 1, 0)],
        )

        assert alternatives_of(c, "P-00001") == []

    def test_require_units_available_in_the_store(self):
        c = catalog(
            [
                product("P-00001", "100.00"),
                product("P-00020", "100.00"),
                product("P-00021", "100.00"),
                product("P-00022", "100.00"),
            ],
            [stock("P-00020", 0, 0), stock("P-00021", 2, 2)],
        )

        assert alternatives_of(c, "P-00001") == []

    def test_are_sorted_by_price_gap_then_sku_and_capped_at_three(self):
        c = catalog(
            [
                product("P-00001", "100.00"),
                product("P-00034", "110.00"),
                product("P-00033", "90.00"),
                product("P-00032", "95.00"),
                product("P-00031", "119.00"),
            ],
            [stock(sku, 1, 0) for sku in ("P-00031", "P-00032", "P-00033", "P-00034")],
        )

        assert alternatives_of(c, "P-00001") == ["P-00032", "P-00033", "P-00034"]

    def test_carry_the_quantity_available_for_sale(self):
        c = catalog(
            [product("P-00001", "100.00"), product("P-00002", "100.00")],
            [stock("P-00002", 5, 2)],
        )

        [alternative] = c.alternatives(SkuCode("P-00001"), STORE)
        assert alternative.available == 3

    def test_do_not_exist_for_an_unknown_product(self):
        c = catalog([product("P-00002", "100.00")], [stock("P-00002", 1, 0)])

        assert alternatives_of(c, "P-99999") == []


def test_lists_stores_with_units_available_sorted_by_store_id():
    p = product("P-00001", "100.00")
    c = in_memory_catalog(
        [p],
        [
            Store(StoreId("S02"), "Magasin 2", "Nantes"),
            Store(StoreId("S01"), "Magasin 1", "Lyon"),
            Store(StoreId("S03"), "Magasin 3", "Lille"),
        ],
        [
            StockLine(p.sku, StoreId("S02"), on_hand=1, reserved=0),
            StockLine(p.sku, StoreId("S01"), on_hand=4, reserved=0),
            StockLine(p.sku, StoreId("S03"), on_hand=2, reserved=2),
        ],
    )

    assert [(s.store.store_id.value, s.available) for s in c.stores_with_stock(p.sku)] == [
        ("S01", 4),
        ("S02", 1),
    ]


HOME_AND_AUDIO = in_memory_catalog(
    [
        Product(
            sku=SkuCode("P-00001"),
            name="Pellisse Cafetière G9",
            brand="Pellisse",
            department="Maison",
            type="Cafetière",
            price=Decimal("101.99"),
        ),
        Product(
            sku=SkuCode("P-00002"),
            name="Pellisse Bouilloire K2",
            brand="Pellisse",
            department="Maison",
            type="Bouilloire",
            price=Decimal("39.90"),
        ),
        Product(
            sku=SkuCode("P-00003"),
            name="Veldric Casque K8",
            brand="Veldric",
            department="Audio",
            type="Casque",
            price=Decimal("100.00"),
        ),
    ],
    [],
    [],
)


def found(query: str, department: str | None = None) -> list[str]:
    return [p.sku.value for p in HOME_AND_AUDIO.search(query, department)]


def browsed(department: str | None) -> list[str]:
    return [p.sku.value for p in HOME_AND_AUDIO.browse(department)]


class TestSearch:
    def test_ignores_case_and_accents(self):
        assert found("CAFETIERE") == ["P-00001"]

    def test_requires_every_word_to_match(self):
        assert found("pellisse cafetière") == ["P-00001"]
        assert found("pellisse casque") == []

    def test_searches_the_brand_and_sorts_by_name(self):
        assert found("pellisse") == ["P-00002", "P-00001"]

    def test_filters_on_the_department_ignoring_case(self):
        assert found("k", "audio") == ["P-00003"]

    def test_treats_a_blank_department_as_no_department(self):
        assert found("pellisse", " ") == ["P-00002", "P-00001"]

    def test_returns_nothing_when_nothing_matches(self):
        assert found("aspirateur") == []

    def test_rejects_a_blank_query(self):
        with pytest.raises(InvalidSearchQueryError, match="^Search query must not be blank$"):
            HOME_AND_AUDIO.search("  ", None)

    def test_rejects_an_unknown_department(self):
        with pytest.raises(DepartmentNotFoundError, match="^Unknown department: Hifi$"):
            HOME_AND_AUDIO.search("casque", "Hifi")

    def test_returns_nothing_for_a_known_department_without_match(self):
        assert found("casque", "Maison") == []


class TestBrowse:
    def test_lists_a_department_sorted_by_name(self):
        assert browsed("maison") == ["P-00002", "P-00001"]

    def test_lists_the_whole_catalog_without_department(self):
        assert browsed(None) == ["P-00002", "P-00001", "P-00003"]
        assert browsed(" ") == ["P-00002", "P-00001", "P-00003"]

    def test_rejects_an_unknown_department(self):
        with pytest.raises(DepartmentNotFoundError, match="^Unknown department: Hifi$"):
            HOME_AND_AUDIO.browse("Hifi")
