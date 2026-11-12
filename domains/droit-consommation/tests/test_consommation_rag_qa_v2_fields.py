"""Champs de la spec rag-qa v2 dans le golden set v5 : ancres, fausses valeurs, règles du générateur
(README du golden set, « v5 »)."""

import copy

import pytest
from consommation_rag_qa_build import (
    Selected,
    add_v2_fields,
    anchor_requests,
    same_but_v2_fields,
    v2_rule_violations,
)

COMPARISON = {
    "id": None,
    "split": "dev",
    "mode": "comparison",
    "answerable": True,
    "question": "Amende pour une société : numéros masqués, et contenus numériques non fournis ?",
    "expected": {
        "facts": [{"accepted": ["375 000 €", "375 000 euros"]}, {"accepted": ["15 000 €"]}],
        "articles": [{"id": "LEGIARTI1", "num": "L242-14"}, {"id": "LEGIARTI2", "num": "L242-18"}],
    },
    "evidence": [
        {"article": "LEGIARTI1", "quote": "375 000 € pour une personne morale"},
        {"article": "LEGIARTI2", "quote": "15 000 euros pour une personne morale"},
    ],
}
PREMISE = {
    "id": None,
    "split": "test",
    "mode": "false_premise",
    "answerable": True,
    "question": "Achat en ligne : j'ai bien 30 jours pour me rétracter ?",
    "expected": {
        "facts": [{"accepted": ["quatorze jours", "14 jours"]}],
        "articles": [{"id": "LEGIARTI3", "num": "L221-18"}],
    },
    "evidence": [{"article": "LEGIARTI3", "quote": "délai de quatorze jours"}],
}
ANCHORS = [["numéros masqués"], ["contenus numériques"]]


def selected(item, name):
    return Selected({"task": name, "mode": item["mode"], "split": item["split"]}, item, [], None)


def anchored(anchors=ANCHORS):
    item = copy.deepcopy(COMPARISON)
    for fact, forms in zip(item["expected"]["facts"], anchors, strict=True):
        fact["anchor"] = forms
    return item


# --- Règles du générateur (spec v2, § 3.1) ------------------------------------------------------


def test_accepts_well_formed_v2_items():
    premise = {**PREMISE, "false_value": {"accepted": ["30 jours", "trente jours"]}}

    assert v2_rule_violations(anchored()) == []
    assert v2_rule_violations(premise) == []


@pytest.mark.parametrize(
    ("anchors", "expected"),
    [
        ([["numéros masqués"], ["contenus et services"]], "« et »"),
        ([["numéros masqués."], ["contenus numériques"]], "ponctuation"),
        ([["numéros masqués"], ["masqués"]], "retrouvée dans une ancre"),
        ([["numéros masqués"], ["livres audio"]], "absente de la question"),
        ([["numéros masqués"], ["  "]], "vide"),
    ],
)
def test_rejects_badly_formed_anchors(anchors, expected):
    violations = v2_rule_violations(anchored(anchors))

    assert any(expected in v for v in violations), violations


def test_rejects_an_anchored_fact_whose_form_contains_et():
    item = anchored()
    item["expected"]["facts"][0]["accepted"].append("375 000 € et plus")

    assert any("« et »" in v for v in v2_rule_violations(item))


@pytest.mark.parametrize(
    ("false_value", "expected"),
    [
        (["14 jours"], "retrouvée dans une forme du fait"),
        (["4 jours"], "absente de la question"),
        (["  "], "vide"),
    ],
)
def test_rejects_badly_formed_false_values(false_value, expected):
    item = {**PREMISE, "false_value": {"accepted": false_value}}

    assert any(expected in v for v in v2_rule_violations(item))


def test_rejects_a_true_form_found_inside_the_false_value():
    item = {**PREMISE, "false_value": {"accepted": ["30 jours", "14 jours ouvrés"]}}

    assert any("retrouvée dans une forme du fait" in v for v in v2_rule_violations(item))


def test_accepts_a_false_value_variant_absent_from_the_question():
    """Une seule forme doit figurer dans la question : « trente jours » est une variante."""
    item = {**PREMISE, "false_value": {"accepted": ["30 jours", "trente jours"]}}

    assert v2_rule_violations(item) == []


