"""Scorer de la spec tool-selection v1 (evals/spec/tool-selection/v1/SPEC.md).

Cœur de notation pur, sans DeepEval : il est vérifié par les vecteurs de conformance, que le
scorer Java doit aussi passer. Les numéros de section renvoient à la spec.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import asdict, dataclass

from scipy import stats

ANY = {"any": True}


def values_equal(a: object, b: object) -> bool:
    """§ 5. Les booléens se testent avant les nombres : en Python, True == 1."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, str) and isinstance(b, str):
        return _normalized(a) == _normalized(b)
    if isinstance(a, int | float) and isinstance(b, int | float):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(values_equal(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(values_equal(a[key], b[key]) for key in a)
    return False


def _normalized(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip().casefold()


def satisfies(call: dict, pattern: dict) -> bool:
    """§ 4 : même outil (sensible à la casse), arguments requis présents et acceptables,
    arguments facultatifs acceptables s'ils sont présents, aucun argument hors du motif."""
    if call["tool"] != pattern["tool"] or not isinstance(call["args"], dict):
        return False
    args = call["args"]
    required = pattern["args"]
    optional = pattern.get("optional", {})
    if any(name not in required and name not in optional for name in args):
        return False
    if any(
        name not in args or not _acceptable(args[name], spec) for name, spec in required.items()
    ):
        return False
    return all(_acceptable(args[name], spec) for name, spec in optional.items() if name in args)


def _acceptable(value: object, spec: list | dict) -> bool:
    if spec == ANY:
        return True
    return any(values_equal(value, accepted) for accepted in spec)


def maximum_matching(patterns: list[dict], calls: list[dict]) -> int:
    """§ 6.2 : cardinalité d'un couplage maximum motifs ↔ appels, par chemins augmentants
    (algorithme de Kuhn). Un couplage glouton dans l'ordre des appels peut en manquer (cv-017)."""
    owner: dict[int, int] = {}  # appel -> motif

    def augment(pattern: int, seen: set[int]) -> bool:
        for index, call in enumerate(calls):
            if index in seen or not satisfies(call, patterns[pattern]):
                continue
            seen.add(index)
            if index not in owner or augment(owner[index], seen):
                owner[index] = pattern
                return True
        return False

    return sum(augment(pattern, set()) for pattern in range(len(patterns)))


@dataclass(frozen=True)
class ExecutionScore:
    tool_recall: float
    args_recall: float
    precision: float | None
    extra_calls: int
    n_calls: int
    success: bool
    strict_success: bool

    def as_dict(self) -> dict:
        return asdict(self)


def score_execution(expectation: dict, calls: list[dict], error: str | None) -> ExecutionScore:
    """§ 6. `expectation` est l'entrée `expected[variante]` d'un item du golden set."""
    required = expectation["required"]
    untolerated = [
        call for call in calls if not any(satisfies(call, p) for p in expectation["tolerated"])
    ]
    r = len(required)
    m = maximum_matching(required, untolerated)
    n = sum(
        min(
            sum(p["tool"] == tool for p in required),
            sum(c["tool"] == tool for c in untolerated),
        )
        for tool in {p["tool"] for p in required}
    )
    extra = len(untolerated) - m
    success = m == r and error is None
    return ExecutionScore(
        tool_recall=n / r,
        args_recall=m / r,
        precision=None if m + extra == 0 else m / (m + extra),
        extra_calls=extra,
        n_calls=len(calls),
        success=success,
        strict_success=success and extra == 0,
    )


@dataclass(frozen=True)
class PairedScore:
    """pᵢ(A) et pᵢ(B) d'un item : moyenne de `success` sur ses k répétitions."""

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
    """§ 7 : différence appariée B − A sur les items `test` seulement, IC de Student à 95 %."""
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
