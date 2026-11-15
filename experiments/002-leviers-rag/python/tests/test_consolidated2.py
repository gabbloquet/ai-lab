"""Run consolidé 2 de la 002 : les garde-fous du lanceur et l'assemblage des verdicts."""

import pytest

from exp002_leviers.consolidated2 import BLOCK_A_MODELS, assemble, main

GOLD = "LEGIARTI000032226842"


def item(item_id: str, *, answerable: bool = True) -> dict:
    return {
        "id": item_id,
        "split": "test",
        "mode": "direct" if answerable else "unanswerable",
        "answerable": answerable,
        "question": f"Question {item_id} ?",
        "expected": {
            "facts": [{"accepted": ["14 jours"]}] if answerable else [],
            "articles": [{"id": GOLD, "num": "L221-18"}] if answerable else [],
        },
        "evidence": [{"article": GOLD, "quote": "quatorze jours"}] if answerable else [],
    }


def execution(item_id, variant, repeat, *, right, tool_calls=None) -> dict:
    return {
        "item_id": item_id,
        "variant": variant,
        "model": "m",
        "repeat": repeat,
        "answer": "14 jours" if right else "30 jours",
        "abstained": False,
        "cited": [],
        "context": [GOLD],
        "usage": {"input_tokens": 4000, "output_tokens": 100},
        "latency_s": 1.0,
        "cost_usd": None,
        "tool_calls": tool_calls,
        "error": None,
    }


def test_the_series_generators_run_block_a() -> None:
    assert BLOCK_A_MODELS == (
        "mistral:mistral-small-2603",
        "mistral:ministral-14b-2512",
        "google:gemini-3.5-flash-lite",
    )


@pytest.mark.parametrize("argv", [["--block", "A"], ["--block", "report"]])
def test_nothing_runs_without_the_final_flag(argv) -> None:
    with pytest.raises(SystemExit, match="--final"):
        main(argv)


def test_a_dirty_tree_is_refused() -> None:
    with pytest.raises(SystemExit, match="commit de gel"):
        main(["--final", "--block", "B"], git_is_clean=lambda: False)


def test_the_report_judges_steps_7_and_8_on_the_test_split() -> None:
    items = [item(f"rq-{i:03d}") for i in range(30)]
    variants = {
        "top_k_20": lambda i: i["id"] < "rq-020",
        "mistral_large_4": lambda i: True,
        "gemini_4_carbon": lambda i: i["id"] < "rq-020",
        "gemma_4_31b": lambda i: i["id"] < "rq-020",
        "mistral_small_reasoning": lambda i: i["id"] < "rq-020",
    }
    step7 = [
        execution(i["id"], v, r, right=f(i))
        for i in items
        for v, f in variants.items()
        for r in range(3)
    ]
    agentic = {
        "mistral-large-4-0": [
            execution(i["id"], "agentic_rag", r, right=True, tool_calls=2)
            for i in items
            for r in range(3)
        ],
        "gemini-4-carbon": [
            execution(i["id"], "agentic_rag", r, right=True, tool_calls=3)
            for i in items
            for r in range(3)
        ],
    }

    result = assemble(items, step7, agentic, block_a={}, excluded=[], day="2026-11-15")

    assert (
        result["step7"]["candidates"]["mistral-large-4-0"]["correct"]["verdict_holm"] == "b_better"
    )
    assert result["step8"]["correct"]["n"] == 30 and result["step8"]["correct"]["delta"] == 0.0
    assert result["step8_carbon_secondary"]["correct"]["verdict"] == "b_better"
    assert result["step7"]["split"] == "test"
