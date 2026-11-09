"""La campagne de la 006 : le RAG à 20 passages, avec la phrase d'ancrage du gel de la 002 (A) ou
une phrase d'ancrage plus exigeante (B)."""

import json
from pathlib import Path

import numpy as np
import pytest

from ailab_rag.corpus import Passage
from ailab_rag.prompting import GROUNDING
from ailab_rag.retrieval import Index
from exp006_rag.campaign import (
    BASELINE,
    GROUNDINGS,
    STRICT_GROUNDING,
    VARIANT,
    build_retrievers,
    excluded_items,
    main,
)

PASSAGES = [Passage(f"LEGIARTI{i:012d}", f"L{i}", f"texte {i}", 0) for i in range(25)]
INDEX = Index(PASSAGES, np.array([[25.0 - i, 1.0] for i in range(25)], dtype=np.float32))


class FixedEmbedder:
    model = "fake"

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)


def test_the_two_variants_are_the_twenty_passage_rag_and_its_strict_version() -> None:
    assert (BASELINE, VARIANT) == ("top_k_20", "abstain_strict")


def test_both_variants_send_the_same_twenty_passages() -> None:
    retrievers = build_retrievers(INDEX, FixedEmbedder())

    assert retrievers[BASELINE]("q") == retrievers[VARIANT]("q") == PASSAGES[:20]


def test_only_the_variant_changes_its_grounding() -> None:
    """A garde la phrase d'ancrage du gel de la 002 ; B la prolonge par sa consigne."""
    assert BASELINE not in GROUNDINGS
    assert GROUNDINGS[VARIANT] == STRICT_GROUNDING
    assert STRICT_GROUNDING.startswith(GROUNDING)
    assert "situation exacte de la question" in STRICT_GROUNDING


def test_excluded_items_are_those_the_audit_found_answered(tmp_path: Path) -> None:
    audit = tmp_path / "audit.jsonl"
    rows = [
        {"id": "rq-006", "verdict": "a_une_reponse"},
        {"id": "rq-012", "verdict": "sans_reponse"},
        {"id": "rq-129", "verdict": "a_une_reponse"},
    ]
    audit.write_text("".join(json.dumps(r) + "\n" for r in rows), "utf-8")

    assert excluded_items(audit) == {"rq-006", "rq-129"}


def test_the_test_split_needs_the_final_flag() -> None:
    with pytest.raises(SystemExit, match="--final"):
        main(
            ["--split", "test", "--model", "mistral:mistral-small-2603"], git_is_clean=lambda: True
        )


def test_a_final_run_needs_a_clean_git_tree() -> None:
    with pytest.raises(SystemExit, match="gel"):
        main(
            ["--split", "test", "--final", "--model", "mistral:mistral-small-2603"],
            git_is_clean=lambda: False,
        )
