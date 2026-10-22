import hashlib
import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest
from magasin_generator import generate, main
from magasin_rules import Catalog, load_catalog

SEED = 42


def read_all(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir())}


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("magasin")
    generate(seed=SEED, out_dir=out)
    return out


@pytest.fixture(scope="module")
def cat(generated: Path) -> Catalog:
    return load_catalog(generated)


@pytest.fixture(scope="module")
def scenarios(generated: Path) -> dict[str, dict]:
    entries = json.loads((generated / "scenarios.json").read_text(encoding="utf-8"))
    return {s["id"]: s for s in entries}


def test_same_seed_produces_identical_files(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"

    generate(seed=SEED, out_dir=first)
    generate(seed=SEED, out_dir=second)

    assert read_all(first), "le générateur n'a produit aucun fichier"
    assert read_all(first) == read_all(second)


def test_different_seeds_produce_different_data(tmp_path: Path) -> None:
    generate(seed=1, out_dir=tmp_path / "a")
    generate(seed=2, out_dir=tmp_path / "b")

    assert read_all(tmp_path / "a") != read_all(tmp_path / "b")


def test_catalog_shape(cat: Catalog) -> None:
    assert len(cat.products) == 50
    assert sorted(cat.stores) == ["S01", "S02", "S03", "S04", "S05"]
    assert len(cat.stock) == 50 * 5
    assert all(re.fullmatch(r"P-\d{5}", sku) for sku in cat.products)
    assert len({p.department for p in cat.products.values()}) == 4

    per_type = Counter(p.type for p in cat.products.values())
    assert sorted(per_type.values()) == [1, 4] + [5] * 9


def test_product_names_are_unique(cat: Catalog) -> None:
    names = [p.name for p in cat.products.values()]

    assert len(names) == len(set(names))


def test_prices_have_two_decimals_and_are_positive(cat: Catalog) -> None:
    for p in cat.products.values():
        assert p.price > 0
        assert p.price == p.price.quantize(Decimal("0.01"))


def test_stock_is_consistent(cat: Catalog) -> None:
    for line in cat.stock.values():
        assert 0 <= line.reserved <= line.on_hand


def test_scenario_boundary_prices(cat: Catalog, scenarios: dict[str, dict]) -> None:
    s = scenarios["boundary_prices"]
    reference = cat.products[s["sku"]]
    alternatives = cat.alternatives(s["sku"], s["storeId"])

    low, high = reference.price * Decimal("0.8"), reference.price * Decimal("1.2")
    just_below = [
        p
        for p in cat.products.values()
        if p.type == reference.type and p.price == low - Decimal("0.01")
    ]

    assert not cat.in_stock(s["sku"], s["storeId"])
    assert sorted(p.price for p in alternatives) == [low, high]
    assert len(just_below) == 1, "un produit juste sous la borne basse doit exister"
    assert cat.in_stock(just_below[0].sku, s["storeId"]), "il doit être exclu par le prix seul"


def test_scenario_out_of_stock_with_alternative(cat: Catalog, scenarios: dict[str, dict]) -> None:
    s = scenarios["out_of_stock_with_alternative"]

    assert not cat.in_stock(s["sku"], s["storeId"])
    assert cat.alternatives(s["sku"], s["storeId"])


def test_scenario_out_of_stock_without_alternative(
    cat: Catalog, scenarios: dict[str, dict]
) -> None:
    s = scenarios["out_of_stock_without_alternative"]

    assert not cat.in_stock(s["sku"], s["storeId"])
    assert cat.alternatives(s["sku"], s["storeId"]) == []


def test_scenario_out_of_stock_everywhere(cat: Catalog, scenarios: dict[str, dict]) -> None:
    s = scenarios["out_of_stock_everywhere"]

    assert cat.stores_with_stock(s["sku"]) == []


def test_scenario_fully_reserved(cat: Catalog, scenarios: dict[str, dict]) -> None:
    s = scenarios["fully_reserved"]
    line = cat.stock[(s["sku"], s["storeId"])]

    assert line.on_hand > 0
    assert not cat.in_stock(s["sku"], s["storeId"])


def test_scenario_single_product_type(cat: Catalog, scenarios: dict[str, dict]) -> None:
    s = scenarios["single_product_type"]
    type_ = cat.products[s["sku"]].type

    assert sum(p.type == type_ for p in cat.products.values()) == 1
    assert cat.alternatives(s["sku"], s["storeId"]) == []


def test_scenarios_use_distinct_products(scenarios: dict[str, dict]) -> None:
    used = [s["sku"] for s in scenarios.values()]

    assert len(used) == len(set(used))


def test_cli_writes_a_version_with_its_manifest(tmp_path: Path) -> None:
    main(["--seed", str(SEED), "--version", "v1", "--data-dir", str(tmp_path)])

    version_dir = tmp_path / "v1"
    manifest = json.loads((version_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == SEED
    assert manifest["version"] == "v1"
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((version_dir / name).read_bytes()).hexdigest() == digest
    assert set(manifest["files"]) == {p.name for p in version_dir.iterdir()} - {"MANIFEST.json"}


def test_cli_refuses_to_overwrite_a_published_version(tmp_path: Path) -> None:
    main(["--seed", str(SEED), "--version", "v1", "--data-dir", str(tmp_path)])
    before = read_all(tmp_path / "v1")

    with pytest.raises(SystemExit):
        main(["--seed", "7", "--version", "v1", "--data-dir", str(tmp_path)])

    assert read_all(tmp_path / "v1") == before
