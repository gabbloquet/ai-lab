"""Contrôle de reproduction du run consolidé, avant le gel et avant tout appel payant.

Sur les items des runs finaux des étapes (v1, et v3 pour l'étape 5), chaque configuration doit
redonner exactement le contexte récupéré alors : les mêmes articles, dans le même ordre. Le
contrôle ne lit que les caches (embeddings, reformulations, notes de reclassement) : un cache
manquant lève `CacheMiss`, il ne déclenche jamais d'appel.

    uv run python -m exp002_leviers.reproduction
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from pydantic_ai.models.function import FunctionModel

from ailab_rag.answering import Retriever
from ailab_rag.campaign import read_jsonl
from ailab_rag.rewriting import QueryRewriter
from exp002_leviers.paths import ARTICLES, CACHE_DIR, GOLDEN, ROOT

# Les étapes 1 à 5 de l'expérience (dossiers 002 à 006) ; leurs `runs/` sont ignorés par git.
STEP_DIRS = (
    "002-rag-naif-vs-modele-seul",
    "003-reformulation-de-requete",
    "004-top-k-20",
    "005-reclassement",
    "006-consigne-abstention",
)

Key = tuple[str, str]  # (configuration, item)


class CacheMiss(RuntimeError):
    """Une valeur absente du cache : le contrôle de reproduction n'appelle aucun modèle."""


class CacheOnlyEmbedder:
    """À placer sous `CachedEmbedder` : il n'est appelé que pour un texte absent du cache."""

    def __init__(self, model: str) -> None:
        self.model = model

    def embed(self, texts: list[str]) -> np.ndarray:
        raise CacheMiss(f"embedding absent du cache pour {len(texts)} texte(s)")


class CacheOnlyReranker:
    """À placer sous `RerankingRetriever` : il n'est appelé que pour un lot absent du cache."""

    def __init__(self, name: str) -> None:
        self.name = name

    def score(self, query: str, documents: list[str]) -> list[float]:
        raise CacheMiss(f"notes de reclassement absentes du cache : {query[:60]}")


def cache_only_rewriter(model: str, instructions: str, cache_dir: Path) -> QueryRewriter:
    """Le reformulateur gelé, avec un modèle qui porte le même nom (donc la même clé de cache)
    mais lève `CacheMiss` au lieu d'appeler le fournisseur."""

    def refuse(*_: Any) -> Any:
        raise CacheMiss("reformulation absente du cache")

    return QueryRewriter(FunctionModel(refuse, model_name=model), instructions, cache_dir)


def final_runs(root: Path = ROOT) -> list[Path]:
    return sorted(
        path
        for step in STEP_DIRS
        for path in (root / "experiments" / step / "runs").glob("final-test-*/executions.jsonl")
    )


def reference_contexts(
    runs: Iterable[Path],
) -> tuple[dict[Key, list[str] | None], dict[Key, dict[tuple[str, ...] | None, int]]]:
    """Le contexte de référence de chaque (configuration, item) : celui de la majorité des
    exécutions des runs finaux. Les clés où les exécutions ne s'accordent pas sont rendues à
    part, avec le décompte de chaque contexte ; une égalité n'a pas de référence."""
    seen: dict[Key, Counter[tuple[str, ...] | None]] = {}
    for run in runs:
        for e in read_jsonl(run):
            context = None if e["context"] is None else tuple(e["context"])
            seen.setdefault((e["variant"], e["item_id"]), Counter())[context] += 1
    references: dict[Key, list[str] | None] = {}
    divergent: dict[Key, dict[tuple[str, ...] | None, int]] = {}
    for key, counts in seen.items():
        (first, n_first), *rest = counts.most_common()
        if rest and rest[0][1] == n_first:
            raise ValueError(f"{key} : aucun contexte majoritaire, {dict(counts)}")
        references[key] = None if first is None else list(first)
        if rest:
            divergent[key] = dict(counts)
    return references, divergent


@dataclass(frozen=True)
class Mismatch:
    variant: str
    item_id: str
    expected: list[str] | None
    got: list[str] | None
    error: str | None = None


@dataclass
class Report:
    checked: Counter[str] = field(default_factory=Counter)
    mismatches: list[Mismatch] = field(default_factory=list)


def check(
    items: Mapping[str, dict],
    retrievers: Mapping[str, Retriever],
    references: Mapping[Key, list[str] | None],
) -> Report:
    """Recalcule chaque contexte de référence comme `ailab_rag.answering.run_item` : les
    articles des passages trouvés, sans doublon, dans l'ordre. Une configuration sans fonction de
    recherche (`closed_book`) n'a pas de contexte."""
    report = Report()
    for (variant, item_id), expected in sorted(references.items()):
        if item_id not in items:
            raise KeyError(f"{item_id} absent du golden set")
        report.checked[variant] += 1
        got: list[str] | None = None
        error: str | None = None
        retrieve = retrievers.get(variant)
        if retrieve is not None:
            try:
                passages = retrieve(items[item_id]["question"])
                got = list(dict.fromkeys(p.article_id for p in passages))
            except CacheMiss as miss:
                error = str(miss)
        if got != expected or error is not None:
            report.mismatches.append(Mismatch(variant, item_id, expected, got, error))
    return report


def main(argv: list[str] | None = None) -> None:
    from ailab_rag.corpus import passages
    from ailab_rag.embeddings import MODEL, CachedEmbedder
    from ailab_rag.retrieval import build_index
    from exp002_leviers.configurations import build_retrievers
    from exp003_rag.campaign import REWRITE_PROMPT, REWRITER
    from exp005_rag.campaign import RERANKER

    parser = argparse.ArgumentParser(description="Contrôle de reproduction du run consolidé")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    args = parser.parse_args(argv)

    items = {i["id"]: i for i in read_jsonl(args.golden)}
    embedder = CachedEmbedder(CacheOnlyEmbedder(MODEL), CACHE_DIR / "embeddings")
    index = build_index(passages(read_jsonl(ARTICLES)), embedder)
    retrievers = build_retrievers(
        index,
        embedder,
        cache_only_rewriter(REWRITER, REWRITE_PROMPT, CACHE_DIR / "rewrites"),
        CacheOnlyReranker(f"cohere:{RERANKER}"),
        CACHE_DIR / "rerank",
    )
    runs = final_runs()
    references, divergent = reference_contexts(runs)
    report = check(items, retrievers, references)

    print(f"{len(runs)} runs finaux lus, {sum(report.checked.values())} contextes vérifiés")
    for variant, n in sorted(report.checked.items()):
        bad = sum(m.variant == variant for m in report.mismatches)
        print(f"  {variant:<15} {n - bad:>4} / {n} identiques")
    for key, counts in sorted(divergent.items()):
        shown = {json.dumps(list(c) if c else c): n for c, n in counts.items()}
        print(f"  référence non unanime {key} : {shown}")
    for m in report.mismatches:
        print(
            f"  ÉCART {m.variant} {m.item_id} : attendu {m.expected}, obtenu {m.got}",
            m.error or "",
        )
    if report.mismatches:
        sys.exit(1)


if __name__ == "__main__":
    main()
