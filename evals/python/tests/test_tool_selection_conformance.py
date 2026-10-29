"""Rejoue les vecteurs de conformance de la spec tool-selection v1 (SPEC.md § 8) : le scorer
Python est conforme s'il reproduit exactement les entiers, les booléens et les verdicts, et les
nombres réels à 1e-9 près."""

import json
from pathlib import Path

import pytest
from ailab_evals.tool_selection import PairedScore, aggregate, score_execution, values_equal

VECTORS = (
    Path(__file__).resolve().parents[2] / "spec" / "tool-selection" / "v1" / "conformance.jsonl"
)
TOLERANCE = 1e-9


def _vectors(kind: str) -> list[dict]:
    lines = VECTORS.read_text(encoding="utf-8").splitlines()
    return [vector for vector in map(json.loads, lines) if vector["kind"] == kind]


def _assert_conforms(actual: dict, expected: dict, vector_id: str) -> None:
    for name, want in expected.items():
        got = actual[name]
        if isinstance(want, float) and not isinstance(want, bool):
            assert got is not None and abs(got - want) <= TOLERANCE, f"{vector_id} {name}: {got}"
        else:
            assert got == want and type(got) is type(want), f"{vector_id} {name}: {got!r}"


@pytest.mark.parametrize("vector", _vectors("execution"), ids=lambda v: v["id"])
def test_scores_each_execution_like_the_spec(vector: dict) -> None:
    execution = vector["execution"]
    expectation = vector["item"]["expected"][execution["variant"]]

    score = score_execution(expectation, execution["calls"], execution["error"])

    _assert_conforms(score.as_dict(), vector["expected"], vector["id"])


@pytest.mark.parametrize("vector", _vectors("aggregate"), ids=lambda v: v["id"])
def test_aggregates_each_series_like_the_spec(vector: dict) -> None:
    rows = [PairedScore(e["item_id"], e["split"], e["p_a"], e["p_b"]) for e in vector["items"]]

    result = aggregate(rows)

    _assert_conforms(result.as_dict(), vector["expected"], vector["id"])


@pytest.mark.parametrize(
    ("a", "b", "equal"),
    [
        (True, 1, False),
        (1, True, False),
        (False, 0, False),
        (True, True, True),
        (None, None, True),
        (None, "", False),
        (2, 2.0, True),
        ("2", 2, False),
        ([1, "A"], [1.0, " a "], True),
        ([1, 2], [2, 1], False),
        ({"k": "\u00c9"}, {"k": "e\u0301"}, True),
        ({"k": "\u00c9"}, {"k": "e"}, False),
        ({"k": 1}, {"k": 1, "x": 2}, False),
    ],
)
def test_compares_values_with_the_rules_of_the_spec(a: object, b: object, equal: bool) -> None:
    assert values_equal(a, b) is equal
