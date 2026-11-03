import json
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.entities.stock_line import StockLine
from exp001_mcp_server.catalog.domain.entities.store import Store
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId


def read_products(data_dir: Path) -> list[Product]:
    return [_product(row) for row in _read_json_lines(data_dir / "products.jsonl")]


def read_stores(data_dir: Path) -> list[Store]:
    return [_store(row) for row in _read_json_lines(data_dir / "stores.jsonl")]


def read_stock_lines(data_dir: Path) -> list[StockLine]:
    return [_stock_line(row) for row in _read_json_lines(data_dir / "stock.jsonl")]


def _read_json_lines(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line, parse_float=Decimal)


def _product(row: dict[str, Any]) -> Product:
    return Product(
        sku=SkuCode(row["sku"]),
        name=row["name"],
        brand=row["brand"],
        department=row["department"],
        type=row["type"],
        price=row["price"],
    )


def _store(row: dict[str, Any]) -> Store:
    return Store(store_id=StoreId(row["storeId"]), name=row["name"], city=row["city"])


def _stock_line(row: dict[str, Any]) -> StockLine:
    return StockLine(
        sku=SkuCode(row["sku"]),
        store_id=StoreId(row["storeId"]),
        on_hand=row["onHand"],
        reserved=row["reserved"],
    )
