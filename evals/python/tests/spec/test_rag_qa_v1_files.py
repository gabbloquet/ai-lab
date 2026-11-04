"""Vérifie les fichiers partagés de la spec rag-qa v1 : le schéma du golden set et les vecteurs de
conformance. Les scorers, eux, vérifient qu'ils reproduisent les métriques attendues."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SPEC_DIR = Path(__file__).resolve().parents[3] / "spec" / "rag-qa" / "v1"

# Cas à couvrir au minimum (SPEC.md § 9).
MINIMUM_CASES = {
    "réponse juste",
    "fait manquant",
    "un fait retrouvé sur deux",
    "plusieurs formes acceptées",
    "abstention sur un item avec réponse",
    "abstention qui l'emporte sur une réponse juste",
    "abstention juste sur un item sans réponse",
    "hallucination",
    "réponse vide",
    "erreur d'exécution",
    "normalisation : casse",
    "normalisation : accents",
    "normalisation : apostrophe typographique",
    "normalisation : espace insécable",
    "normalisation : espaces entre chiffres",
    "normalisation : ligature",
    "délimitation : 114 jours",
    "délimitation : 14 joursx",
    "délimitation : début de réponse",
    "délimitation : fin de réponse",
    "délimitation : ponctuation",
    "contexte nul",
    "contexte plus court que k",
    "article attendu au rang 1",
    "article attendu au rang 4",
    "article attendu absent",
    "un article attendu sur deux",
    "retrieval_miss",
    "generation_miss",
    "erreur avec contexte",
    "contexte avec doublon",
    "citation : Article L. 221-18",
    "citation : art. L. 221-18",
    "citation : L221-18",
    "citation : l. 221-18",
    "citation en double",
    "aucune citation",
    "citation fausse",
    "citation : plage dans un seul élément",
    "B meilleure",
    "B moins bonne",
    "non concluant",
    "items dev ignorés",
}
EXTRA_CASES = {
    "deux faits retrouvés",
    "délimitation : une occurrence délimitée suffit",
    "IC nul",
}

KS = (1, 3, 5, 10)
EXECUTION_METRICS = {
    "correct",
    "facts_found",
    "false_abstention",
    "hallucination",
    *(f"evidence_recall@{k}" for k in KS),
    *(f"all_evidence@{k}" for k in KS),
    "context_size",
    "failure",
    "citation_precision",
    "citation_recall",
}
EXECUTION_FIELDS = {
    "item_id",
    "variant",
    "model",
    "repeat",
    "answer",
    "abstained",
    "cited",
    "context",
    "usage",
    "error",
}
AGGREGATE_RESULTS = {"n", "delta", "ci_low", "ci_high", "verdict"}

SPEC_ITEM = {
    "id": "rq-001",
    "split": "dev",
    "mode": "paraphrase",
    "answerable": True,
    "question": "J'ai acheté un aspirateur en ligne, combien de temps ai-je pour changer d'avis ?",
    "expected": {
        "facts": [{"accepted": ["quatorze jours", "14 jours"]}],
        "articles": [{"id": "LEGIARTI000032226842", "num": "L221-18"}],
    },
    "evidence": [
        {"article": "LEGIARTI000032226842", "quote": "dispose d'un délai de quatorze jours"}
    ],
}

UNANSWERABLE_ITEM = {
    "id": "rq-002",
    "split": "test",
    "mode": "unanswerable",
    "answerable": False,
    "question": "Combien coûte un timbre fiscal pour une réclamation ?",
    "expected": {"facts": [], "articles": []},
    "evidence": [],
    "source_article": "LEGIARTI000032226842",
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


def _mutated(item, change):
    item = copy.deepcopy(item)
    change(item)
    return item


def test_accepts_the_item_given_as_example_by_the_spec(validator):
    assert list(validator.iter_errors(SPEC_ITEM)) == []


def test_accepts_an_unanswerable_item(validator):
    assert list(validator.iter_errors(UNANSWERABLE_ITEM)) == []


@pytest.mark.parametrize(
    ("case", "change"),
    [
        ("split inconnu", lambda i: i.update(split="train")),
        ("identifiant mal formé", lambda i: i.update(id="rq1")),
        ("mode vide", lambda i: i.update(mode="")),
        ("answerable absent", lambda i: i.pop("answerable")),
        ("question vide", lambda i: i.update(question="")),
        ("question faite d'espaces", lambda i: i.update(question="   ")),
        ("champ inconnu", lambda i: i.update(answer="14 jours")),
        ("aucun fait", lambda i: i["expected"].update(facts=[])),
        ("aucun article", lambda i: i["expected"].update(articles=[])),
        ("aucune citation du corpus", lambda i: i.update(evidence=[])),
        ("fait sans forme", lambda i: i["expected"]["facts"][0].update(accepted=[])),
        ("forme vide", lambda i: i["expected"]["facts"][0].update(accepted=[""])),
        ("forme en double", lambda i: i["expected"]["facts"][0].update(accepted=["a", "a"])),
        ("fait avec champ inconnu", lambda i: i["expected"]["facts"][0].update(weight=1)),
        ("article sans numéro", lambda i: i["expected"]["articles"][0].pop("num")),
        ("article sans id", lambda i: i["expected"]["articles"][0].pop("id")),
        ("extrait vide", lambda i: i["evidence"][0].update(quote="")),
    ],
)
def test_rejects_a_malformed_answerable_item(validator, case, change):
    assert list(validator.iter_errors(_mutated(SPEC_ITEM, change))), case


@pytest.mark.parametrize(
    ("case", "change"),
    [
        ("fait attendu", lambda i: i["expected"].update(facts=[{"accepted": ["x"]}])),
        (
            "article attendu",
            lambda i: i["expected"].update(articles=[{"id": "LEGIARTI1", "num": "L1"}]),
        ),
    ],
)
def test_rejects_an_unanswerable_item_that_expects_something(validator, case, change):
    assert list(validator.iter_errors(_mutated(UNANSWERABLE_ITEM, change))), case


def test_gives_each_vector_a_unique_id(vectors):
    ids = [vector["id"] for vector in vectors]

    assert len(ids) == len(set(ids))


def test_covers_every_minimum_case_with_known_names(vectors):
    covered = {case for vector in vectors for case in vector["covers"]}

    assert covered >= MINIMUM_CASES
    assert covered <= MINIMUM_CASES | EXTRA_CASES


def test_describes_each_execution_with_a_valid_item_and_every_metric(validator, vectors):
    executions = [vector for vector in vectors if vector["kind"] == "execution"]

    assert executions
    for vector in executions:
        assert list(validator.iter_errors(vector["item"])) == [], vector["id"]
        assert set(vector["execution"]) == EXECUTION_FIELDS, vector["id"]
        assert vector["execution"]["item_id"] == vector["item"]["id"], vector["id"]
        assert set(vector["expected"]) == EXECUTION_METRICS, vector["id"]
        assert vector["expected"]["failure"] in {
            None,
            "correct",
            "retrieval_miss",
            "generation_miss",
            "error",
        }, vector["id"]


def test_describes_each_aggregate_with_paired_scores_and_a_verdict(vectors):
    aggregates = [vector for vector in vectors if vector["kind"] == "aggregate"]

    assert aggregates
    assert any(
        {entry["split"] for entry in vector["items"]} == {"dev", "test"} for vector in aggregates
    )
    for vector in aggregates:
        assert set(vector["expected"]) == AGGREGATE_RESULTS, vector["id"]
        assert vector["expected"]["verdict"] in {"b_better", "b_worse", "inconclusive"}
        assert vector["expected"]["n"] == sum(entry["split"] == "test" for entry in vector["items"])
        for entry in vector["items"]:
            assert entry["split"] in {"dev", "test"}, vector["id"]
            assert 0 <= entry["p_a"] <= 1 and 0 <= entry["p_b"] <= 1, vector["id"]


def test_knows_only_two_kinds_of_vectors(vectors):
    assert {vector["kind"] for vector in vectors} == {"execution", "aggregate"}
