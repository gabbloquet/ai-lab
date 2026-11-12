"""L'analyse d'un run de la 002 noté par la spec rag-qa v2 (golden set v5).

Les mêmes mesures que `analysis` (run consolidé, spec v1), mais calculées par le scorer partagé de
la v2, vérifié par ses vecteurs de conformance en Python et en Java :
- les six comparaisons de `correct` (§ 8.1), et leur correction de Holm sur la famille des six
  (§ 8.3) ;
- pour `abstain_strict`, le verdict à deux critères de l'étape 5 (§ 8.2) : réponses inventées,
  garde sur les abstentions à tort, marge de l'étape 5 ;
- les agrégats de chaque configuration (§ 7).
"""

from __future__ import annotations

from collections.abc import Collection
from statistics import mean
from typing import Any

from ailab_evals import rag_qa_v2
from exp002_leviers.analysis import ALPHA
from exp002_leviers.configurations import ABSTAIN_STRICT, COMPARISONS, CONFIGURATIONS, TOP_K_20
from exp006_rag.campaign import GUARD_MARGIN

SPEC = "evals/spec/rag-qa/v2"


def _correct_mean(
    items: list[dict], executions: list[dict], variant: str, kept: set[str]
) -> float | None:
    by_id = {i["id"]: i for i in items}
    values = [
        float(rag_qa_v2.score_execution(by_id[e["item_id"]], e)["correct"])
        for e in executions
        if e["variant"] == variant and e["item_id"] in kept
    ]
    return mean(values) if values else None


def analyze_v2(
    items: list[dict],
    executions: list[dict],
    *,
    split: str,
    exclude: Collection[str] = frozenset(),
) -> dict[str, Any]:
    """`items` : tout le golden set ; seuls les items du `split` hors `exclude` comptent."""
    excluded = sorted(i["id"] for i in items if i["split"] == split and i["id"] in exclude)
    kept = {i["id"] for i in items if i["split"] == split and i["id"] not in exclude}
    common = {"split": split, "excluded": excluded}

    comparisons = []
    members = []
    for c in COMPARISONS:
        result = rag_qa_v2.compare(
            items,
            executions,
            baseline=c.baseline,
            variant=c.variant,
            metric="correct",
            direction="higher_better",
            **common,
        )
        comparisons.append(
            {
                "baseline": c.baseline,
                "variant": c.variant,
                "step": c.step,
                "reading": c.reading,
                "smallest_effect": c.smallest_effect,
                "p_a": _correct_mean(items, executions, c.baseline, kept),
                "p_b": _correct_mean(items, executions, c.variant, kept),
                **result,
            }
        )
        pairs = _pairs(items, executions, c.baseline, c.variant, kept)
        members.append(rag_qa_v2.FamilyMember(f"{c.variant}-{c.baseline}", "higher_better", pairs))
    for comparison, corrected in zip(
        comparisons, rag_qa_v2.holm_family(members, alpha=ALPHA), strict=True
    ):
        comparison["p_holm"] = corrected["p_holm"]
        comparison["verdict_holm"] = corrected["verdict_holm"]

    abstention = rag_qa_v2.joint_comparison(
        items,
        executions,
        baseline=TOP_K_20,
        variant=ABSTAIN_STRICT,
        main=("hallucination", "lower_better"),
        guard=("false_abstention", "lower_better"),
        margin=GUARD_MARGIN,
        **common,
    )
    abstention["guard_margin"] = GUARD_MARGIN

    configurations = {
        name: rag_qa_v2.variant_aggregates(
            items, [e for e in executions if e["variant"] == name], **common
        )
        for name in CONFIGURATIONS
        if any(e["variant"] == name for e in executions)
    }
    return {
        "spec": SPEC,
        "split": split,
        "n_items": len(kept),
        "excluded": excluded,
        "alpha": ALPHA,
        "comparisons": comparisons,
        "abstention": abstention,
        "configurations": configurations,
    }


def _pairs(
    items: list[dict], executions: list[dict], baseline: str, variant: str, kept: set[str]
) -> list[rag_qa_v2.PairedScore]:
    """Les pᵢ de `correct` des deux configurations, pour la famille de Holm (§ 8.3)."""
    by_id = {i["id"]: i for i in items}
    values: dict[tuple[str, str], list[float]] = {}
    for e in executions:
        if e["variant"] in (baseline, variant) and e["item_id"] in kept:
            score = rag_qa_v2.score_execution(by_id[e["item_id"]], e)["correct"]
            values.setdefault((e["item_id"], e["variant"]), []).append(float(score))
    return [
        rag_qa_v2.PairedScore(
            item_id, "test", mean(values[(item_id, baseline)]), mean(values[(item_id, variant)])
        )
        for item_id in sorted(kept)
        if (item_id, baseline) in values and (item_id, variant) in values
    ]
