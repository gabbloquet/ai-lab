"""La campagne de la 003 : deux RAG, l'un qui cherche avec la question, l'autre avec sa
reformulation ; et les garde-fous du run final."""

from pathlib import Path

import numpy as np
import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from ailab_rag.corpus import Passage
from ailab_rag.retrieval import Index
from ailab_rag.rewriting import REFORMULATE, QueryRewriter
from exp003_rag.campaign import BASELINE, VARIANT, build_retrievers, main

P1 = Passage("LEGIARTI000032226842", "L221-18", "droit de rétractation de quatorze jours", 0)
P2 = Passage("LEGIARTI000032221377", "L221-23", "coûts directs de renvoi", 0)


class FixedEmbedder:
    model = "fake"

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = {"changer d'avis ?": [0.0, 1.0], "droit de rétractation": [1.0, 0.0]}
        return np.array([vectors[t] for t in texts], dtype=np.float32)


def rewriter(tmp_path: Path) -> QueryRewriter:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("droit de rétractation")])

    return QueryRewriter(FunctionModel(respond, model_name="fake"), REFORMULATE, tmp_path)


def test_the_two_variants_are_the_naive_rag_and_the_rewriting_rag() -> None:
    assert (BASELINE, VARIANT) == ("naive_rag", "query_rewrite")


def test_the_baseline_searches_with_the_question_and_the_variant_with_its_rewrite(
    tmp_path: Path,
) -> None:
    index = Index([P1, P2], np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32))

    retrievers = build_retrievers(index, FixedEmbedder(), rewriter(tmp_path), k=1)

    assert retrievers[BASELINE]("changer d'avis ?") == [P2]
    assert retrievers[VARIANT]("changer d'avis ?") == [P1]


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
