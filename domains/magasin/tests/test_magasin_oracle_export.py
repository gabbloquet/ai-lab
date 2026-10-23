import json
from pathlib import Path

from magasin_oracle_export import export

DATA_V1 = Path(__file__).resolve().parents[1] / "data" / "v1"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_exports_one_expectation_per_product_and_store(tmp_path: Path) -> None:
    export(DATA_V1, tmp_path)

    assert len(read_jsonl(tmp_path / "availability.jsonl")) == 50 * 5
    assert len(read_jsonl(tmp_path / "stores_with_stock.jsonl")) == 50


def test_boundary_scenario_lists_both_bounds_sorted_by_sku(tmp_path: Path) -> None:
    export(DATA_V1, tmp_path)
    rows = read_jsonl(tmp_path / "availability.jsonl")

    row = next(r for r in rows if r["sku"] == "P-15695" and r["storeId"] == "S02")
    assert row["available"] == 0
    assert row["alternatives"] == ["P-26361", "P-44671"]


def test_export_is_reproducible(tmp_path: Path) -> None:
    export(DATA_V1, tmp_path / "a")
    export(DATA_V1, tmp_path / "b")

    for name in ("availability.jsonl", "stores_with_stock.jsonl"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
