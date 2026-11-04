import json
from pathlib import Path

from deepeval.test_case import LLMTestCase

from ailab_evals.rag_qa_metric import RagQaMetric

VECTORS = Path(__file__).resolve().parents[2] / "spec" / "rag-qa" / "v1" / "conformance.jsonl"


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
    metric = RagQaMetric()

    assert metric.measure(_test_case(vector)) == 1.0
    assert metric.is_successful()
    assert metric.score_breakdown == vector["expected"]


def test_scores_zero_when_a_fact_is_missing_and_keeps_the_diagnosis() -> None:
    vector = _vector("cv-003")
    metric = RagQaMetric()

    assert metric.measure(_test_case(vector)) == 0.0
    assert not metric.is_successful()
    assert metric.score_breakdown["failure"] == "generation_miss"


def test_reports_an_execution_error_in_the_reason() -> None:
    metric = RagQaMetric()

    metric.measure(_test_case(_vector("cv-011")))

    assert not metric.is_successful()
    assert "invalid_output" in metric.reason
