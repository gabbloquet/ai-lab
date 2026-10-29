import json
from pathlib import Path

from ailab_evals.tool_selection_metric import ToolSelectionMetric
from deepeval.test_case import LLMTestCase, ToolCall

VECTORS = (
    Path(__file__).resolve().parents[2] / "spec" / "tool-selection" / "v1" / "conformance.jsonl"
)


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
        actual_output="",
        tools_called=[
            ToolCall(name=call["tool"], input_parameters=call["args"])
            for call in execution["calls"]
        ],
        metadata={
            "expected": vector["item"]["expected"][execution["variant"]],
            "error": execution["error"],
        },
    )


def test_scores_one_when_every_required_call_is_made() -> None:
    vector = _vector("cv-003")
    metric = ToolSelectionMetric()

    assert metric.measure(_test_case(vector)) == 1.0
    assert metric.is_successful()
    assert metric.score_breakdown == vector["expected"]


def test_scores_zero_when_a_required_call_is_missing() -> None:
    vector = _vector("cv-012")
    metric = ToolSelectionMetric()

    assert metric.measure(_test_case(vector)) == 0.0
    assert not metric.is_successful()
    assert metric.score_breakdown == vector["expected"]


def test_fails_an_execution_that_ended_in_error() -> None:
    metric = ToolSelectionMetric()

    metric.measure(_test_case(_vector("cv-015")))

    assert not metric.is_successful()
    assert "max_steps_reached" in metric.reason


def test_reads_a_call_without_arguments_as_an_empty_object() -> None:
    test_case = LLMTestCase(
        input="Quels magasins ?",
        actual_output="",
        tools_called=[ToolCall(name="list_stores")],
        metadata={"expected": {"required": [{"tool": "list_stores", "args": {}}], "tolerated": []}},
    )

    assert ToolSelectionMetric().measure(test_case) == 1.0
