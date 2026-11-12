"""Vérifie les fichiers partagés de la spec rag-qa v2 : les schémas des items et des exécutions, et
les vecteurs de conformance. Les scorers, eux, vérifient qu'ils reproduisent les résultats
attendus."""

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
            {
                "accepted": ["15 000 euros", "15 000 €"],
                "anchor": ["contenus", "services numériques"],
            },
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


def _read_vectors(directory):
    lines = (directory / "conformance.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


@pytest.fixture(scope="module")
def vectors():
    return _read_vectors(SPEC_DIR)


@pytest.fixture(scope="module")
def v1_vectors():
    return _read_vectors(V1_DIR)


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


# --- Bloc 3 : vecteurs de conformance (§ 9) ------------------------------------------------------

KS = (1, 3, 5, 10)
KINDS = {"execution", "aggregate", "variant", "comparison", "joint", "family"}
DIRECTIONS = {"higher_better", "lower_better"}
VERDICTS = {"b_better", "b_worse", "inconclusive"}
FAILURES = {"correct", "retrieval_miss", "generation_miss", "error"}
PREMISES = {"corrected", "unresolved", "adopted", "missed"}

EXECUTION_METRICS = {
    "correct",
    "facts_found",
    "facts_attached",
    "premise",
    "false_abstention",
    "hallucination",
    *(f"evidence_recall@{k}" for k in KS),
    *(f"all_evidence@{k}" for k in KS),
    "all_evidence",
    "context_size",
    "failure",
    "citation_precision",
    "citation_recall",
    "tool_calls",
    "latency_s",
    "cost_usd",
}
# § 8.1 : les métriques numériques ou booléennes du § 6, plus les trois champs recopiés.
COMPARABLE_METRICS = EXECUTION_METRICS - {"failure", "premise"}
VARIANT_KEYS = {
    "n_executions",
    "correct",
    "correct_answerable",
    "false_abstention_rate",
    "hallucination_rate",
    "error_rate",
    *(f"evidence_recall@{k}" for k in KS),
    *(f"all_evidence@{k}" for k in KS),
    "all_evidence",
    "context_size",
    "failure",
    "premise",
    "correct_by_mode",
    "tokens_mean",
    "cost_usd_mean",
    "latency_s_median",
    "latency_s_p95",
    "tool_calls_mean",
}
COMPARISON_KEYS = {"n", "delta", "ci_low", "ci_high", "verdict", "p_value"}
AGGREGATE_KEYS = {"n", "delta", "ci_low", "ci_high", "verdict"}
FAMILY_KEYS = {"name", "p_value", "p_holm", "verdict_holm"}

# Les noms du test v1, recopiés tels quels.
V1_MINIMUM_CASES = {
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
# SPEC.md § 9 : la liste de référence des cas nouveaux en v2.
MINIMUM_CASES = V1_MINIMUM_CASES | {
    "IC nul",
    "normalisation : espace avant %",
    "normalisation : espace avant €",
    "mots-clés : dans la fenêtre",
    "mots-clés : fenêtre dépassée d'un mot",
    "mots-clés : ordre inverse",
    "mots-clés : mot fléchi",
    "mots-clés : mot coupé par une apostrophe",
    "mots-clés : fenêtre nulle",
    "rattachement : deux phrases",
    "rattachement : deux propositions",
    "rattachement : phrase à une seule ancre malgré « et »",
    "rattachement : inversion entre deux phrases",
    "rattachement : inversion dans une phrase",
    "rattachement : valeur sans ancre",
    "rattachement : abréviation L. 242-14",
    "rattachement : facts_attached partiel",
    "prémisse : vraie valeur seule",
    "prémisse : et non",
    "prémisse : marqueur à 6 mots",
    "prémisse : marqueur à 7 mots",
    "prémisse : marqueur de plusieurs mots",
    "prémisse : fausse valeur seule",
    "prémisse : ni l'une ni l'autre",
    "prémisse : une occurrence non marquée sur deux",
    "prémisse : abstention qui l'emporte",
    "agentique : un appel",
    "agentique : plusieurs appels",
    "agentique : aucun appel",
    "agrégats : autre split ignoré",
    "agrégats : moyenne sans valeur",
    "agrégats : répartition de failure",
    "agrégats : répartition de premise",
    "agrégats : deux modes",
    "agrégats : centiles sur un nombre pair",
    "agrégats : centiles sur un nombre impair",
    "agrégats : champ manquant",
    "comparaison : lower_better qui s'améliore",
    "comparaison : lower_better qui se dégrade",
    "comparaison : k > 1 répétitions",
    "comparaison : répétition en erreur ignorée",
    "comparaison : répétition en erreur comptée fausse",
    "comparaison : item sans valeur écarté",
    "comparaison : baseline sans valeur",
    "comparaison : un seul item",
    "comparaison : autre split ignoré",
    "verdict joint : b_better",
    "verdict joint : b_worse par le critère principal",
    "verdict joint : b_worse par la garde",
    "verdict joint : tradeoff",
    "verdict joint : inconclusive",
    "verdict joint : garde à la marge",
    "verdict joint : garde higher_better",
    "verdict joint : n < 2",
    "holm : p-value",
    "holm : sans dispersion, delta nul",
    "holm : sans dispersion, delta non nul",
    "holm : plafond à 1",
    "holm : maximum cumulé",
    "holm : p-values égales",
    "holm : comparaison à n < 2",
    "holm : b_worse en lower_better",
    "holm : concluant avant correction seulement",
    "exclusion : agrégats",
    "exclusion : comparaison",
    "exclusion : verdict joint",
}
EXTRA_CASES = {"deux faits retrouvés", "délimitation : une occurrence délimitée suffit"}


def _of(vectors, kind):
    return [vector for vector in vectors if vector["kind"] == kind]


def _errors(validator, document):
    return list(validator.iter_errors(document))


def test_gives_each_vector_a_unique_id(vectors):
    ids = [vector["id"] for vector in vectors]

    assert len(ids) == len(set(ids))


def test_uses_every_kind_and_only_known_kinds(vectors):
    assert {vector["kind"] for vector in vectors} == KINDS


def test_covers_every_minimum_case_with_known_names(vectors):
    covered = {case for vector in vectors for case in vector["covers"]}

    assert MINIMUM_CASES - covered == set()
    assert covered - (MINIMUM_CASES | EXTRA_CASES) == set()


def test_describes_each_execution_vector(golden_validator, execution_validator, vectors):
    for vector in _of(vectors, "execution"):
        assert _errors(golden_validator, vector["item"]) == [], vector["id"]
        assert _errors(execution_validator, vector["execution"]) == [], vector["id"]
        assert vector["execution"]["item_id"] == vector["item"]["id"], vector["id"]
        assert set(vector["expected"]) == EXECUTION_METRICS, vector["id"]
        assert vector["expected"]["failure"] in FAILURES | {None}, vector["id"]
        assert vector["expected"]["premise"] in PREMISES | {None}, vector["id"]


def _check_paired_items(vector, entries):
    for entry in entries:
        assert set(entry) == {"item_id", "split", "p_a", "p_b"}, vector["id"]
        assert entry["split"] in {"dev", "test"}, vector["id"]
        assert 0 <= entry["p_a"] <= 1 and 0 <= entry["p_b"] <= 1, vector["id"]


def test_describes_each_aggregate_vector(vectors):
    aggregates = _of(vectors, "aggregate")

    assert any({entry["split"] for entry in v["items"]} == {"dev", "test"} for v in aggregates)
    for vector in aggregates:
        _check_paired_items(vector, vector["items"])
        assert set(vector["expected"]) == AGGREGATE_KEYS, vector["id"]
        assert vector["expected"]["verdict"] in VERDICTS, vector["id"]
        assert vector["expected"]["n"] == sum(e["split"] == "test" for e in vector["items"])


def _check_run(golden_validator, execution_validator, vector, variants):
    """Entrées communes de variant, comparison et joint (§ 7, § 8.1, § 8.2, § 8.4)."""
    ids = {item["id"] for item in vector["items"]}
    assert len(ids) == len(vector["items"]), vector["id"]
    for item in vector["items"]:
        assert _errors(golden_validator, item) == [], vector["id"]
    assert vector["split"] in {"dev", "test"}, vector["id"]
    assert set(vector["excluded"]) <= ids, vector["id"]
    assert vector["executions"], vector["id"]
    for execution in vector["executions"]:
        assert _errors(execution_validator, execution) == [], vector["id"]
        assert execution["item_id"] in ids, vector["id"]
    assert len({execution["model"] for execution in vector["executions"]}) == 1, vector["id"]
    assert {execution["variant"] for execution in vector["executions"]} == variants, vector["id"]


def _check_distribution(vector, value, keys):
    if value is not None:
        assert set(value) == keys, vector["id"]
        assert abs(sum(value.values()) - 1) < 1e-9, vector["id"]


def test_describes_each_variant_vector(golden_validator, execution_validator, vectors):
    for vector in _of(vectors, "variant"):
        variants = {execution["variant"] for execution in vector["executions"]}
        assert len(variants) == 1, vector["id"]
        _check_run(golden_validator, execution_validator, vector, variants)
        expected = vector["expected"]
        assert set(expected) == VARIANT_KEYS, vector["id"]
        _check_distribution(vector, expected["failure"], FAILURES)
        _check_distribution(vector, expected["premise"], PREMISES)


def test_gives_every_variant_key_a_value_somewhere(vectors):
    """§ 9 : chaque clé du § 7 est non nulle dans au moins un vecteur."""
    valued = {
        key
        for vector in _of(vectors, "variant")
        for key, value in vector["expected"].items()
        if value is not None
    }

    assert VARIANT_KEYS - valued == set()


def _check_comparison_result(vector, result):
    assert set(result) == COMPARISON_KEYS, vector["id"]
    assert result["verdict"] in VERDICTS | {None}, vector["id"]


def test_describes_each_comparison_vector(golden_validator, execution_validator, vectors):
    for vector in _of(vectors, "comparison"):
        assert vector["baseline"] != vector["variant"], vector["id"]
        _check_run(
            golden_validator, execution_validator, vector, {vector["baseline"], vector["variant"]}
        )
        assert vector["metric"] in COMPARABLE_METRICS, vector["id"]
        assert vector["direction"] in DIRECTIONS, vector["id"]
        _check_comparison_result(vector, vector["expected"])


def test_describes_each_joint_vector(golden_validator, execution_validator, vectors):
    for vector in _of(vectors, "joint"):
        assert vector["baseline"] != vector["variant"], vector["id"]
        _check_run(
            golden_validator, execution_validator, vector, {vector["baseline"], vector["variant"]}
        )
        for criterion in ("main", "guard"):
            assert set(vector[criterion]) == {"metric", "direction"}, vector["id"]
            assert vector[criterion]["metric"] in COMPARABLE_METRICS, vector["id"]
            assert vector[criterion]["direction"] in DIRECTIONS, vector["id"]
            _check_comparison_result(vector, vector["expected"][criterion])
        assert vector["margin"] >= 0, vector["id"]
        assert set(vector["expected"]) == {"main", "guard", "verdict"}, vector["id"]
        assert vector["expected"]["verdict"] in VERDICTS | {"tradeoff", None}, vector["id"]


def test_describes_each_family_vector(vectors):
    for vector in _of(vectors, "family"):
        assert 0 < vector["alpha"] < 1, vector["id"]
        names = [comparison["name"] for comparison in vector["comparisons"]]
        assert len(names) == len(set(names)), vector["id"]
        for comparison in vector["comparisons"]:
            assert set(comparison) == {"name", "direction", "items"}, vector["id"]
            assert comparison["direction"] in DIRECTIONS, vector["id"]
            _check_paired_items(vector, comparison["items"])
        assert [result["name"] for result in vector["expected"]] == names, vector["id"]
        for result in vector["expected"]:
            assert set(result) == FAMILY_KEYS, vector["id"]
            assert result["verdict_holm"] in VERDICTS | {None}, vector["id"]


# --- Bloc 4 : reprise des vecteurs v1 (§ 9) ------------------------------------------------------


def test_keeps_every_v1_vector_under_the_same_id_and_kind(vectors, v1_vectors):
    kinds = {vector["id"]: vector["kind"] for vector in vectors}

    assert {vector["id"]: vector["kind"] for vector in v1_vectors}.items() <= kinds.items()


def test_completes_each_v1_execution_vector_without_changing_it(vectors, v1_vectors):
    """Même item ; exécution complétée des champs nouveaux à `null` ; métriques v1 inchangées, sauf
    sur un vecteur qui porte `v1_change`."""
    by_id = {vector["id"]: vector for vector in vectors}
    for old in _of(v1_vectors, "execution"):
        new = by_id[old["id"]]
        assert new["item"] == old["item"], old["id"]
        assert new["execution"] == {**old["execution"], **NEW_FIELDS_V2}, old["id"]
        if "v1_change" not in new:
            changed = {k for k in old["expected"] if new["expected"][k] != old["expected"][k]}
            assert changed == set(), old["id"]


def test_keeps_each_v1_aggregate_vector_as_is(vectors, v1_vectors):
    by_id = {vector["id"]: vector for vector in vectors}
    for old in _of(v1_vectors, "aggregate"):
        new = by_id[old["id"]]
        assert (new["items"], new["expected"]) == (old["items"], old["expected"]), old["id"]


def test_explains_a_v1_change_only_on_a_v1_vector(vectors, v1_vectors):
    v1_ids = {vector["id"] for vector in v1_vectors}
    for vector in vectors:
        if "v1_change" in vector:
            assert vector["id"] in v1_ids, vector["id"]
            assert vector["v1_change"].strip(), vector["id"]
