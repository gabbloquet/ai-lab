"""Étape 7 de la 002 : le registre des générateurs, vérifié à la source le 2026-11-12."""

import pytest

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


# --- Lanceur : coût, analyse, choix pour l'étape 8 ----------------------------------------------

GOLD = "LEGIARTI000032226842"


def item(item_id: str, *, answerable: bool = True, split: str = "dev") -> dict:
    return {
        "id": item_id,
        "split": split,
        "mode": "direct" if answerable else "unanswerable",
        "answerable": answerable,
        "question": f"Question {item_id} ?",
        "expected": {
            "facts": [{"accepted": ["14 jours"]}] if answerable else [],
            "articles": [{"id": GOLD, "num": "L221-18"}] if answerable else [],
        },
        "evidence": [{"article": GOLD, "quote": "quatorze jours"}] if answerable else [],
    }


def execution(item_id: str, variant: str, repeat: int, *, right: bool, error=None) -> dict:
    return {
        "item_id": item_id,
        "variant": variant,
        "model": "m",
        "repeat": repeat,
        "answer": "14 jours" if right else "30 jours",
        "abstained": False,
        "cited": [],
        "context": [GOLD],
        "usage": {"input_tokens": 1_000_000, "output_tokens": 100_000},
        "latency_s": 1.0,
        "cost_usd": None,
        "tool_calls": None,
        "error": error,
    }


def test_the_cost_of_an_execution_follows_the_dated_price_list() -> None:
    from exp002_leviers.step7 import cost_usd

    e = execution("rq-001", "mistral_large_4", 0, right=True)

    assert cost_usd(e, "mistral-large-4-0", day="2026-11-12") == pytest.approx(0.70 + 0.21)
    assert cost_usd(e, "gemini-4-carbon", day="2026-11-30") == pytest.approx(2.0 + 1.0)
    assert cost_usd(e, "gemini-4-carbon", day="2026-12-01") == pytest.approx(4.0 + 2.0)
    assert cost_usd(e, "gemma-4-31b-it", day="2026-11-12") is None


def test_each_candidate_runs_under_its_own_variant_name() -> None:
    from exp002_leviers.step7 import VARIANTS

    assert VARIANTS == {
        "mistral-large-4-0": "mistral_large_4",
        "gemini-4-carbon": "gemini_4_carbon",
        "gemma-4-31b-it": "gemma_4_31b",
        "mistral-small-2603-reasoning": "mistral_small_reasoning",
    }


def _run(rules: dict) -> tuple[list[dict], list[dict]]:
    items = [item(f"rq-{i:03d}") for i in range(30)] + [
        item(f"rq-{i:03d}", answerable=False) for i in range(30, 34)
    ]
    rows = []
    for it in items:
        for variant, right_for in rules.items():
            for r in range(3):
                rows.append(execution(it["id"], variant, r, right=right_for(it)))
    return items, rows


def test_the_analysis_judges_each_candidate_on_two_criteria_with_their_own_holm_family() -> None:
    from exp002_leviers.step7 import analyze_step7

    items, rows = _run(
        {
            "top_k_20": lambda it: it["answerable"] and it["id"] < "rq-005",
            "mistral_large_4": lambda it: it["answerable"],
            "gemini_4_carbon": lambda it: it["answerable"] and it["id"] < "rq-005",
            "gemma_4_31b": lambda it: it["answerable"] and it["id"] < "rq-005",
            "mistral_small_reasoning": lambda it: it["answerable"] and it["id"] < "rq-005",
        }
    )

    result = analyze_step7(items, rows, split="dev", excluded=[])

    large = result["candidates"]["mistral-large-4-0"]
    assert large["correct"]["verdict_holm"] == "b_better"
    assert result["candidates"]["gemini-4-carbon"]["correct"]["verdict_holm"] == "inconclusive"
    assert set(large["hallucination"]) >= {"delta", "ci_low", "ci_high", "p_value", "p_holm"}
    assert set(result["configurations"]) == {"top_k_20", *result["candidates"]}


def test_the_step8_choice_takes_the_best_correct_among_reliable_candidates() -> None:
    from exp002_leviers.step7 import choose_step8

    def candidate(correct, errors, ci_high, cost):
        return {
            "aggregates": {"correct": correct, "error_rate": errors, "cost_usd_mean": cost},
            "hallucination": {"ci_high": ci_high},
        }

    baseline = {"aggregates": {"correct": 0.78, "error_rate": 0.0, "cost_usd_mean": 0.001}}
    candidates = {
        "best_but_unreliable": candidate(0.95, 0.02, 0.0, 0.004),
        "invents_more": candidate(0.93, 0.0, 0.15, 0.004),
        "good": candidate(0.90, 0.0, 0.05, 0.009),
        "almost_as_good_and_cheaper": candidate(0.885, 0.0, 0.05, 0.002),
    }

    choice = choose_step8(baseline, candidates)

    assert choice["chosen"] == "almost_as_good_and_cheaper"
    assert set(choice["excluded"]) == {"best_but_unreliable", "invents_more"}


def test_the_launcher_refuses_a_test_run_of_its_own() -> None:
    from exp002_leviers.step7 import main

    with pytest.raises(SystemExit, match="run consolidé 2"):
        main(["--split", "test"])
