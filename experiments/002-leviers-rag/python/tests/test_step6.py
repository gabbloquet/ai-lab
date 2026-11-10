"""Étape 6 de la 002 : s'abstenir quand le meilleur score de reclassement est sous un seuil."""

import json
from pathlib import Path

import pytest

from exp002_leviers.step6 import (
    BASELINE,
    THRESHOLD,
    VARIANT,
    apply_threshold,
    frozen_baseline,
    judge,
    main,
)

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


def execution(item_id: str, repeat: int = 0, *, variant: str = BASELINE) -> dict:
    """Le RAG à 20 passages répond toujours « 14 jours » : juste avec réponse, inventé sinon."""
    return {
        "item_id": item_id,
        "variant": variant,
        "model": "fake-model",
        "repeat": repeat,
        "answer": "14 jours",
        "abstained": False,
        "cited": ["L221-18"],
        "context": [GOLD],
        "usage": {"input_tokens": 4000, "output_tokens": 20},
        "error": None,
        "latency": {"generation_s": 0.8},
    }


def test_the_threshold_and_the_names_fixed_by_the_protocol() -> None:
    assert (THRESHOLD, BASELINE, VARIANT) == (0.20, "top_k_20", "abstain_low_rerank")


# --- Substitution ---------------------------------------------------------------------------------


def test_above_the_threshold_b_gives_the_answer_of_a() -> None:
    (b,) = apply_threshold([execution("rq-1")], {"rq-1": 0.6})
    assert b == {**execution("rq-1"), "variant": VARIANT, "threshold_abstention": False}


def test_below_the_threshold_b_abstains_without_calling_the_generator() -> None:
    (b,) = apply_threshold([execution("rq-1")], {"rq-1": 0.1})
    assert (b["variant"], b["answer"], b["abstained"], b["cited"]) == (VARIANT, "", True, [])
    assert b["usage"] == {"input_tokens": 0, "output_tokens": 0}
    assert b["latency"] == {"generation_s": 0.0}
    assert b["threshold_abstention"] is True
    # La recherche a eu lieu : le contexte reste celui de A.
    assert b["context"] == [GOLD]


def test_a_failed_execution_of_a_becomes_a_clean_abstention_below_the_threshold() -> None:
    failed = {**execution("rq-1"), "answer": "", "error": "ModelHTTPError: 400"}
    (b,) = apply_threshold([failed], {"rq-1": 0.1})
    assert b["error"] is None and b["abstained"] is True


def test_a_score_equal_to_the_threshold_keeps_the_answer() -> None:
    (b,) = apply_threshold([execution("rq-1")], {"rq-1": THRESHOLD})
    assert b["abstained"] is False


def test_only_the_baseline_executions_are_substituted() -> None:
    rows = [execution("rq-1"), execution("rq-1", variant="rerank_cohere")]
    assert [b["item_id"] for b in apply_threshold(rows, {"rq-1": 0.6})] == ["rq-1"]


def test_a_question_without_score_is_an_error() -> None:
    with pytest.raises(KeyError, match="rq-1"):
        apply_threshold([execution("rq-1")], {})


# --- Verdict --------------------------------------------------------------------------------------

ITEMS = [item(f"rq-{i}") for i in range(4)] + [
    item("rq-u1", answerable=False),
    item("rq-u2", answerable=False),
    item("rq-u3", answerable=False),
    item("rq-out", answerable=False),  # écarté par l'audit
    item("rq-dev", split="dev"),
]
A = [execution(i["id"], r) for i in ITEMS for r in range(3)]


def test_the_threshold_that_only_removes_inventions_makes_b_better() -> None:
    best = {i["id"]: 0.1 if not i["answerable"] else 0.7 for i in ITEMS}
    result = judge(ITEMS, A, best, split="test", exclude={"rq-out"})
    assert result["abstention"]["hallucination"]["n"] == 3
    assert result["abstention"]["hallucination"]["delta"] == -1.0
    assert result["abstention"]["false_abstention"]["delta"] == 0.0
    assert result["abstention"]["verdict"] == "b_better"
    assert result["correct"]["delta"] == pytest.approx(3 / 7)


def test_the_share_of_questions_below_the_threshold_is_reported() -> None:
    best = {"rq-0": 0.1, "rq-1": 0.7, "rq-2": 0.7, "rq-3": 0.7, "rq-u1": 0.1, "rq-u2": 0.7}
    best |= {"rq-u3": 0.7, "rq-out": 0.1, "rq-dev": 0.1}
    result = judge(ITEMS, A, best, split="test", exclude={"rq-out"})
    assert result["below_threshold"] == {"answerable": [1, 4], "unanswerable": [1, 3]}


# --- Ligne de commande ----------------------------------------------------------------------------


def _frozen_run(tmp_path: Path, *, commit: str, final: bool) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    (run / "summary.json").write_text(json.dumps({"run": {"commit": commit, "final": final}}))
    (run / "executions.jsonl").write_text(json.dumps(execution("rq-1")) + "\n")
    return run


def test_the_frozen_baseline_must_come_from_the_final_consolidated_run(tmp_path: Path) -> None:
    run = _frozen_run(tmp_path, commit="f836315bab76", final=True)
    assert [e["item_id"] for e in frozen_baseline(run, split="test")] == ["rq-1"]


def test_a_baseline_from_another_commit_is_refused(tmp_path: Path) -> None:
    run = _frozen_run(tmp_path, commit="0000000", final=True)
    with pytest.raises(SystemExit, match="gel"):
        frozen_baseline(run, split="test")


def test_a_baseline_that_is_not_the_final_run_is_refused(tmp_path: Path) -> None:
    run = _frozen_run(tmp_path, commit="f836315bab76", final=False)
    with pytest.raises(SystemExit, match="final"):
        frozen_baseline(run, split="test")


def test_the_test_split_needs_the_final_flag() -> None:
    with pytest.raises(SystemExit, match="--final"):
        main(["--split", "test"], git_is_clean=lambda: True)


def test_a_final_computation_needs_a_clean_git_tree() -> None:
    with pytest.raises(SystemExit, match="gel"):
        main(["--split", "test", "--final"], git_is_clean=lambda: False)