@pytest.mark.parametrize(
    "form",
    [{"tokens": ["l'activité", "évaluer"], "window": 2}, {"tokens": ["", "x"], "window": 1}],
)
def test_rejects_a_keyword_that_is_not_a_single_word(form):
    item = copy.deepcopy(PREMISE)
    item["expected"]["facts"][0]["accepted"].append(form)

    assert any("un seul mot" in v for v in v2_rule_violations(item))


# --- Ajout des champs ----------------------------------------------------------------------------


def test_takes_the_false_value_from_the_frozen_draft():
    drafts = {"fp-1": {"output": {"false_value": "30 jours"}}}

    result = add_v2_fields([selected(PREMISE, "fp-1")], drafts, anchors={}, review={})

    assert result.items["fp-1"]["false_value"] == {"accepted": ["30 jours"]}
    assert result.pending == ["fp-1"]  # pas encore relu


def test_takes_the_anchors_from_their_draft_and_keeps_other_modes_unchanged():
    other = {**PREMISE, "mode": "direct"}
    anchors = {"cmp-1": {"output": {"anchors": ANCHORS}}}
    review = {"cmp-1": {"task": "cmp-1", "verdict": "ok"}}

    result = add_v2_fields(
        [selected(COMPARISON, "cmp-1"), selected(other, "d-1")], {}, anchors=anchors, review=review
    )

    assert result.items["cmp-1"] == anchored()
    assert result.items["d-1"] == other
    assert result.pending == []
    assert result.violations == {}


def test_a_review_correction_replaces_anchors_and_false_value():
    drafts = {"fp-1": {"output": {"false_value": "30 jours"}}}
    review = {
        "fp-1": {
            "task": "fp-1",
            "verdict": "corrige",
            "correction": {"false_value": ["30 jours", "trente jours"]},
        },
        "cmp-1": {"task": "cmp-1", "verdict": "corrige", "correction": {"anchors": ANCHORS}},
    }

    result = add_v2_fields(
        [selected(PREMISE, "fp-1"), selected(COMPARISON, "cmp-1")],
        drafts,
        anchors={},
        review=review,
    )

    assert result.items["fp-1"]["false_value"]["accepted"] == ["30 jours", "trente jours"]
    assert result.items["cmp-1"] == anchored()
    assert result.pending == []


def test_a_comparison_without_anchors_waits_and_is_reported():
    result = add_v2_fields([selected(COMPARISON, "cmp-1")], {}, anchors={}, review={})

    assert result.pending == ["cmp-1"]
    assert result.violations == {"cmp-1": ["ancres manquantes"]}
    assert "anchor" not in result.items["cmp-1"]["expected"]["facts"][0]


def test_reports_rule_violations_per_task():
    anchors = {"cmp-1": {"output": {"anchors": [["numéros masqués"], ["masqués"]]}}}

    result = add_v2_fields([selected(COMPARISON, "cmp-1")], {}, anchors=anchors, review={})

    assert any("retrouvée dans une ancre" in v for v in result.violations["cmp-1"])


def test_lists_the_anchor_requests_of_comparison_items():
    requests = anchor_requests([selected(COMPARISON, "cmp-1"), selected(PREMISE, "fp-1")])

    assert requests == [
        {
            "task": "cmp-1",
            "question": COMPARISON["question"],
            "facts": [["375 000 €", "375 000 euros"], ["15 000 €"]],
            "articles": ["L242-14", "L242-18"],
        }
    ]


# --- Publication ---------------------------------------------------------------------------------


def test_a_base_item_may_only_gain_v2_fields():
    premise = {**PREMISE, "false_value": {"accepted": ["30 jours"]}}

    assert same_but_v2_fields(anchored(), COMPARISON)
    assert same_but_v2_fields(premise, PREMISE)
    assert not same_but_v2_fields({**premise, "question": "Autre ?"}, PREMISE)


def test_a_review_correction_may_add_a_keyword_form():
    """Protocole v5 : une correction peut ajouter une forme à mots-clés (spec v2, § 5.2)."""
    from consommation_rag_qa_build import _apply_correction

    form = {"tokens": ["accord", "exprès"], "window": 2}
    correction = {"facts": [{"accepted": ["quatorze jours", form, dict(form), "14 jours"]}]}

    item = _apply_correction(copy.deepcopy(PREMISE), correction, by_num={})

    assert item["expected"]["facts"][0]["accepted"] == ["quatorze jours", form, "14 jours"]
