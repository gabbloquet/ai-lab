from decimal import Decimal

import pytest

from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.entities.stock_line import StockLine
from exp001_mcp_server.catalog.domain.entities.store import Store
from exp001_mcp_server.catalog.domain.errors import ProductNotFoundError, StoreNotFoundError
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId
from exp001_mcp_server.catalog.infra.outbound.memory.in_memory_catalog import in_memory_catalog

HEADPHONES_SKU = SkuCode("P-00001")
LYON = StoreId("S01")
HEADPHONES = Product(
    sku=HEADPHONES_SKU,
    name="Casque test",
    brand="Marque",
    department="Audio",
    type="Casque",
    price=Decimal("100.00"),
)
CATALOG = in_memory_catalog(
    [HEADPHONES],
    [Store(LYON, "Magasin test", "Lyon")],
    [StockLine(HEADPHONES_SKU, LYON, on_hand=3, reserved=3)],
)


def product(sku: str, department: str) -> Product:
    return Product(
        sku=SkuCode(sku),
        name=f"Produit {sku}",
        brand="Marque",
        department=department,
        type="Type",
        price=Decimal("10.00"),
    )


def test_finds_a_product_by_sku():
    assert CATALOG.product(HEADPHONES_SKU) == HEADPHONES


def test_finds_a_product_from_an_unnormalized_code():
    assert CATALOG.product(SkuCode(" p-00001 ")) == HEADPHONES


def test_unknown_sku_gives_no_product():
    assert CATALOG.product(SkuCode("P-99999")) is None


def test_requires_a_known_product():
    assert CATALOG.require_product(HEADPHONES_SKU) == HEADPHONES


def test_signals_an_unknown_product_with_its_sku():
    with pytest.raises(ProductNotFoundError) as error:
        CATALOG.require_product(SkuCode("P-99999"))

    assert error.value.sku == SkuCode("P-99999")


def test_requires_a_known_store():
    assert CATALOG.require_store(LYON).city == "Lyon"


def test_signals_an_unknown_store_with_its_id():
    with pytest.raises(StoreNotFoundError) as error:
        CATALOG.require_store(StoreId("S99"))

    assert error.value.store_id == StoreId("S99")


def test_finds_a_store_by_id():
    store = CATALOG.store(StoreId(" s01 "))

    assert store is not None
    assert store.city == "Lyon"


def test_unknown_store_id_gives_no_store():
    assert CATALOG.store(StoreId("S99")) is None


def test_finds_the_stock_line_of_a_product_in_a_store():
    line = CATALOG.stock(SkuCode("p-00001"), StoreId("s01"))

    assert line is not None
    assert (line.on_hand, line.reserved, line.available) == (3, 3, 0)


def test_unknown_store_gives_no_stock_line():
    assert CATALOG.stock(HEADPHONES_SKU, StoreId("S99")) is None


def test_lists_each_department_once_in_order():
    catalog = in_memory_catalog(
        [product("P-00001", "Maison"), product("P-00002", "Audio"), product("P-00003", "Maison")],
        [],
        [],
    )

    assert catalog.departments() == ["Audio", "Maison"]
