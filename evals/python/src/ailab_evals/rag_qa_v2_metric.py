"""Métrique DeepEval personnalisée pour la spec rag-qa v2.

Une enveloppe fine autour du cœur de notation (rag_qa_v2.py), comme `RagQaMetric` pour la v1. On
n'utilise pas les métriques RAG de DeepEval : elles reposent sur un juge LLM, alors que la spec note
sans juge.

Le LLMTestCase porte la réponse dans `actual_output`, et dans `metadata` :
- `item` : la ligne du golden set ;
- `execution` : l'exécution observée, sous la forme canonique du § 3.2 de la spec.
"""

from __future__ import annotations

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from ailab_evals.rag_qa_v2 import score_execution


class RagQaV2Metric(BaseMetric):
    """Score 1.0 si `correct` (§ 5.5), 0.0 sinon ; toutes les métriques dans `score_breakdown`."""

    def __init__(self) -> None:
        self.threshold = 1.0
        self.async_mode = False
        self.include_reason = True

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        metadata = test_case.metadata or {}
        execution = metadata["execution"]
        self.score_breakdown = score_execution(metadata["item"], execution)
        correct = self.score_breakdown["correct"]
        self.score = 1.0 if correct else 0.0
        self.success = correct
        self.reason = _reason(self.score_breakdown, execution["error"])
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return bool(self.success)

    @property
    def __name__(self) -> str:
        return "RAG QA (spec rag-qa v2)"


def _reason(metrics: dict, error: str | None) -> str:
    detail = ", ".join(f"{name}={value}" for name, value in metrics.items() if value is not None)
    return f"Erreur d'exécution : {error}. {detail}" if error else detail
