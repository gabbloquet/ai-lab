from decimal import Decimal

from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.entities.stock_line import StockLine
from exp001_mcp_server.catalog.domain.entities.store import Store
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId
from exp001_mcp_server.catalog.infra.outbound.memory.in_memory_product_repository import (
    InMemoryProductRepository,
)
from exp001_mcp_server.catalog.infra.outbound.memory.in_memory_stock_repository import (
    InMemoryStockRepository,
)
from exp001_mcp_server.catalog.infra.outbound.memory.in_memory_store_repository import (
    InMemoryStoreRepository,
)

HEADPHONES = Product(
    sku=SkuCode("P-00001"),
    name="Casque test",
    brand="Marque",
    department="Audio",
    type="Casque",
    price=Decimal("100.00"),
)
KETTLE = Product(
    sku=SkuCode("P-00002"),
    name="Bouilloire test",
    brand="Marque",
    department="Maison",
    type="Bouilloire",
    price=Decimal("30.00"),
)
LYON = Store(StoreId("S01"), "Magasin Lyon", "Lyon")


def test_finds_a_product_by_sku():
    products = InMemoryProductRepository([HEADPHONES, KETTLE])

    assert products.find_by_sku(SkuCode("p-00002")) == KETTLE
    assert products.find_by_sku(SkuCode("P-99999")) is None


def test_lists_every_product_in_load_order():
    assert list(InMemoryProductRepository([KETTLE, HEADPHONES]).find_all()) == [KETTLE, HEADPHONES]


def test_finds_a_store_by_id():
    stores = InMemoryStoreRepository([LYON])

    assert stores.find_by_id(StoreId("s01")) == LYON
    assert stores.find_by_id(StoreId("S99")) is None
    assert list(stores.find_all()) == [LYON]


def test_finds_the_stock_line_of_a_product_in_a_store():
    line = StockLine(SkuCode("P-00001"), StoreId("S01"), on_hand=3, reserved=1)
    stock = InMemoryStockRepository([line])

    assert stock.find(SkuCode("P-00001"), StoreId("S01")) == line
    assert stock.find(SkuCode("P-00001"), StoreId("S02")) is None


def test_keeps_its_own_copy_of_the_loaded_lists():
    loaded = [HEADPHONES]
    products = InMemoryProductRepository(loaded)
    loaded.append(KETTLE)

    assert list(products.find_all()) == [HEADPHONES]
