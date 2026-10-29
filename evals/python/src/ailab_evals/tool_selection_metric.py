"""Métrique DeepEval personnalisée pour la spec tool-selection v1.

Une enveloppe fine autour du cœur de notation (tool_selection.py). On n'utilise pas
`ToolCorrectnessMetric` : ses règles diffèrent de la spec (elle calcule une précision).

Le LLMTestCase porte les appels émis dans `tools_called`, et dans `metadata` :
- `expected` : l'entrée `expected[variante]` de l'item du golden set ;
- `error` : l'erreur d'exécution, ou None.
"""

from __future__ import annotations

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from ailab_evals.tool_selection import score_execution


class ToolSelectionMetric(BaseMetric):
    """Score 1.0 si `success` (§ 6), 0.0 sinon ; toutes les métriques dans `score_breakdown`."""

    def __init__(self) -> None:
        self.threshold = 1.0
        self.async_mode = False
        self.include_reason = True

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        metadata = test_case.metadata or {}
        calls = [
            {"tool": call.name, "args": call.input_parameters or {}}
            for call in test_case.tools_called or []
        ]
        error = metadata.get("error")
        result = score_execution(metadata["expected"], calls, error)
        self.score_breakdown = result.as_dict()
        self.score = 1.0 if result.success else 0.0
        self.success = result.success
        self.reason = _reason(result.as_dict(), error)
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return bool(self.success)

    @property
    def __name__(self) -> str:
        return "Tool selection (spec v1)"


def _reason(metrics: dict, error: str | None) -> str:
    detail = ", ".join(f"{name}={value}" for name, value in metrics.items())
    return f"Erreur d'exécution : {error}. {detail}" if error else detail
