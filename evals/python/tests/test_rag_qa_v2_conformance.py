"""Rejoue les vecteurs de conformance de la spec rag-qa v2 (SPEC.md § 9) : le scorer Python est
conforme s'il reproduit exactement les entiers, les booléens, les chaînes et les `null`, et les
nombres réels à 1e-9 près."""

import json
from pathlib import Path

import pytest

from ailab_evals import rag_qa_v2 as scorer

VECTORS = Path(__file__).resolve().parents[2] / "spec" / "rag-qa" / "v2" / "conformance.jsonl"
TOLERANCE = 1e-9


def _vectors(kind: str) -> list[dict]:
    lines = VECTORS.read_text(encoding="utf-8").splitlines()
    return [vector for vector in map(json.loads, lines) if vector["kind"] == kind]


def _assert_conforms(actual, expected, where: str) -> None:
    """Compare récursivement : mêmes clés, mêmes types, réels à TOLERANCE près."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{where}: {actual!r}"
        assert set(actual) == set(expected), f"{where}: {sorted(set(actual) ^ set(expected))}"
        for key, want in expected.items():
            _assert_conforms(actual[key], want, f"{where}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), f"{where}: {actual!r}"
        for index, (got, want) in enumerate(zip(actual, expected, strict=True)):
            _assert_conforms(got, want, f"{where}[{index}]")
    elif isinstance(expected, float):
        assert isinstance(actual, float), f"{where}: {actual!r}"
        assert abs(actual - expected) <= TOLERANCE, f"{where}: {actual} au lieu de {expected}"
    else:
        assert actual == expected and type(actual) is type(expected), f"{where}: {actual!r}"


@pytest.mark.parametrize("vector", _vectors("execution"), ids=lambda v: v["id"])
def test_scores_each_execution_like_the_spec(vector: dict) -> None:
    result = scorer.score_execution(vector["item"], vector["execution"])

    _assert_conforms(result, vector["expected"], vector["id"])


@pytest.mark.parametrize("vector", _vectors("aggregate"), ids=lambda v: v["id"])
def test_compares_each_paired_series_like_the_spec(vector: dict) -> None:
    pairs = [
        scorer.PairedScore(e["item_id"], e["split"], e["p_a"], e["p_b"]) for e in vector["items"]
    ]

    result = scorer.paired_comparison(pairs, "higher_better")

    _assert_conforms({k: result[k] for k in vector["expected"]}, vector["expected"], vector["id"])


@pytest.mark.parametrize("vector", _vectors("variant"), ids=lambda v: v["id"])
def test_aggregates_each_variant_like_the_spec(vector: dict) -> None:
    result = scorer.variant_aggregates(
        vector["items"], vector["executions"], split=vector["split"], excluded=vector["excluded"]
    )

    _assert_conforms(result, vector["expected"], vector["id"])


@pytest.mark.parametrize("vector", _vectors("comparison"), ids=lambda v: v["id"])
def test_compares_each_metric_like_the_spec(vector: dict) -> None:
    result = scorer.compare(
        vector["items"],
        vector["executions"],
        baseline=vector["baseline"],
        variant=vector["variant"],
        metric=vector["metric"],
        direction=vector["direction"],
        split=vector["split"],
        excluded=vector["excluded"],
    )

    _assert_conforms(result, vector["expected"], vector["id"])


@pytest.mark.parametrize("vector", _vectors("joint"), ids=lambda v: v["id"])
def test_judges_each_joint_verdict_like_the_spec(vector: dict) -> None:
    result = scorer.joint_comparison(
        vector["items"],
        vector["executions"],
        baseline=vector["baseline"],
        variant=vector["variant"],
        main=(vector["main"]["metric"], vector["main"]["direction"]),
        guard=(vector["guard"]["metric"], vector["guard"]["direction"]),
        margin=vector["margin"],
        split=vector["split"],
        excluded=vector["excluded"],
    )

    _assert_conforms(result, vector["expected"], vector["id"])


@pytest.mark.parametrize("vector", _vectors("family"), ids=lambda v: v["id"])
def test_corrects_each_family_like_the_spec(vector: dict) -> None:
    comparisons = [
        scorer.FamilyMember(
            name=c["name"],
            direction=c["direction"],
            pairs=[
                scorer.PairedScore(e["item_id"], e["split"], e["p_a"], e["p_b"]) for e in c["items"]
            ],
        )
        for c in vector["comparisons"]
    ]

    result = scorer.holm_family(comparisons, alpha=vector["alpha"])

    _assert_conforms(result, vector["expected"], vector["id"])


@pytest.mark.parametrize(
    ("text", "normalized"),
    [
        ("Délai de 1 500 €.", "delai de 1500€."),  # exemple du § 4
        ("10 % du prix", "10% du prix"),  # exemple du § 4
        ("L’Œuvre", "l'oeuvre"),  # exemple du § 4
    ],
)
def test_normalizes_the_examples_of_the_spec(text: str, normalized: str) -> None:
    assert scorer.normalize(text) == normalized


def test_splits_words_like_the_example_of_the_spec() -> None:
    """§ 5.2 : « d'evaluer et controler l'activite »."""
    assert scorer.words("d'evaluer et controler l'activite") == [
        "d",
        "evaluer",
        "et",
        "controler",
        "l",
        "activite",
    ]
