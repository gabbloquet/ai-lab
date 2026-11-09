"""Une campagne de la série RAG : chaque item × chaque variante × k répétitions, puis le résumé.

Chaque exécution est ajoutée à `executions.jsonl` dès qu'elle est finie : une campagne
interrompue reprend sans refaire ni repayer ce qui est déjà enregistré. Une erreur passagère du
fournisseur (limite de débit, panne) relance l'exécution au lieu de la compter comme fausse.

La ligne de commande, les chemins et les garde-fous du run final sont propres à chaque
expérience (par exemple `exp002_rag.campaign`).
"""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from statistics import mean, median
from typing import Any

from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models import Model

from ailab_evals.rag_qa import KS, PairedScore, aggregate, score_execution
from ailab_rag.answering import CLOSED_BOOK, NAIVE_RAG, Retriever, run_item
from ailab_rag.tracing import NO_TRACING, Tracer

TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
FAILURES = ("correct", "retrieval_miss", "generation_miss", "error")


def is_transient(error: BaseException) -> bool:
    return isinstance(error, ModelHTTPError) and error.status_code in TRANSIENT_STATUSES


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _key(execution: dict) -> tuple[str, str, int]:
    return execution["item_id"], execution["variant"], execution["repeat"]


# --- Campagne -----------------------------------------------------------------------------------


async def run_campaign(
    items: list[dict],
    *,
    variants: list[str],
    model: str | Model,
    repeats: int,
    out: Path,
    retrieve: Retriever | None = None,
    retrievers: Mapping[str, Retriever] | None = None,
    concurrency: int = 4,
    max_attempts: int = 5,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    tracer: Tracer = NO_TRACING,
) -> list[dict]:
    done = {_key(e): e for e in read_jsonl(out)}
    plan = [(item, v, r) for item in items for v in variants for r in range(repeats)]
    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    out.parent.mkdir(parents=True, exist_ok=True)

    async def one(item: dict, variant: str, repeat: int) -> dict:
        async with semaphore:
            with tracer.execution(item=item, variant=variant, repeat=repeat) as observe:
                for attempt in range(1, max_attempts + 1):
                    try:
                        execution = await run_item(
                            item,
                            variant=variant,
                            model=model,
                            repeat=repeat,
                            retrieve=(retrievers or {}).get(variant, retrieve),
                            reraise=is_transient,
                        )
                        break
                    except ModelHTTPError as error:
                        if not is_transient(error) or attempt == max_attempts:
                            raise
                        await sleep(min(2.0**attempt, 60.0))
                observe(execution, score_execution(item, execution).as_dict())
        async with lock:
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(execution, ensure_ascii=False) + "\n")
        return execution

    todo = [(i, v, r) for i, v, r in plan if (i["id"], v, r) not in done]
    for execution in await asyncio.gather(*(one(i, v, r) for i, v, r in todo)):
        done[_key(execution)] = execution
    return [done[(i["id"], v, r)] for i, v, r in plan]


# --- Résumé -------------------------------------------------------------------------------------


def _mean(values: list[Any]) -> float | None:
    present = [float(v) for v in values if v is not None]
    return mean(present) if present else None


def durations(values: list[float]) -> dict[str, float] | None:
    """Moyenne, médiane et 90e centile (rang le plus proche) ; `None` sans mesure."""
    if not values:
        return None
    ordered = sorted(values)
    return {
        "mean": mean(ordered),
        "median": median(ordered),
        "p90": ordered[math.ceil(0.9 * len(ordered)) - 1],
    }


def _variant_summary(rows: list[tuple[dict, dict, dict]]) -> dict[str, Any]:
    """Agrégats d'une variante (spec § 7). `rows` : (item, exécution, score)."""
    scores = [s for _, _, s in rows]
    failures = [s["failure"] for s in scores if s["failure"] is not None]
    by_mode: dict[str, list[bool]] = {}
    for item, _, s in rows:
        by_mode.setdefault(item["mode"], []).append(s["correct"])
    summary: dict[str, Any] = {
        "n_executions": len(rows),
        "correct": _mean([s["correct"] for s in scores]),
        "correct_answerable": _mean([s["correct"] for i, _, s in rows if i["answerable"]]),
        "false_abstention": _mean([s["false_abstention"] for s in scores]),
        "hallucination": _mean([s["hallucination"] for s in scores]),
        "error_rate": _mean([e["error"] is not None for _, e, _ in rows]),
        "failure": ({f: failures.count(f) / len(failures) for f in FAILURES} if failures else None),
        "by_mode": {mode: _mean(values) for mode, values in sorted(by_mode.items())},
        "citation_precision": _mean([s["citation_precision"] for s in scores]),
        "citation_recall": _mean([s["citation_recall"] for s in scores]),
        "context_size": _mean([s["context_size"] for s in scores]),
        "tokens": _mean([sum(e["usage"].values()) for _, e, _ in rows]),
        "generation_s": durations(
            [e["latency"]["generation_s"] for _, e, _ in rows if "latency" in e]
        ),
    }
    for k in KS:
        summary[f"evidence_recall@{k}"] = _mean([s[f"evidence_recall@{k}"] for s in scores])
        summary[f"all_evidence@{k}"] = _mean([s[f"all_evidence@{k}"] for s in scores])
    return summary


def summarize(
    items: list[dict],
    executions: list[dict],
    *,
    split: str,
    baseline: str = CLOSED_BOOK,
    variant: str = NAIVE_RAG,
) -> dict[str, Any]:
    by_id = {i["id"]: i for i in items if i["split"] == split}
    rows: dict[str, list[tuple[dict, dict, dict]]] = {}
    for e in executions:
        if e["item_id"] in by_id:
            item = by_id[e["item_id"]]
            rows.setdefault(e["variant"], []).append((item, e, score_execution(item, e).as_dict()))

    comparison = None
    if baseline in rows and variant in rows:

        def p(name: str, item_id: str) -> float:
            return mean(float(s["correct"]) for i, _, s in rows[name] if i["id"] == item_id)

        # La règle de la spec (§ 8) ne garde que les items `test` ; sur le dev, on applique la
        # même règle aux items dev, et le résumé le signale par son champ `split`.
        paired = [
            PairedScore(item_id, "test", p(baseline, item_id), p(variant, item_id))
            for item_id in by_id
        ]
        if len(paired) >= 2:
            comparison = aggregate(paired).as_dict()

    return {
        "split": split,
        "n_items": len(by_id),
        "baseline": baseline,
        "variant": variant,
        "variants": {name: _variant_summary(r) for name, r in rows.items()},
        "comparison": comparison,
    }


# --- Ligne de commande --------------------------------------------------------------------------
