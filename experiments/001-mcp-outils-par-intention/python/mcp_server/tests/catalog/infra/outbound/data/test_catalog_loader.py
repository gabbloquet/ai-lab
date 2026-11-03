from decimal import Decimal
from pathlib import Path

import pytest

from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId
from exp001_mcp_server.catalog.infra.outbound.data.catalog_loader import (
    read_products,
    read_stock_lines,
    read_stores,
)


@pytest.fixture
def data_dir(pytestconfig) -> Path:
    return pytestconfig.rootpath / "domains/magasin/data/v1"


def test_loads_the_whole_dataset(data_dir):
    assert len(read_products(data_dir)) == 50
    assert len(read_stores(data_dir)) == 5
    assert len(read_stock_lines(data_dir)) == 250


def test_loads_prices_exactly(data_dir):
    product = next(p for p in read_products(data_dir) if p.sku == SkuCode("P-13905"))

    assert product.price == Decimal("101.99")


def test_loads_identifiers_as_value_objects(data_dir):
    line = next(
        line
        for line in read_stock_lines(data_dir)
        if line.sku == SkuCode("P-38893") and line.store_id == StoreId("S04")
    )

    assert line.on_hand == 3
    assert line.available == 0


def test_loads_stores_with_their_city(data_dir):
    store = next(s for s in read_stores(data_dir) if s.store_id == StoreId("S03"))

    assert store.city == "Lille"
