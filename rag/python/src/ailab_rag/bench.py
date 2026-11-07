"""Banc de mesure de la récupération, sans génération.

Chaque contexte est noté par le scorer de la spec rag-qa v1 (§ 6), pour que les chiffres d'une
pré-étude se comparent à ceux d'une expérience complète. Seuls les items avec réponse sont
mesurés : un item sans réponse n'a pas d'article attendu.
"""

from __future__ import annotations

from collections.abc import Callable
from statistics import mean
from typing import Any

from ailab_evals.rag_qa import KS, score_execution
from ailab_rag.corpus import Passage

METRICS = (*(f"evidence_recall@{k}" for k in KS), *(f"all_evidence@{k}" for k in KS))


def _context_scores(item: dict, ranking: list[Passage]) -> dict[str, float]:
    execution = {
        "item_id": item["id"],
        "variant": "retrieval_bench",
        "model": "none",
        "repeat": 0,
        "answer": "",
        "abstained": False,
        "cited": [],
        "context": [p.article_id for p in ranking],
        "usage": {},
        "error": None,
    }
    score = score_execution(item, execution).as_dict()
    return {name: float(score[name]) for name in METRICS}


def _averages(rows: list[dict[str, float]]) -> dict[str, Any]:
    return {"n": len(rows), **{name: mean(r[name] for r in rows) for name in METRICS}}


def retrieval_report(items: list[dict], retrieve: Callable[[str], list[Passage]]) -> dict[str, Any]:
    """`retrieve` renvoie les passages classés du plus proche au moins proche ; il en faut au
    moins 10 pour mesurer le top-10."""
    per_item = {
        item["id"]: _context_scores(item, retrieve(item["question"]))
        for item in items
        if item["answerable"]
    }
    by_mode: dict[str, list[dict[str, float]]] = {}
    for item in items:
        if item["id"] in per_item:
            by_mode.setdefault(item["mode"], []).append(per_item[item["id"]])
    overall = _averages(list(per_item.values()))
    return {
        "n": overall["n"],
        "overall": {k: v for k, v in overall.items() if k != "n"},
        "by_mode": {mode: _averages(rows) for mode, rows in sorted(by_mode.items())},
        "items": per_item,
    }
