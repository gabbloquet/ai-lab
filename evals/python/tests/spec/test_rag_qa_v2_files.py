"""Vérifie les fichiers partagés de la spec rag-qa v2 : les schémas des items et des exécutions, et les
vecteurs de conformance. Les scorers, eux, vérifient qu'ils reproduisent les résultats attendus."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SPEC_DIR = Path(__file__).resolve().parents[3] / "spec" / "rag-qa" / "v2"
V1_DIR = SPEC_DIR.parent / "v1"

# Exemples du § 3.1. SPEC_ITEM et UNANSWERABLE_ITEM sont ceux du test v1.
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

ANCHORED_ITEM = {
    "id": "rq-003",
    "split": "test",
    "mode": "comparison",
    "answerable": True,
    "question": (
        "Amende maximale pour une société : numéros masqués, et contenus numériques non fournis ?"
    ),
    "expected": {
        "facts": [
            {
                "accepted": ["375 000 €", "375 000 euros"],
                "anchor": ["numéros masqués", "démarchage téléphonique"],
            },
            {"accepted": ["15 000 euros", "15 000 €"], "anchor": ["contenus", "services numériques"]},
        ],
        "articles": [{"id": "LEGIARTI1", "num": "L1"}, {"id": "LEGIARTI2", "num": "L2"}],
    },
    "evidence": [
        {"article": "LEGIARTI1", "quote": "375 000 € pour une personne morale"},
        {"article": "LEGIARTI2", "quote": "15 000 euros pour une personne morale"},
    ],
}

TOKENS_FORM = {"tokens": ["évaluer", "activité"], "window": 4}
FALSE_VALUE = {"accepted": ["30 jours", "trente jours"]}

# Exemple du § 3.2, recopié tel quel.
SPEC_EXECUTION = {
    "item_id": "rq-001",
    "variant": "naive_rag",
    "model": "<fournisseur>/<modèle>",
    "repeat": 0,
    "answer": "Vous disposez de 14 jours.",
    "abstained": False,
    "cited": ["L. 221-18"],
    "context": ["LEGIARTI000032226842", "LEGIARTI000032226840"],
    "usage": {"input_tokens": 1830, "output_tokens": 42},
    "latency_s": 1.42,
    "cost_usd": 0.00031,
    "tool_calls": None,
    "error": None,
}
NEW_FIELDS_V2 = {"latency_s": None, "cost_usd": None, "tool_calls": None}


def _load(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _mutated(item, change):
    item = copy.deepcopy(item)
    change(item)
    return item


def _fact(item, index=0):
    return item["expected"]["facts"][index]


@pytest.fixture(scope="module")
def golden_validator():
    return _load(SPEC_DIR / "golden.schema.json")


@pytest.fixture(scope="module")
def execution_validator():
    return _load(SPEC_DIR / "execution.schema.json")


@pytest.fixture(scope="module")
def v1_vectors():
    lines = (V1_DIR / "conformance.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


# --- Bloc 1 : schéma des items (§ 3.1) ----------------------------------------------------------


@pytest.mark.parametrize(
    "item",
    [
        SPEC_ITEM,
        UNANSWERABLE_ITEM,
        ANCHORED_ITEM,
        _mutated(SPEC_ITEM, lambda i: _fact(i)["accepted"].append(TOKENS_FORM)),
        _mutated(SPEC_ITEM, lambda i: i.update(false_value=FALSE_VALUE)),
    ],
    ids=["exemple", "sans réponse", "faits ancrés", "forme à mots-clés", "fausse valeur"],
)
def test_accepts_the_items_of_the_spec(golden_validator, item):
    assert list(golden_validator.iter_errors(item)) == []


def test_accepts_every_item_valid_in_v1(golden_validator, v1_vectors):
    """SPEC.md § 0 : un item v1 valide reste valide en v2."""
    items = [SPEC_ITEM, UNANSWERABLE_ITEM]
    items += [vector["item"] for vector in v1_vectors if vector["kind"] == "execution"]

    for item in items:
        assert list(golden_validator.iter_errors(item)) == [], item["id"]


# Les 17 cas du test v1, recopiés tels quels : la v1 est figée, son test aussi.
V1_MALFORMED = [
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
    ("fait sans forme", lambda i: _fact(i).update(accepted=[])),
    ("forme vide", lambda i: _fact(i).update(accepted=[""])),
    ("forme en double", lambda i: _fact(i).update(accepted=["a", "a"])),
    ("fait avec champ inconnu", lambda i: _fact(i).update(weight=1)),
    ("article sans numéro", lambda i: i["expected"]["articles"][0].pop("num")),
    ("article sans id", lambda i: i["expected"]["articles"][0].pop("id")),
    ("extrait vide", lambda i: i["evidence"][0].update(quote="")),
]


def _add_form(form):
    return lambda i: _fact(i)["accepted"].append(form)


MALFORMED = V1_MALFORMED + [
    # Forme à mots-clés (§ 5.2).
    ("un seul mot-clé", _add_form({"tokens": ["jours"], "window": 0})),
    ("mot-clé avec espace", _add_form({"tokens": ["14 jours", "délai"], "window": 0})),
    ("mot-clé vide", _add_form({"tokens": ["", "délai"], "window": 0})),
    ("fenêtre de 6", _add_form({**TOKENS_FORM, "window": 6})),
    ("fenêtre négative", _add_form({**TOKENS_FORM, "window": -1})),
    ("fenêtre non entière", _add_form({**TOKENS_FORM, "window": 1.5})),
    ("fenêtre absente", _add_form({"tokens": TOKENS_FORM["tokens"]})),
    ("mots-clés absents", _add_form({"window": 4})),
    ("forme à champ inconnu", _add_form({**TOKENS_FORM, "stem": True})),
    # Ancre (§ 3.1) : un item à un seul fait n'en porte pas.
    ("ancre sur un item à un seul fait", lambda i: _fact(i).update(anchor=["délai"])),
    # Fausse valeur (§ 5.4).
    ("fausse valeur sans forme", lambda i: i.update(false_value={"accepted": []})),
    ("fausse valeur à mots-clés", lambda i: i.update(false_value={"accepted": [TOKENS_FORM]})),
    ("fausse valeur à champ inconnu", lambda i: i.update(false_value={**FALSE_VALUE, "x": 1})),
]


@pytest.mark.parametrize(("case", "change"), MALFORMED, ids=[case for case, _ in MALFORMED])
def test_rejects_a_malformed_answerable_item(golden_validator, case, change):
    assert list(golden_validator.iter_errors(_mutated(SPEC_ITEM, change))), case


MALFORMED_ANCHORS = [
    ("ancre sur un seul des faits", lambda i: _fact(i, 1).pop("anchor")),
    ("ancre vide", lambda i: _fact(i).update(anchor=[])),
    ("ancre en double", lambda i: _fact(i).update(anchor=["contenus", "contenus"])),
    ("ancre en forme à mots-clés", lambda i: _fact(i).update(anchor=[TOKENS_FORM])),
    ("ancre faite d'espaces", lambda i: _fact(i).update(anchor=["  "])),
]


@pytest.mark.parametrize(
    ("case", "change"), MALFORMED_ANCHORS, ids=[case for case, _ in MALFORMED_ANCHORS]
)
def test_rejects_a_malformed_anchored_item(golden_validator, case, change):
    assert list(golden_validator.iter_errors(_mutated(ANCHORED_ITEM, change))), case


@pytest.mark.parametrize(
    ("case", "change"),
    [
        ("fait attendu", lambda i: i["expected"].update(facts=[{"accepted": ["x"]}])),
        (
            "article attendu",
            lambda i: i["expected"].update(articles=[{"id": "LEGIARTI1", "num": "L1"}]),
        ),
        ("fausse valeur", lambda i: i.update(false_value=FALSE_VALUE)),
    ],
)
def test_rejects_an_unanswerable_item_that_expects_something(golden_validator, case, change):
    assert list(golden_validator.iter_errors(_mutated(UNANSWERABLE_ITEM, change))), case


# --- Bloc 2 : schéma des exécutions (§ 3.2) -----------------------------------------------------


def _with(**fields):
    return {**SPEC_EXECUTION, **fields}


@pytest.mark.parametrize(
    "execution",
    [
        SPEC_EXECUTION,
        _with(variant="closed_book", context=None),
        _with(variant="agentic_rag", tool_calls=0, context=[]),
        _with(variant="agentic_rag", tool_calls=3),
        _with(extra={"threshold_abstention": False}),
        _with(usage={"input_tokens": None, "output_tokens": None}, error="timeout", latency_s=None),
    ],
    ids=[
        "exemple",
        "sans récupération",
        "agentique sans recherche",
        "agentique",
        "diagnostic dans extra",
        "délai dépassé",
    ],
)
def test_accepts_the_executions_of_the_spec(execution_validator, execution):
    assert list(execution_validator.iter_errors(execution)) == []


def test_accepts_every_v1_execution_completed_with_nulls(execution_validator, v1_vectors):
    """SPEC.md § 9 : une exécution v1, complétée des champs nouveaux à `null`, est valide."""
    for vector in v1_vectors:
        if vector["kind"] == "execution":
            execution = {**vector["execution"], **NEW_FIELDS_V2}
            assert list(execution_validator.iter_errors(execution)) == [], vector["id"]


@pytest.mark.parametrize("field", sorted(SPEC_EXECUTION))
def test_rejects_an_execution_without_a_required_field(execution_validator, field):
    """§ 3.2 : un champ qui ne s'applique pas vaut `null`, il n'est jamais omis."""
    execution = {key: value for key, value in SPEC_EXECUTION.items() if key != field}

    assert list(execution_validator.iter_errors(execution)), field


MALFORMED_EXECUTIONS = [
    ("champ inconnu", _with(threshold_abstention=False)),
    ("latence au format des runs 002", _with(latency={"generation_s": 1.42})),
    ("agentique sans contexte", _with(tool_calls=2, context=None)),
    ("identifiant d'item mal formé", _with(item_id="rq1")),
    ("variante mal formée", _with(variant="Naive-RAG")),
    ("modèle vide", _with(model="")),
    ("répétition négative", _with(repeat=-1)),
    ("répétition non entière", _with(repeat=0.5)),
    ("réponse non textuelle", _with(answer=None)),
    ("abstention non booléenne", _with(abstained="false")),
    ("citation non textuelle", _with(cited=[221])),
    ("contexte non liste", _with(context="LEGIARTI000032226842")),
    ("article vide dans le contexte", _with(context=[""])),
    ("usage incomplet", _with(usage={"input_tokens": 1})),
    ("usage avec champ inconnu", _with(usage={"input_tokens": 1, "output_tokens": 1, "total": 2})),
    ("tokens négatifs", _with(usage={"input_tokens": -1, "output_tokens": 1})),
    ("tokens non entiers", _with(usage={"input_tokens": 1, "output_tokens": 1.5})),
    ("latence négative", _with(latency_s=-0.1)),
    ("coût négatif", _with(cost_usd=-0.01)),
    ("appels négatifs", _with(tool_calls=-1)),
    ("appels non entiers", _with(tool_calls=1.5)),
    ("erreur vide", _with(error="")),
    ("extra non objet", _with(extra=["x"])),
]


@pytest.mark.parametrize(
    ("case", "execution"),
    MALFORMED_EXECUTIONS,
    ids=[case for case, _ in MALFORMED_EXECUTIONS],
)
def test_rejects_a_malformed_execution(execution_validator, case, execution):
    assert list(execution_validator.iter_errors(execution)), case
