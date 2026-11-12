"""Générateurs à réglages propres (étape 7 de la 002).

Pydantic AI 2.65 traduit tout effort de réflexion activé en `reasoning_effort="high"` chez Mistral,
alors que l'API accepte aussi `low` et `medium` (Mistral Large 4, docs.mistral.ai, vérifié le
2026-11-12) et que le SDK `mistralai` 3.7.0 les connaît. `MistralEffortModel` envoie l'effort
demandé tel quel.
"""

from __future__ import annotations

from typing import Any

from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.mistral import MistralModel


class MistralEffortModel(MistralModel):
    """Un modèle Mistral qui envoie toujours `reasoning_effort=effort`."""

    def __init__(self, model_name: str, *, effort: str, **kwargs: Any) -> None:
        super().__init__(model_name, **kwargs)
        self._effort = effort

    def _translate_thinking(self, model_request_parameters: ModelRequestParameters) -> Any:
        return self._effort
