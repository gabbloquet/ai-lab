"""Résumé d'une campagne : succès par variante et différences appariées (spec § 7)."""

import statistics
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

BASELINE = "rest"
VARIANT = "intent"


@dataclass(frozen=True)
class Summary:
    per_item: dict[str, tuple[float, float]]
    """pᵢ(A), pᵢ(B) : moyenne de success sur les répétitions, pour les items joués en A et en B."""
    success: dict[str, float]
    """Moyenne de success par variante, sur toutes ses exécutions."""
    delta: float | None
    """Moyenne des dᵢ = pᵢ(B) − pᵢ(A)."""
    s_d: float | None
    """Écart-type empirique des dᵢ : il fixe l'effet minimal détectable (README, MDE)."""


def summarize(scored: Iterable[dict[str, Any]]) -> Summary:
    by_item: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    by_variant: dict[str, list[bool]] = defaultdict(list)
    for execution in scored:
        by_item[execution["item_id"]][execution["variant"]].append(execution["success"])
        by_variant[execution["variant"]].append(execution["success"])

    per_item = {
        item_id: (_mean(variants[BASELINE]), _mean(variants[VARIANT]))
        for item_id, variants in sorted(by_item.items())
        if BASELINE in variants and VARIANT in variants
    }
    differences = [p_b - p_a for p_a, p_b in per_item.values()]
    return Summary(
        per_item=per_item,
        success={variant: _mean(values) for variant, values in by_variant.items()},
        delta=statistics.fmean(differences) if differences else None,
        s_d=statistics.stdev(differences) if len(differences) >= 2 else None,
    )


def _mean(values: list[bool]) -> float:
    return sum(values) / len(values)
