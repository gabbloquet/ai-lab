import pytest

from exp001_agent.summary import summarize


def execution(item_id: str, variant: str, repeat: int, success: bool) -> dict:
    return {"item_id": item_id, "variant": variant, "repeat": repeat, "success": success}


def test_averages_success_per_item_then_compares_the_variants_item_by_item():
    scored = [
        execution("ts-1", "rest", 0, False),
        execution("ts-1", "rest", 1, True),
        execution("ts-1", "intent", 0, True),
        execution("ts-1", "intent", 1, True),
        execution("ts-2", "rest", 0, False),
        execution("ts-2", "rest", 1, False),
        execution("ts-2", "intent", 0, True),
        execution("ts-2", "intent", 1, False),
    ]

    summary = summarize(scored)

    assert summary.per_item == {"ts-1": (0.5, 1.0), "ts-2": (0.0, 0.5)}
    assert summary.success == {"rest": 0.25, "intent": 0.75}
    assert summary.delta == pytest.approx(0.5)
    assert summary.s_d == pytest.approx(0.0)


def test_measures_the_spread_of_the_paired_differences():
    scored = [
        execution("ts-1", "rest", 0, False),
        execution("ts-1", "intent", 0, True),
        execution("ts-2", "rest", 0, True),
        execution("ts-2", "intent", 0, True),
    ]

    summary = summarize(scored)

    assert summary.delta == pytest.approx(0.5)
    assert summary.s_d == pytest.approx(0.7071, abs=1e-4)


def test_reports_one_variant_without_a_comparison():
    summary = summarize([execution("ts-1", "intent", 0, True)])

    assert summary.success == {"intent": 1.0}
    assert summary.delta is None
    assert summary.s_d is None
