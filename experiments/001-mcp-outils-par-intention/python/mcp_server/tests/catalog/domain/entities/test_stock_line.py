from exp001_mcp_server.catalog.domain.entities.stock_line import StockLine
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId


def test_available_units_are_stock_on_hand_minus_reserved_units():
    line = StockLine(SkuCode("P-38893"), StoreId("S04"), on_hand=9, reserved=5)

    assert line.available == 4


def test_nothing_is_available_when_every_unit_is_reserved():
    line = StockLine(SkuCode("P-38893"), StoreId("S04"), on_hand=6, reserved=6)

    assert line.available == 0
