"""Comparaison appariée de deux variantes, commune aux specs du lab.

C'est la règle de verdict de tool-selection v1 (§ 7) et de rag-qa v1 (§ 8) : différence appariée
B − A sur les seuls items `test`, intervalle de Student à 95 %, verdict selon le signe des bornes.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from scipy import stats


@dataclass(frozen=True)
class PairedScore:
    """pᵢ(A) et pᵢ(B) d'un item : moyenne de la métrique principale sur ses k répétitions."""

    item_id: str
    split: str
    p_a: float
    p_b: float


@dataclass(frozen=True)
class Aggregate:
    n: int
    delta: float
    ci_low: float
    ci_high: float
    verdict: str

    def as_dict(self) -> dict:
        return asdict(self)


def aggregate(scores: list[PairedScore]) -> Aggregate:
    """Différence appariée B − A sur les items `test` seulement, IC de Student à 95 %."""
    differences = [s.p_b - s.p_a for s in scores if s.split == "test"]
    n = len(differences)
    if n < 2:
        raise ValueError("Il faut au moins deux items test pour un intervalle de confiance.")
    delta = sum(differences) / n
    deviation = math.sqrt(sum((d - delta) ** 2 for d in differences) / (n - 1))
    half_width = float(stats.t.ppf(0.975, n - 1)) * deviation / math.sqrt(n)
    low, high = delta - half_width, delta + half_width
    verdict = "b_better" if low > 0 else "b_worse" if high < 0 else "inconclusive"
    return Aggregate(n=n, delta=delta, ci_low=low, ci_high=high, verdict=verdict)
