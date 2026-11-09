"""Le verdict à deux critères de la 006 : baisser les réponses inventées sans faire augmenter les
abstentions à tort au-delà d'une marge."""

import pytest

from ailab_evals.paired import Aggregate, joint_verdict

MARGIN = 0.03


def delta(low: float, high: float) -> Aggregate:
    return Aggregate(n=50, delta=(low + high) / 2, ci_low=low, ci_high=high, verdict="")


@pytest.mark.parametrize(
    ("main", "guard", "expected"),
    [
        # Moins de réponses inventées, abstentions à tort sous la marge.
        (delta(-0.20, -0.05), delta(-0.01, 0.02), "b_better"),
        # Plus de réponses inventées.
        (delta(0.02, 0.15), delta(-0.01, 0.01), "b_worse"),
        # Abstentions à tort nettement au-delà de la marge, même avec moins d'invention.
        (delta(-0.20, -0.05), delta(0.04, 0.10), "b_worse"),
        # Moins d'invention, mais la garde n'est pas tenue sans être franchement dépassée.
        (delta(-0.20, -0.05), delta(0.00, 0.06), "tradeoff"),
        # Baisse non établie.
        (delta(-0.15, 0.05), delta(-0.01, 0.02), "inconclusive"),
    ],
)
def test_joint_verdict(main: Aggregate, guard: Aggregate, expected: str) -> None:
    assert joint_verdict(main, guard, guard_margin=MARGIN) == expected


def test_a_guard_bound_exactly_at_the_margin_does_not_hold() -> None:
    """La borne haute de la garde doit être strictement sous la marge."""
    assert joint_verdict(delta(-0.2, -0.1), delta(0.0, MARGIN), guard_margin=MARGIN) == "tradeoff"
