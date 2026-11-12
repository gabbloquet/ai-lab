"""Les générateurs de l'étape 7 de la 002 : un modèle Mistral qui envoie l'effort de réflexion
demandé, là où Pydantic AI 2.65 ramène tout effort activé à `high`."""

from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.providers.mistral import MistralProvider

from ailab_rag.generators import MistralEffortModel


def test_sends_the_requested_reasoning_effort() -> None:
    model = MistralEffortModel(
        "mistral-large-4-0", effort="low", provider=MistralProvider(api_key="x")
    )

    assert model._translate_thinking(ModelRequestParameters()) == "low"
    assert model.model_name == "mistral-large-4-0"
