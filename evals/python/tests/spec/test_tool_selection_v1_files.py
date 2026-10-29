"""Vérifie les fichiers partagés de la spec tool-selection v1 : le schéma du golden set et les
vecteurs de conformance. Les scorers, eux, vérifient qu'ils reproduisent les métriques attendues."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SPEC_DIR = Path(__file__).resolve().parents[3] / "spec" / "tool-selection" / "v1"

# Cas à couvrir au minimum (SPEC.md § 8), plus ceux du verdict (§ 7).
MINIMUM_CASES = {
    "appel parfait",
    "outil faux",
    "argument faux",
    "argument halluciné",
    "argument facultatif omis",
    "argument facultatif présent mais faux",
    "argument non contraint",
    "appel requis manquant",
    "appel en double",
    "appel toléré",
    "outil inconnu",
    "erreur d'exécution",
    "aucun appel",
    "motifs du même outil qui se recouvrent",
    "chaînes : casse",
    "chaînes : espaces",
    "chaînes : NFC",
    "chaînes : P-1569 contre P-15695",
    "nombres : 2 contre 2.0",
    'nombres : "2" contre 2',
    "items dev ignorés",
    "B meilleure",
    "B moins bonne",
    "non concluant",
}

EXECUTION_METRICS = {
    "tool_recall",
    "args_recall",
    "precision",
    "extra_calls",
    "n_calls",
    "success",
    "strict_success",
}
AGGREGATE_RESULTS = {"n", "delta", "ci_low", "ci_high", "verdict"}

SPEC_ITEM = {
    "id": "ts-001",
    "split": "test",
    "question": "Le casque Veldric K8 est en rupture ici, tu as un équivalent dispo ?",
    "context": {"storeId": "S02"},
    "tags": ["alternative"],
    "expected": {
        "intent": {
            "required": [
                {
                    "tool": "find_in_stock_alternative",
                    "args": {"sku": ["P-15695"], "storeId": ["S02"]},
                }
            ],
            "tolerated": [],
        },
        "rest": {
            "required": [
                {"tool": "get_similar", "args": {"sku": ["P-15695"]}},
                {"tool": "get_stock", "args": {"sku": ["P-26361", "P-44671"], "storeId": ["S02"]}},
            ],
            "tolerated": [{"tool": "get_product", "args": {"sku": ["P-15695"]}}],
        },
    },
}


@pytest.fixture(scope="module")
def validator():
    schema = json.loads((SPEC_DIR / "golden.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture(scope="module")
def vectors():
    lines = (SPEC_DIR / "conformance.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _mutated(change):
    item = copy.deepcopy(SPEC_ITEM)
    change(item)
    return item


def test_accepts_the_item_given_as_example_by_the_spec(validator):
    assert list(validator.iter_errors(SPEC_ITEM)) == []


def test_accepts_optional_and_unconstrained_arguments(validator):
    item = _mutated(
        lambda i: i["expected"]["intent"].update(
            required=[
                {
                    "tool": "search_catalog",
                    "args": {"query": {"any": True}},
                    "optional": {"category": ["Audio"]},
                }
            ]
        )
    )

    assert list(validator.iter_errors(item)) == []


@pytest.mark.parametrize(
    ("case", "change"),
    [
        ("split inconnu", lambda i: i.update(split="train")),
        ("question vide", lambda i: i.update(question="")),
        ("sans tag", lambda i: i.update(tags=[])),
        ("champ inconnu", lambda i: i.update(answer="P-26361")),
        ("sans variante", lambda i: i.update(expected={})),
        ("aucun appel requis", lambda i: i["expected"]["intent"].update(required=[])),
        ("sans liste de tolérés", lambda i: i["expected"]["intent"].pop("tolerated")),
        ("motif sans outil", lambda i: i["expected"]["intent"]["required"][0].pop("tool")),
        (
            "nom d'outil avec espace",
            lambda i: i["expected"]["intent"]["required"][0].update(tool="find alt"),
        ),
        (
            "motif avec champ inconnu",
            lambda i: i["expected"]["intent"]["required"][0].update(weight=2),
        ),
        (
            "valeur seule au lieu d'une liste",
            lambda i: i["expected"]["intent"]["required"][0]["args"].update(sku="P-15695"),
        ),
        (
            "liste de valeurs vide",
            lambda i: i["expected"]["intent"]["required"][0]["args"].update(sku=[]),
        ),
        (
            "any à false",
            lambda i: i["expected"]["intent"]["required"][0]["args"].update(sku={"any": False}),
        ),
    ],
)
def test_rejects_a_malformed_item(validator, case, change):
    assert list(validator.iter_errors(_mutated(change))), case


def test_gives_each_vector_a_unique_id(vectors):
    ids = [vector["id"] for vector in vectors]

    assert len(ids) == len(set(ids))


def test_covers_every_minimum_case_with_known_names(vectors):
    covered = {case for vector in vectors for case in vector["covers"]}

    assert covered >= MINIMUM_CASES
    assert covered <= MINIMUM_CASES | {
        "appel toléré avec des arguments faux",
        "nom d'outil sensible à la casse",
        "argument facultatif présent et juste",
        "argument non contraint absent",
        "IC nul",
        "booléen contre nombre",
    }


def test_describes_each_execution_with_a_valid_item_and_every_metric(validator, vectors):
    executions = [vector for vector in vectors if vector["kind"] == "execution"]

    assert executions
    for vector in executions:
        assert list(validator.iter_errors(vector["item"])) == [], vector["id"]
        assert vector["execution"]["item_id"] == vector["item"]["id"], vector["id"]
        assert vector["execution"]["variant"] in vector["item"]["expected"], vector["id"]
        assert set(vector["expected"]) == EXECUTION_METRICS, vector["id"]


def test_never_requires_and_tolerates_the_same_tool(vectors):
    for vector in vectors:
        if vector["kind"] != "execution":
            continue
        for expectation in vector["item"]["expected"].values():
            required = {pattern["tool"] for pattern in expectation["required"]}
            tolerated = {pattern["tool"] for pattern in expectation["tolerated"]}
            assert not required & tolerated, vector["id"]


def test_describes_each_aggregate_with_paired_scores_and_a_verdict(vectors):
    aggregates = [vector for vector in vectors if vector["kind"] == "aggregate"]

    assert aggregates
    assert any(
        {entry["split"] for entry in vector["items"]} == {"dev", "test"} for vector in aggregates
    )
    for vector in aggregates:
        assert set(vector["expected"]) == AGGREGATE_RESULTS, vector["id"]
        assert vector["expected"]["verdict"] in {"b_better", "b_worse", "inconclusive"}, vector[
            "id"
        ]
        assert vector["expected"]["n"] == sum(entry["split"] == "test" for entry in vector["items"])
        for entry in vector["items"]:
            assert entry["split"] in {"dev", "test"}, vector["id"]
            assert 0 <= entry["p_a"] <= 1 and 0 <= entry["p_b"] <= 1, vector["id"]


def test_knows_only_two_kinds_of_vectors(vectors):
    assert {vector["kind"] for vector in vectors} == {"execution", "aggregate"}
