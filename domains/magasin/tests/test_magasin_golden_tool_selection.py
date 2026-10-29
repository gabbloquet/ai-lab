import json
from collections import Counter
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from magasin_golden_tool_selection import ANY, generate, main
from magasin_rules import Catalog, load_catalog

DOMAIN = Path(__file__).resolve().parents[1]
REPO = DOMAIN.parents[1]
SCHEMA = REPO / "evals" / "spec" / "tool-selection" / "v1" / "golden.schema.json"
INTENTS = ["availability", "alternative", "stores_with_stock", "product_details", "search"]


@pytest.fixture(scope="module")
def cat() -> Catalog:
    return load_catalog(DOMAIN / "data" / "v1")


@pytest.fixture(scope="module")
def scenario_rows() -> list[dict]:
    return json.loads((DOMAIN / "data" / "v1" / "scenarios.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def scenarios(scenario_rows: list[dict]) -> dict[str, dict]:
    return {row["id"]: row for row in scenario_rows}


@pytest.fixture(scope="module")
def items(cat: Catalog, scenario_rows: list[dict]) -> list[dict]:
    return generate(cat, scenario_rows, seed=42)


def of_intent(items: list[dict], intent: str) -> list[dict]:
    return [item for item in items if intent in item["tags"]]


def ref(item: dict) -> str:
    return next(tag for tag in item["tags"] if tag.startswith("ref:"))


def store(item: dict) -> str:
    return item["context"]["storeId"]


def target(item: dict) -> str:
    return item["expected"]["intent"]["required"][0]["args"]["sku"][0]


def test_builds_twenty_six_items_per_intent(items: list[dict]) -> None:
    assert len(items) == 130
    assert Counter(tag for item in items for tag in item["tags"] if tag in INTENTS) == {
        intent: 26 for intent in INTENTS
    }


def test_puts_six_items_of_each_intent_in_dev(items: list[dict]) -> None:
    for intent in INTENTS:
        assert Counter(item["split"] for item in of_intent(items, intent)) == {"dev": 6, "test": 20}


def test_balances_references_by_sku_and_by_name_in_each_split(items: list[dict]) -> None:
    for intent in INTENTS[:4]:
        counts = Counter((item["split"], ref(item)) for item in of_intent(items, intent))
        assert counts == {
            ("dev", "ref:sku"): 3,
            ("dev", "ref:name"): 3,
            ("test", "ref:sku"): 10,
            ("test", "ref:name"): 10,
        }


def test_gives_sequential_ids(items: list[dict]) -> None:
    assert [item["id"] for item in items] == [f"ts-{i:03d}" for i in range(1, 131)]


def test_every_item_matches_the_golden_schema(items: list[dict]) -> None:
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

    for item in items:
        assert list(validator.iter_errors(item)) == [], item["id"]


def test_never_requires_and_tolerates_the_same_tool(items: list[dict]) -> None:
    for item in items:
        for expectation in item["expected"].values():
            required = {pattern["tool"] for pattern in expectation["required"]}
            tolerated = {pattern["tool"] for pattern in expectation["tolerated"]}
            assert not required & tolerated, item["id"]


def test_requires_no_more_calls_than_the_ten_call_cap(items: list[dict]) -> None:
    for item in items:
        for expectation in item["expected"].values():
            assert len(expectation["required"]) <= 10, item["id"]


def test_is_reproducible_with_the_same_seed(
    cat: Catalog, scenario_rows: list[dict], items: list[dict]
) -> None:
    assert generate(cat, scenario_rows, seed=42) == items
    assert generate(cat, scenario_rows, seed=7) != items


def test_asks_each_question_once(items: list[dict]) -> None:
    questions = [item["question"] for item in items]

    assert len(questions) == len(set(questions))


def test_shows_the_sku_only_in_questions_by_reference(items: list[dict]) -> None:
    for item in items:
        if "search" in item["tags"]:
            continue
        shown = target(item) in item["question"]
        assert shown == (ref(item) == "ref:sku"), item["id"]


def test_names_the_product_in_questions_by_name(cat: Catalog, items: list[dict]) -> None:
    for item in items:
        if "search" not in item["tags"] and ref(item) == "ref:name":
            product = cat.products[target(item)]
            model = product.name.removeprefix(f"{product.brand} {product.type} ")
            assert product.brand in item["question"] and model in item["question"], item["id"]


def test_tolerates_the_search_tool_only_when_the_question_gives_a_name(items: list[dict]) -> None:
    for item in items:
        if "search" in item["tags"]:
            continue
        tolerated = {
            variant: {pattern["tool"] for pattern in expectation["tolerated"]}
            for variant, expectation in item["expected"].items()
        }
        by_name = ref(item) == "ref:name"
        assert ("search_catalog" in tolerated["intent"]) == by_name, item["id"]
        assert ("list_products" in tolerated["rest"]) == by_name, item["id"]


def test_checks_availability_in_the_current_store(cat: Catalog, items: list[dict]) -> None:
    availability = of_intent(items, "availability")

    for item in availability:
        args = {"sku": [target(item)], "storeId": [store(item)]}
        assert item["expected"]["intent"]["required"] == [
            {"tool": "check_availability", "args": args}
        ]
        assert item["expected"]["rest"]["required"] == [{"tool": "get_stock", "args": args}]
    out_of_stock = [item for item in availability if not cat.in_stock(target(item), store(item))]
    assert len(out_of_stock) == 9


def test_asks_for_an_alternative_only_when_the_product_is_out_of_stock_here(
    cat: Catalog, items: list[dict]
) -> None:
    for item in of_intent(items, "alternative"):
        assert not cat.in_stock(target(item), store(item)), item["id"]
        assert item["expected"]["intent"]["required"] == [
            {
                "tool": "find_in_stock_alternative",
                "args": {"sku": [target(item)], "storeId": [store(item)]},
            }
        ]


def test_rest_needs_a_stock_check_on_one_of_the_alternatives_the_intent_tool_returns(
    cat: Catalog, items: list[dict]
) -> None:
    with_alternative = [
        item
        for item in of_intent(items, "alternative")
        if cat.alternatives(target(item), store(item))
    ]

    assert len(with_alternative) == 18
    for item in with_alternative:
        alternatives = [p.sku for p in cat.alternatives(target(item), store(item))]
        assert item["expected"]["rest"]["required"] == [
            {"tool": "get_similar", "args": {"sku": [target(item)]}},
            {"tool": "get_stock", "args": {"sku": alternatives, "storeId": [store(item)]}},
        ]


def test_rest_needs_a_stock_check_on_every_similar_product_when_none_is_available(
    cat: Catalog, items: list[dict]
) -> None:
    without_alternative = [
        item
        for item in of_intent(items, "alternative")
        if not cat.alternatives(target(item), store(item))
    ]

    assert len(without_alternative) == 8
    for item in without_alternative:
        assert item["expected"]["rest"]["required"] == [
            {"tool": "get_similar", "args": {"sku": [target(item)]}}
        ] + [
            {"tool": "get_stock", "args": {"sku": [p.sku], "storeId": [store(item)]}}
            for p in cat.similar(target(item))
        ]


def test_covers_the_alternative_scenarios_of_the_domain(
    items: list[dict], scenarios: dict[str, dict]
) -> None:
    asked = {(target(item), store(item)) for item in of_intent(items, "alternative")}

    for scenario in (
        "boundary_prices",
        "out_of_stock_with_alternative",
        "out_of_stock_without_alternative",
        "single_product_type",
    ):
        assert (scenarios[scenario]["sku"], scenarios[scenario]["storeId"]) in asked, scenario


def test_rest_checks_every_store_to_find_the_ones_with_stock(
    cat: Catalog, items: list[dict], scenarios: dict[str, dict]
) -> None:
    stores_items = of_intent(items, "stores_with_stock")

    for item in stores_items:
        assert item["expected"]["intent"]["required"] == [
            {"tool": "find_stores_with_stock", "args": {"sku": [target(item)]}}
        ]
        assert item["expected"]["rest"]["required"] == [
            {"tool": "get_stock", "args": {"sku": [target(item)], "storeId": [store_id]}}
            for store_id in sorted(cat.stores)
        ]
        assert {"tool": "list_stores", "args": {}} in item["expected"]["rest"]["tolerated"]
    assert scenarios["out_of_stock_everywhere"]["sku"] in {target(item) for item in stores_items}


def test_asks_for_the_details_of_distinct_products(items: list[dict]) -> None:
    details = of_intent(items, "product_details")

    for item in details:
        assert item["expected"]["intent"]["required"] == [
            {"tool": "get_product_details", "args": {"sku": [target(item)]}}
        ]
        assert item["expected"]["rest"]["required"] == [
            {"tool": "get_product", "args": {"sku": [target(item)]}}
        ]
    assert len({target(item) for item in details}) == 26


def test_searches_with_a_free_query_and_an_optional_category(
    cat: Catalog, items: list[dict]
) -> None:
    departments = {p.department for p in cat.products.values()}

    for item in of_intent(items, "search"):
        intent, rest = item["expected"]["intent"], item["expected"]["rest"]
        assert [p["tool"] for p in intent["required"]] == ["search_catalog"]
        assert [p["tool"] for p in rest["required"]] == ["list_products"]
        for pattern in (intent["required"][0], rest["required"][0]):
            assert pattern["args"] == {"query": ANY}
            category = pattern["optional"]["category"]
            if "search:absent" in item["tags"]:
                assert category == ANY
            else:
                assert len(category) == 1 and category[0] in departments
        assert intent["tolerated"] == rest["tolerated"] == []
    assert sum("search:absent" in item["tags"] for item in of_intent(items, "search")) == 4


def test_cli_writes_the_items_and_their_manifest(tmp_path: Path) -> None:
    main(["--seed", "42", "--version", "v1", "--data-version", "v1", "--golden-dir", str(tmp_path)])

    lines = (tmp_path / "v1" / "items.jsonl").read_text(encoding="utf-8").splitlines()
    manifest = json.loads((tmp_path / "v1" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert len(lines) == 130
    assert manifest["seed"] == 42
    assert manifest["data_version"] == "v1"
    assert manifest["spec"] == "evals/spec/tool-selection/v1"
    assert set(manifest["files"]) == {"items.jsonl"}


def test_cli_refuses_to_overwrite_a_version(tmp_path: Path) -> None:
    (tmp_path / "v1").mkdir()
    (tmp_path / "v1" / "items.jsonl").write_text("{}\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        main(
            [
                "--seed",
                "42",
                "--version",
                "v1",
                "--data-version",
                "v1",
                "--golden-dir",
                str(tmp_path),
            ]
        )
