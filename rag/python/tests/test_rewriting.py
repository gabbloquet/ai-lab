"""Réécriture de requête : un modèle reformule la question avant la recherche."""

from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from ailab_rag.corpus import Passage
from ailab_rag.rewriting import HYDE, REFORMULATE, QueryRewriter, RewritingRetriever

QUESTION = "J'ai acheté un aspirateur en ligne, combien de temps pour changer d'avis ?"


class Writer:
    """Un faux modèle qui renvoie un texte fixé et compte ses appels."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0
        self.instructions: list[str | None] = []

    def model(self) -> FunctionModel:
        def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            self.calls += 1
            self.instructions.append(info.instructions)
            return ModelResponse(parts=[TextPart(self.text)])

        return FunctionModel(respond, model_name="fake-model")


def test_the_two_prompts_ask_for_legal_vocabulary_without_answering() -> None:
    assert "vocabulaire juridique" in REFORMULATE and "sans y répondre" in REFORMULATE
    assert "extrait d'article" in HYDE


def test_the_rewriter_returns_the_model_text(tmp_path: Path) -> None:
    writer = Writer("Délai du droit de rétractation pour un contrat conclu à distance")
    rewriter = QueryRewriter(writer.model(), REFORMULATE, tmp_path)

    assert rewriter.rewrite(QUESTION) == (
        "Délai du droit de rétractation pour un contrat conclu à distance"
    )
    assert writer.instructions == [REFORMULATE]


def test_a_cached_rewrite_does_not_call_the_model_again(tmp_path: Path) -> None:
    writer = Writer("Délai du droit de rétractation")
    QueryRewriter(writer.model(), REFORMULATE, tmp_path).rewrite(QUESTION)

    QueryRewriter(writer.model(), REFORMULATE, tmp_path).rewrite(QUESTION)

    assert writer.calls == 1


def test_the_cache_keeps_prompts_apart(tmp_path: Path) -> None:
    writer = Writer("texte")
    QueryRewriter(writer.model(), REFORMULATE, tmp_path).rewrite(QUESTION)

    QueryRewriter(writer.model(), HYDE, tmp_path).rewrite(QUESTION)

    assert writer.calls == 2


def test_an_empty_rewrite_falls_back_to_the_question(tmp_path: Path) -> None:
    assert QueryRewriter(Writer("   ").model(), REFORMULATE, tmp_path).rewrite(QUESTION) == QUESTION


def test_the_retriever_searches_with_the_rewrite(tmp_path: Path) -> None:
    rewriter = QueryRewriter(Writer("droit de rétractation").model(), REFORMULATE, tmp_path)
    seen: list[tuple[str, int]] = []
    found = [Passage("LEGIARTI000032226842", "L221-18", "quatorze jours", 0)]

    def inner(query: str, k: int) -> list[Passage]:
        seen.append((query, k))
        return found

    assert RewritingRetriever(rewriter, inner).retrieve(QUESTION, 5) == found
    assert seen == [("droit de rétractation", 5)]


def test_rewrite_all_fills_the_cache_before_a_campaign(tmp_path: Path) -> None:
    writer = Writer("réécrit")
    rewriter = QueryRewriter(writer.model(), REFORMULATE, tmp_path)

    rewriter.rewrite_all(["q1", "q2", "q1"], workers=2)
    rewriter.rewrite("q2")

    assert writer.calls == 2
