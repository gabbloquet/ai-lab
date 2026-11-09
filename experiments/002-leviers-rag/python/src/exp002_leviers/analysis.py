"""L'analyse du run consolidé, pour un modèle (README, « Mesures »).

- Six comparaisons de `correct`, chacune selon la règle de la spec rag-qa v1 (§ 8) : moyenne par
  item sur les k répétitions, différence appariée, IC de Student à 95 %.
- La p-value bilatérale du test t apparié, celui dont l'IC est l'inversion, puis la correction de
  Holm sur les six p-values du modèle. Le verdict corrigé (`verdict_holm`) exige
  p_holm < 0,05 ; le verdict de la spec (`verdict`, IC non corrigé) est publié à côté.
- Pour `abstain_strict`, les deux critères de l'étape 5, repris de `ailab_rag.campaign`.
- Les agrégats de la spec (§ 7) pour chaque configuration, comme mesures secondaires.
"""

from __future__ import annotations

import math
from collections.abc import Collection
from statistics import mean
from typing import Any

from scipy import stats

from ailab_evals.paired import PairedScore, aggregate
from ailab_evals.rag_qa import score_execution
from ailab_rag.campaign import abstention_comparison, summarize
from exp002_leviers.configurations import ABSTAIN_STRICT, COMPARISONS, TOP_K_20
from exp006_rag.campaign import GUARD_MARGIN

ALPHA = 0.05


def holm(p_values: list[float]) -> list[float]:
    """p-values ajustées de Holm-Bonferroni, dans l'ordre reçu."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = running
    return adjusted


def paired_test(scores: list[PairedScore]) -> dict[str, Any]:
    """L'agrégat de la spec, plus la p-value bilatérale du test t apparié (H0 : delta nul). Sans
    aucune dispersion, la p-value vaut 1 si le delta est nul, 0 sinon."""
    result = aggregate(scores).as_dict()
    differences = [s.p_b - s.p_a for s in scores if s.split == "test"]
    n = len(differences)
    deviation = math.sqrt(sum((d - result["delta"]) ** 2 for d in differences) / (n - 1))
    if deviation == 0.0:
        result["p_value"] = 1.0 if result["delta"] == 0.0 else 0.0
    else:
        t = result["delta"] / (deviation / math.sqrt(n))
        result["p_value"] = float(2 * stats.t.sf(abs(t), n - 1))
    return result


def _correct_by_item(
    items: dict[str, dict], executions: list[dict]
) -> dict[tuple[str, str], list[float]]:
    values: dict[tuple[str, str], list[float]] = {}
    for e in executions:
        item = items.get(e["item_id"])
        if item is not None:
            correct = score_execution(item, e).as_dict()["correct"]
            values.setdefault((e["variant"], e["item_id"]), []).append(float(correct))
    return values


def analyze(
    items: list[dict],
    executions: list[dict],
    *,
    split: str,
    exclude: Collection[str] = frozenset(),
) -> dict[str, Any]:
    """`items` : tout le golden set ; seuls les items du `split` qui ne sont pas dans `exclude`
    comptent. Sur le `dev`, la même règle s'applique aux items `dev`, signalés par `split`."""
    kept = {i["id"]: i for i in items if i["split"] == split and i["id"] not in exclude}
    correct = _correct_by_item(kept, executions)

    comparisons = []
    for c in COMPARISONS:
        scores = [
            PairedScore(
                item_id,
                "test",
                mean(correct[(c.baseline, item_id)]),
                mean(correct[(c.variant, item_id)]),
            )
            for item_id in kept
        ]
        comparisons.append(
            {
                "baseline": c.baseline,
                "variant": c.variant,
                "step": c.step,
                "reading": c.reading,
                "smallest_effect": c.smallest_effect,
                "p_a": mean(s.p_a for s in scores),
                "p_b": mean(s.p_b for s in scores),
                **paired_test(scores),
            }
        )
    for c, p_holm in zip(comparisons, holm([c["p_value"] for c in comparisons]), strict=True):
        c["p_holm"] = p_holm
        significant = p_holm < ALPHA
        c["verdict_holm"] = (
            ("b_better" if c["delta"] > 0 else "b_worse") if significant else "inconclusive"
        )

    secondary = summarize(items, executions, split=split, exclude=exclude)
    return {
        "split": split,
        "n_items": len(kept),
        "excluded": secondary["excluded"],
        "alpha": ALPHA,
        "comparisons": comparisons,
        "abstention": abstention_comparison(
            items,
            executions,
            baseline=TOP_K_20,
            variant=ABSTAIN_STRICT,
            guard_margin=GUARD_MARGIN,
            split=split,
            exclude=exclude,
        ),
        "configurations": secondary["variants"],
    }
