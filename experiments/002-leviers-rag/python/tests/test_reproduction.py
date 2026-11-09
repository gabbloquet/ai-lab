"""Le contrôle de reproduction : avant tout appel payant, chaque configuration doit redonner les
contextes récupérés aux runs finaux de son étape, sans appeler aucun modèle."""

import json
import os
from pathlib import Path

import numpy as np
import pytest

from ailab_rag.corpus import Passage
from ailab_rag.embeddings import CachedEmbedder
from ailab_rag.reranking import RerankingRetriever
from ailab_rag.retrieval import Index
from ailab_rag.rewriting import QueryRewriter
from exp002_leviers.reproduction import (
    CacheMiss,
    CacheOnlyEmbedder,
    CacheOnlyReranker,
    cache_only_rewriter,
    check,
    reference_contexts,
)

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

PASSAGES = [Passage(f"A{i}", f"L{i}", f"texte {i}", 0) for i in range(6)]
INDEX = Index(PASSAGES, np.array([[6.0 - i, 0.0] for i in range(6)], dtype=np.float32))
ITEMS = {"rq-1": {"id": "rq-1", "question": "q1"}, "rq-2": {"id": "rq-2", "question": "q2"}}


def _write_run(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def _row(item: str, variant: str, context: list[str] | None, repeat: int = 0) -> dict:
    return {"item_id": item, "variant": variant, "repeat": repeat, "context": context}


# --- Contextes de référence ---------------------------------------------------------------------


def test_the_reference_is_the_context_of_the_final_runs(tmp_path) -> None:
    run = _write_run(tmp_path / "a.jsonl", [_row("rq-1", "naive_rag", ["A0", "A1"])])
    references, divergent = reference_contexts([run])
    assert references == {("naive_rag", "rq-1"): ["A0", "A1"]}
    assert divergent == {}


def test_a_minority_context_is_kept_aside_and_reported(tmp_path) -> None:
    # Étape 1, rq-001 : une seule exécution sur neuf a vu deux articles dans l'autre ordre.
    runs = [
        _write_run(
            tmp_path / "a.jsonl", [_row("rq-1", "naive_rag", ["A0", "A1"], r) for r in (0, 1)]
        ),
        _write_run(tmp_path / "b.jsonl", [_row("rq-1", "naive_rag", ["A1", "A0"])]),
    ]
    references, divergent = reference_contexts(runs)
    assert references == {("naive_rag", "rq-1"): ["A0", "A1"]}
    assert divergent == {("naive_rag", "rq-1"): {("A0", "A1"): 2, ("A1", "A0"): 1}}


def test_a_tie_between_two_contexts_has_no_reference(tmp_path) -> None:
    runs = [
        _write_run(tmp_path / "a.jsonl", [_row("rq-1", "naive_rag", ["A0", "A1"])]),
        _write_run(tmp_path / "b.jsonl", [_row("rq-1", "naive_rag", ["A1", "A0"])]),
    ]
    with pytest.raises(ValueError, match="rq-1"):
        reference_contexts(runs)


# --- Contrôle ------------------------------------------------------------------------------------


def _dense(k: int):
    return lambda question: INDEX.search(np.array([1.0, 0.0]), k)


def test_an_identical_context_passes() -> None:
    references = {("naive_rag", "rq-1"): ["A0", "A1"], ("closed_book", "rq-1"): None}
    report = check(ITEMS, {"naive_rag": _dense(2)}, references)
    assert report.mismatches == []
    assert report.checked == {"naive_rag": 1, "closed_book": 1}


def test_the_order_of_the_passages_counts() -> None:
    references = {("naive_rag", "rq-1"): ["A1", "A0"]}
    report = check(ITEMS, {"naive_rag": _dense(2)}, references)
    assert [(m.variant, m.item_id, m.expected, m.got) for m in report.mismatches] == [
        ("naive_rag", "rq-1", ["A1", "A0"], ["A0", "A1"])
    ]


def test_a_passage_split_in_parts_counts_once_as_in_the_runs() -> None:
    parts = [Passage("A0", "L0", "début", 0), Passage("A0", "L0", "fin", 1)]
    report = check(ITEMS, {"naive_rag": lambda q: parts}, {("naive_rag", "rq-1"): ["A0"]})
    assert report.mismatches == []


def test_a_missing_cache_is_a_mismatch_not_a_call() -> None:
    def miss(question: str) -> list[Passage]:
        raise CacheMiss("embedding absent")

    report = check(ITEMS, {"naive_rag": miss}, {("naive_rag", "rq-1"): ["A0"]})
    assert [(m.item_id, m.got, m.error) for m in report.mismatches] == [
        ("rq-1", None, "embedding absent")
    ]


def test_a_configuration_without_retriever_must_have_had_no_context() -> None:
    report = check(ITEMS, {}, {("closed_book", "rq-1"): ["A0"]})
    assert [(m.variant, m.got) for m in report.mismatches] == [("closed_book", None)]


def test_a_reference_item_missing_from_the_golden_set_is_an_error() -> None:
    with pytest.raises(KeyError, match="rq-9"):
        check(ITEMS, {"naive_rag": _dense(2)}, {("naive_rag", "rq-9"): ["A0"]})


# --- Adaptateurs sans appel ----------------------------------------------------------------------


def test_the_cache_only_embedder_reads_the_cache_and_never_calls(tmp_path) -> None:
    class Once:
        model = "fake"

        def embed(self, texts: list[str]) -> np.ndarray:
            return np.ones((len(texts), 2), dtype=np.float32)

    CachedEmbedder(Once(), tmp_path).embed(["déjà vu"])
    offline = CachedEmbedder(CacheOnlyEmbedder("fake"), tmp_path)
    assert offline.embed(["déjà vu"]).tolist() == [[1.0, 1.0]]
    with pytest.raises(CacheMiss):
        offline.embed(["jamais vu"])


def test_the_cache_only_rewriter_reads_the_rewrites_of_the_real_one(tmp_path) -> None:
    real = QueryRewriter("test", "consigne", tmp_path)
    written = real.rewrite("question")
    offline = cache_only_rewriter("test", "consigne", tmp_path)
    assert offline.rewrite("question") == written
    with pytest.raises(CacheMiss):
        offline.rewrite("autre question")


def test_the_cache_only_reranker_reads_the_scores_of_the_real_one(tmp_path) -> None:
    class Real:
        name = "cohere:rerank"

        def score(self, query: str, documents: list[str]) -> list[float]:
            return [float(i) for i in range(len(documents))]

    class Fixed:
        model = "fake"

        def embed(self, texts: list[str]) -> np.ndarray:
            return np.array([[1.0, 0.0] for _ in texts])

    real = RerankingRetriever(INDEX, Fixed(), Real(), cache_dir=tmp_path, pool=4, k=2)
    offline = RerankingRetriever(
        INDEX, Fixed(), CacheOnlyReranker("cohere:rerank"), cache_dir=tmp_path, pool=4, k=2
    )
    written = real("q")
    assert offline("q") == written
    with pytest.raises(CacheMiss):
        offline("autre q")
