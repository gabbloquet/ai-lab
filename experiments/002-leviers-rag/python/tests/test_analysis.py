"""L'analyse du run consolidé : six comparaisons par modèle, IC apparié, correction de Holm, et
les critères de l'étape 5 pour la consigne d'abstention."""

import pytest
from scipy import stats

from ailab_evals.paired import PairedScore
from exp002_leviers.analysis import analyze, holm, paired_test
from exp002_leviers.configurations import COMPARISONS, CONFIGURATIONS

# --- Holm ----------------------------------------------------------------------------------------


def test_holm_multiplies_the_ordered_p_values_and_keeps_them_monotone() -> None:
    # Triées : 0,005 × 4 = 0,02 ; 0,01 × 3 = 0,03 ; 0,03 × 2 = 0,06 ; 0,04 × 1 = 0,04 → 0,06.
    assert holm([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.03, 0.06, 0.06, 0.02])


def test_holm_caps_the_adjusted_p_values_at_one() -> None:
    assert holm([0.5, 0.9]) == [1.0, 1.0]


# --- Test apparié --------------------------------------------------------------------------------


def _scores(differences: list[float]) -> list[PairedScore]:
    return [PairedScore(f"rq-{i}", "test", 0.5, 0.5 + d) for i, d in enumerate(differences)]


def test_the_p_value_is_the_one_of_the_paired_student_test() -> None:
    differences = [0.0, 1.0, 1.0, -1 / 3, 2 / 3, 0.0, 1.0]
    result = paired_test(_scores(differences))
    assert result["p_value"] == pytest.approx(stats.ttest_1samp(differences, 0.0).pvalue)


def test_the_interval_is_the_one_of_the_spec() -> None:
    result = paired_test(_scores([0.0, 1.0, 1.0, -1 / 3, 2 / 3]))
    assert result["delta"] == pytest.approx(7 / 15)
    assert result["ci_low"] < result["delta"] < result["ci_high"]
    assert result["verdict"] in {"b_better", "b_worse", "inconclusive"}


def test_no_difference_at_all_has_a_p_value_of_one() -> None:
    assert paired_test(_scores([0.0, 0.0, 0.0]))["p_value"] == 1.0


def test_the_same_difference_on_every_item_has_a_p_value_of_zero() -> None:
    assert paired_test(_scores([1.0, 1.0, 1.0]))["p_value"] == 0.0


# --- Analyse d'un run ----------------------------------------------------------------------------

GOLD = "LEGIARTI000032226842"


def item(item_id: str, *, answerable: bool = True, split: str = "test") -> dict:
    return {
        "id": item_id,
        "split": split,
        "mode": "direct" if answerable else "unanswerable",
        "answerable": answerable,
        "question": f"Question {item_id} ?",
        "expected": {
            "facts": [{"accepted": ["14 jours"]}] if answerable else [],
            "articles": [{"id": GOLD, "num": "L221-18"}] if answerable else [],
        },
        "evidence": [{"article": GOLD, "quote": "quatorze jours"}] if answerable else [],
    }


def execution(item_id: str, variant: str, repeat: int, *, right: bool) -> dict:
    """Juste : la bonne réponse, ou l'abstention sur une question sans réponse."""
    return {
        "item_id": item_id,
        "variant": variant,
        "model": "fake-model",
        "repeat": repeat,
        "answer": "14 jours" if right else "30 jours",
        "abstained": False,
        "cited": ["L221-18"],
        "context": None if variant == "closed_book" else [GOLD],
        "usage": {"input_tokens": 10, "output_tokens": 2},
        "error": None,
    }


def abstaining(item_id: str, variant: str, repeat: int) -> dict:
    return {**execution(item_id, variant, repeat, right=False), "answer": "", "abstained": True}


ITEMS = [item(f"rq-{i}") for i in range(6)] + [
    item("rq-u1", answerable=False),
    item("rq-u2", answerable=False),
    item("rq-out"),  # écarté par l'audit
    item("rq-dev", split="dev"),
]


def _run(right_for) -> list[dict]:
    rows = []
    for i in ITEMS:
        for v in CONFIGURATIONS:
            for r in range(3):
                if not i["answerable"]:
                    if v == "abstain_strict":
                        rows.append(abstaining(i["id"], v, r))
                    else:
                        rows.append(execution(i["id"], v, r, right=False))
                else:
                    rows.append(execution(i["id"], v, r, right=right_for(i["id"], v, r)))
    return rows


def _rag_beats_closed_book(item_id: str, variant: str, repeat: int) -> bool:
    return variant != "closed_book"


def test_one_result_per_comparison_of_the_protocol() -> None:
    result = analyze(ITEMS, _run(_rag_beats_closed_book), split="test", exclude={"rq-out"})
    assert [(c["baseline"], c["variant"]) for c in result["comparisons"]] == [
        (c.baseline, c.variant) for c in COMPARISONS
    ]


def test_the_excluded_and_dev_items_do_not_count() -> None:
    result = analyze(ITEMS, _run(_rag_beats_closed_book), split="test", exclude={"rq-out"})
    assert result["n_items"] == 8
    assert result["excluded"] == ["rq-out"]
    assert {c["n"] for c in result["comparisons"]} == {8}


def test_the_holm_p_values_are_computed_over_the_six_comparisons() -> None:
    result = analyze(ITEMS, _run(_rag_beats_closed_book), split="test", exclude={"rq-out"})
    raw = [c["p_value"] for c in result["comparisons"]]
    assert [c["p_holm"] for c in result["comparisons"]] == pytest.approx(holm(raw))


def test_a_large_gain_survives_holm_and_no_change_stays_inconclusive() -> None:
    result = analyze(ITEMS, _run(_rag_beats_closed_book), split="test", exclude={"rq-out"})
    by_pair = {(c["baseline"], c["variant"]): c for c in result["comparisons"]}
    rag = by_pair[("closed_book", "naive_rag")]
    assert rag["delta"] == pytest.approx(6 / 8)
    assert rag["verdict_holm"] == "b_better"
    assert by_pair[("naive_rag", "top_k_20")]["verdict_holm"] == "inconclusive"


def test_a_loss_after_holm_is_b_worse() -> None:
    def rewrite_hurts(item_id: str, variant: str, repeat: int) -> bool:
        return variant != "query_rewrite"

    result = analyze(ITEMS, _run(rewrite_hurts), split="test", exclude={"rq-out"})
    rewrite = next(c for c in result["comparisons"] if c["variant"] == "query_rewrite")
    assert rewrite["verdict_holm"] == "b_worse"


def test_the_abstention_configuration_is_also_judged_on_the_criteria_of_step_5() -> None:
    result = analyze(ITEMS, _run(_rag_beats_closed_book), split="test", exclude={"rq-out"})
    abstention = result["abstention"]
    assert abstention["hallucination"]["n"] == 2
    assert abstention["hallucination"]["delta"] == -1.0
    assert abstention["false_abstention"]["n"] == 6
    assert abstention["guard_margin"] == 0.03


def test_every_configuration_has_its_secondary_measures() -> None:
    result = analyze(ITEMS, _run(_rag_beats_closed_book), split="test", exclude={"rq-out"})
    assert set(result["configurations"]) == set(CONFIGURATIONS)
    assert result["configurations"]["naive_rag"]["by_mode"]["direct"] == 1.0
