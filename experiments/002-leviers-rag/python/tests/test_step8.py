"""Étape 8 de la 002 : le lanceur du RAG agentique (analyse, coût, statistiques d'outils)."""

import pytest

from exp002_leviers.step8 import BASELINE_VARIANT, GUIDANCES, analyze_step8, main, tool_stats

GOLD = "LEGIARTI000032226842"


def item(item_id: str, *, answerable: bool = True) -> dict:
    return {
        "id": item_id,
        "split": "dev",
        "mode": "direct" if answerable else "unanswerable",
        "answerable": answerable,
        "question": f"Question {item_id} ?",
        "expected": {
            "facts": [{"accepted": ["14 jours"]}] if answerable else [],
            "articles": [{"id": GOLD, "num": "L221-18"}] if answerable else [],
        },
        "evidence": [{"article": GOLD, "quote": "quatorze jours"}] if answerable else [],
    }


def execution(item_id, variant, repeat, *, right, tool_calls=None, gets=0) -> dict:
    return {
        "item_id": item_id,
        "variant": variant,
        "model": "mistral-large-4-0",
        "repeat": repeat,
        "answer": "14 jours" if right else "30 jours",
        "abstained": False,
        "cited": [],
        "context": [GOLD],
        "usage": {"input_tokens": 10_000, "output_tokens": 300},
        "latency_s": 5.0,
        "cost_usd": None,
        "tool_calls": tool_calls,
        "error": None,
        **({"extra": {"search_calls": tool_calls - gets, "get_calls": gets}} if tool_calls else {}),
    }


def test_the_first_cycle_uses_the_guidance_written_before_any_dev_run() -> None:
    from ailab_rag.agentic import AGENTIC_GUIDANCE

    assert GUIDANCES[1] == AGENTIC_GUIDANCE
    assert BASELINE_VARIANT == "mistral_large_4"


def test_the_analysis_compares_the_agentic_variant_to_top_k_20_with_large_4() -> None:
    items = [item(f"rq-{i:03d}") for i in range(30)]
    rows = [
        execution(i["id"], v, r, right=(v == "agentic_rag" or i["id"] < "rq-020"), tool_calls=t)
        for i in items
        for v, t in ((BASELINE_VARIANT, None), ("agentic_rag", 3))
        for r in range(3)
    ]

    result = analyze_step8(items, rows, split="dev", excluded=[])

    assert result["correct"]["verdict"] == "b_better" and result["correct"]["n"] == 30
    assert result["baseline"]["n_executions"] == 90
    assert result["agentic"]["tool_calls_mean"] == 3.0
    assert result["agentic"]["cost_usd_mean"] == pytest.approx((10_000 * 0.70 + 300 * 2.10) / 1e6)


def test_tool_stats_count_calls_the_cap_and_the_share_of_article_reads() -> None:
    rows = [
        execution("rq-001", "agentic_rag", 0, right=True, tool_calls=6, gets=2),
        execution("rq-002", "agentic_rag", 0, right=True, tool_calls=2, gets=0),
    ]

    stats = tool_stats(rows)

    assert stats == {
        "executions": 2,
        "mean": 4.0,
        "median": 4.0,
        "distribution": {"2": 1, "6": 1},
        "at_cap_share": 0.5,
        "get_article_share": 0.25,
    }


def test_the_launcher_refuses_a_test_run_and_an_unknown_cycle() -> None:
    with pytest.raises(SystemExit, match="run consolidé 2"):
        main(["--split", "test"])
    with pytest.raises(SystemExit, match="cycle"):
        main(["--split", "dev", "--cycle", "3"])
