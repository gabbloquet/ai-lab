"""Rejoue les vecteurs de conformance de la spec rag-qa v1 (SPEC.md § 9) : le scorer Python est
conforme s'il reproduit exactement les entiers, les booléens, les chaînes et les `null`, et les
nombres réels à 1e-9 près."""

import json
from pathlib import Path

import pytest

from ailab_evals.rag_qa import (
    PairedScore,
    aggregate,
    fact_found,
    normalize,
    normalize_citation,
    score_execution,
)

VECTORS = Path(__file__).resolve().parents[2] / "spec" / "rag-qa" / "v1" / "conformance.jsonl"
TOLERANCE = 1e-9


def _vectors(kind: str) -> list[dict]:
    lines = VECTORS.read_text(encoding="utf-8").splitlines()
    return [vector for vector in map(json.loads, lines) if vector["kind"] == kind]


def _assert_conforms(actual: dict, expected: dict, vector_id: str) -> None:
    assert set(actual) == set(expected), vector_id
    for name, want in expected.items():
        got = actual[name]
        if isinstance(want, float):
            assert isinstance(got, float), f"{vector_id} {name}: {got!r}"
            assert abs(got - want) <= TOLERANCE, f"{vector_id} {name}: {got}"
        else:
            assert got == want and type(got) is type(want), f"{vector_id} {name}: {got!r}"


@pytest.mark.parametrize("vector", _vectors("execution"), ids=lambda v: v["id"])
def test_scores_each_execution_like_the_spec(vector: dict) -> None:
    score = score_execution(vector["item"], vector["execution"])

    _assert_conforms(score.as_dict(), vector["expected"], vector["id"])


@pytest.mark.parametrize("vector", _vectors("aggregate"), ids=lambda v: v["id"])
def test_aggregates_each_series_like_the_spec(vector: dict) -> None:
    rows = [PairedScore(e["item_id"], e["split"], e["p_a"], e["p_b"]) for e in vector["items"]]

    result = aggregate(rows)

    _assert_conforms(result.as_dict(), vector["expected"], vector["id"])


@pytest.mark.parametrize(
    ("text", "normalized"),
    [
        ("Délai de 1 500 €.", "delai de 1500 €."),  # exemple de la spec (§ 4)
        ("L’Œuvre", "l'oeuvre"),  # exemple de la spec (§ 4)
        ("  deux   espaces\tet\nretours  ", "deux espaces et retours"),
        ("1 000 000", "1000000"),
        ("Straße", "strasse"),  # casefold complet, pas lower()
        ("é", "e"),  # accent combinant
        ("ÆON", "aeon"),
        ("quatorze jours", "quatorze jours"),  # les nombres en lettres ne changent pas
        ("1 et 2", "1 et 2"),  # seules les espaces entre deux chiffres disparaissent
    ],
)
def test_normalizes_text_like_the_spec(text: str, normalized: str) -> None:
    assert normalize(text) == normalized


@pytest.mark.parametrize(
    ("citation", "normalized"),
    [
        ("Article L. 221-18", "L221-18"),
        ("articles L. 221-18", "L221-18"),
        ("art. L. 221-18", "L221-18"),
        ("l. 221-18", "L221-18"),
        ("L221-18", "L221-18"),
        ("liminaire", "LIMINAIRE"),
    ],
)
def test_normalizes_citations_like_the_spec(citation: str, normalized: str) -> None:
    assert normalize_citation(citation) == normalized


@pytest.mark.parametrize(
    ("form", "answer", "found"),
    [
        ("14 jours", "Sous 14 jours.", True),
        ("14 jours", "114 jours", False),
        ("14 jours", "14 joursx", False),
        ("14 jours", "14 jours²", False),  # ² est de catégorie No : un chiffre au sens de la spec
        ("jours", "14 jours", True),
        ("a", "à", True),  # la forme et la réponse passent toutes deux par N
    ],
)
def test_finds_a_form_only_where_it_is_delimited(form: str, answer: str, found: bool) -> None:
    assert fact_found({"accepted": [form]}, answer) is found
