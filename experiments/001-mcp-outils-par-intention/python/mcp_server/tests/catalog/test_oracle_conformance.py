import json
from pathlib import Path
from typing import Any

import pytest

from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId
from exp001_mcp_server.catalog.infra.outbound.data.catalog_loader import load_catalog

ROOT = Path(__file__).resolve().parents[6]
CATALOG = load_catalog(ROOT / "domains/magasin/data/v1")
ORACLE = ROOT / "domains/magasin/oracle/v1"


def expectations(name: str) -> list[dict[str, Any]]:
    lines = (ORACLE / name).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


AVAILABILITY = expectations("availability.jsonl")
STORES_WITH_STOCK = expectations("stores_with_stock.jsonl")


def test_covers_the_whole_oracle():
    assert (len(AVAILABILITY), len(STORES_WITH_STOCK)) == (250, 50)


@pytest.mark.parametrize("expected", AVAILABILITY, ids=lambda e: f"{e['sku']}@{e['storeId']}")
def test_matches_the_oracle_on_availability_and_alternatives(expected):
    sku, store_id = SkuCode(expected["sku"]), StoreId(expected["storeId"])
    line = CATALOG.stock(sku, store_id)

    assert (line.available if line else 0) == expected["available"]
    assert [a.product.sku.value for a in CATALOG.alternatives(sku, store_id)] == expected[
        "alternatives"
    ]


@pytest.mark.parametrize("expected", STORES_WITH_STOCK, ids=lambda e: e["sku"])
def test_matches_the_oracle_on_stores_with_stock(expected):
    stores = CATALOG.stores_with_stock(SkuCode(expected["sku"]))

    assert [s.store.store_id.value for s in stores] == expected["storeIds"]
