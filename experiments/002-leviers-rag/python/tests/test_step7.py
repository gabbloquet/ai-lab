"""Étape 7 de la 002 : le registre des générateurs, vérifié à la source le 2026-11-12."""

from exp002_leviers.step7 import BASELINE, CANDIDATES, generators


def test_one_baseline_and_four_candidates_one_per_axis() -> None:
    assert BASELINE == "mistral-small-2603"
    assert set(CANDIDATES) == {
        "mistral-large-4-0",
        "gemini-4-carbon",
        "gemma-4-31b-it",
        "mistral-small-2603-reasoning",
    }


def test_gemini_models_do_not_receive_temperature_and_think_at_the_lowest_level() -> None:
    settings = {name: g.settings for name, g in generators(api_keys=False).items()}

    assert "temperature" not in settings["gemini-4-carbon"]
    assert settings["gemini-4-carbon"]["google_thinking_config"] == {"thinking_level": "low"}
    assert settings["mistral-small-2603"] == {"temperature": 0.0}


def test_mistral_models_send_their_reasoning_effort() -> None:
    from pydantic_ai.models import ModelRequestParameters

    built = generators(api_keys=False)

    assert built["mistral-large-4-0"].model._translate_thinking(ModelRequestParameters()) == "low"
    small = built["mistral-small-2603-reasoning"].model
    assert small._translate_thinking(ModelRequestParameters()) == "high"
    assert small.model_name == "mistral-small-2603"
