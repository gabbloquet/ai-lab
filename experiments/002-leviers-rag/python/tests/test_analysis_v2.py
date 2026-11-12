"""L'analyse d'un run noté par la spec rag-qa v2 : mêmes comparaisons que le run consolidé, faites
par le scorer partagé (comparaison § 8.1, Holm § 8.3, verdict à deux critères § 8.2, agrégats
§ 7)."""

import pytest

from exp002_leviers.analysis import analyze
from exp002_leviers.analysis_v2 import analyze_v2
from exp002_leviers.configurations import COMPARISONS, CONFIGURATIONS

V2_FIELDS = {"latency_s": 1.0, "cost_usd": None, "tool_calls": None}
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


def execution(item_id: str, variant: str, repeat: int, *, right: bool, abstained=False) -> dict:
    """Comme dans test_analysis : la bonne réponse, ou « 30 jours », ou l'abstention."""
    return {
        "item_id": item_id,
        "variant": variant,
        "model": "fake-model",
        "repeat": repeat,
        "answer": "" if abstained else "14 jours" if right else "30 jours",
        "abstained": abstained,
        "cited": ["L221-18"],
        "context": None if variant == "closed_book" else [GOLD],
        "usage": {"input_tokens": 10, "output_tokens": 2},
        "error": None,
    }


ITEMS = [item(f"rq-{i}") for i in range(6)] + [
    item("rq-u1", answerable=False),
    item("rq-u2", answerable=False),
    item("rq-out"),  # écarté par l'audit
    item("rq-dev", split="dev"),
]


def _rag_beats_closed_book(item_id: str, variant: str, repeat: int) -> bool:
    return variant != "closed_book"


def _run(right_for) -> list[dict]:
    rows = []
    for i in ITEMS:
        for v in CONFIGURATIONS:
            for r in range(3):
                if not i["answerable"]:
                    strict = v == "abstain_strict"
                    rows.append(execution(i["id"], v, r, right=False, abstained=strict))
                else:
                    rows.append(execution(i["id"], v, r, right=right_for(i["id"], v, r)))
    return rows


def _v2(rows: list[dict]) -> list[dict]:
    return [{**row, **V2_FIELDS} for row in rows]


def test_gives_the_same_comparisons_as_the_v1_analysis_on_items_without_v2_fields() -> None:
    rows = _run(_rag_beats_closed_book)
    v1 = analyze(ITEMS, rows, split="test", exclude={"rq-out"})

    v2 = analyze_v2(ITEMS, _v2(rows), split="test", exclude={"rq-out"})

    keys = ("n", "delta", "ci_low", "ci_high", "verdict", "p_value", "p_holm", "verdict_holm")
    assert [(c["baseline"], c["variant"]) for c in v2["comparisons"]] == [
        (c.baseline, c.variant) for c in COMPARISONS
    ]
    for old, new in zip(v1["comparisons"], v2["comparisons"], strict=True):
        for key in keys:
            assert new[key] == pytest.approx(old[key]), key
    assert v2["abstention"]["verdict"] == v1["abstention"]["verdict"]
    assert v2["n_items"] == v1["n_items"] and v2["excluded"] == v1["excluded"]


def test_publishes_the_aggregates_of_the_spec_for_each_configuration() -> None:
    v2 = analyze_v2(ITEMS, _v2(_run(_rag_beats_closed_book)), split="test", exclude={"rq-out"})

    assert set(v2["configurations"]) == set(CONFIGURATIONS)
    closed = v2["configurations"]["closed_book"]
    assert closed["n_executions"] == 8 * 3
    assert closed["latency_s_median"] == 1.0
    assert closed["cost_usd_mean"] is None
    assert v2["spec"] == "evals/spec/rag-qa/v2"
