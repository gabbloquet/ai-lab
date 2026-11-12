import json
from pathlib import Path

from deepeval.test_case import LLMTestCase

from ailab_evals.rag_qa_v2_metric import RagQaV2Metric

VECTORS = Path(__file__).resolve().parents[2] / "spec" / "rag-qa" / "v2" / "conformance.jsonl"


def _vector(vector_id: str) -> dict:
    for line in VECTORS.read_text(encoding="utf-8").splitlines():
        vector = json.loads(line)
        if vector["id"] == vector_id:
            return vector
    raise KeyError(vector_id)


def _test_case(vector: dict) -> LLMTestCase:
    execution = vector["execution"]
    return LLMTestCase(
        input=vector["item"]["question"],
        actual_output=execution["answer"],
        metadata={"item": vector["item"], "execution": execution},
    )


def test_scores_one_for_a_correct_answer() -> None:
    vector = _vector("cv-001")
    metric = RagQaV2Metric()

    assert metric.measure(_test_case(vector)) == 1.0
    assert metric.is_successful()
    assert metric.score_breakdown == vector["expected"]


def test_scores_zero_for_an_inverted_comparison_and_keeps_the_diagnosis() -> None:
    vector = next(
        v
        for v in map(json.loads, VECTORS.read_text(encoding="utf-8").splitlines())
        if "rattachement : inversion dans une phrase" in v["covers"]
    )
    metric = RagQaV2Metric()

    assert metric.measure(_test_case(vector)) == 0.0
    assert not metric.is_successful()
    assert metric.score_breakdown["facts_attached"] == 0
    assert "facts_found=2" in metric.reason


def test_names_the_spec_version() -> None:
    assert RagQaV2Metric().__name__ == "RAG QA (spec rag-qa v2)"
