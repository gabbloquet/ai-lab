"""Les garde-fous du lanceur : ils jouent avant tout appel payant."""

import pytest

from exp002_leviers.campaign import main

MODEL = ["--model", "mistral:mistral-small-2603"]


def _main(argv: list[str], *, clean: bool = True, reproduces: bool = True) -> None:
    main(argv, git_is_clean=lambda: clean, reproduces=lambda: reproduces)


def test_the_test_split_needs_the_final_flag() -> None:
    with pytest.raises(SystemExit, match="--final"):
        _main(["--split", "test", *MODEL])


def test_a_final_run_needs_a_clean_git_tree() -> None:
    with pytest.raises(SystemExit, match="gel"):
        _main(["--split", "test", "--final", *MODEL], clean=False)


def test_the_reranking_needs_the_cohere_key(monkeypatch) -> None:
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="COHERE_API_KEY"):
        _main(["--split", "dev", *MODEL])


def test_no_run_starts_if_the_frozen_configurations_are_not_reproduced(monkeypatch) -> None:
    monkeypatch.setenv("COHERE_API_KEY", "clé-de-test")
    with pytest.raises(SystemExit, match="reproduction"):
        _main(["--split", "dev", *MODEL], reproduces=False)


def test_a_v2_run_needs_the_published_v5_golden_set(tmp_path, monkeypatch) -> None:
    """Spec rag-qa v2 : le run se fait sur la v5 ; tant qu'elle n'est pas publiée, rien ne part."""
    import exp002_leviers.campaign as campaign

    monkeypatch.setattr(campaign, "GOLDEN_V5", tmp_path / "v5" / "items.jsonl")
    with pytest.raises(SystemExit, match="v5"):
        _main(["--split", "dev", "--spec", "v2", *MODEL])


def test_v2_executions_are_checked_against_the_canonical_schema() -> None:
    from exp002_leviers.campaign import invalid_v2_executions

    good = {
        "item_id": "rq-001",
        "variant": "naive_rag",
        "model": "m",
        "repeat": 0,
        "answer": "14 jours",
        "abstained": False,
        "cited": [],
        "context": [],
        "usage": {"input_tokens": 1, "output_tokens": 1},
        "latency_s": 1.0,
        "cost_usd": None,
        "tool_calls": None,
        "error": None,
    }
    old = {k: v for k, v in good.items() if k not in {"latency_s", "cost_usd", "tool_calls"}}

    assert invalid_v2_executions([good]) == []
    assert invalid_v2_executions([good, {**old, "latency": {"generation_s": 1.0}}]) == [1]


def test_the_v2_control_run_adds_step6_from_the_top_k_20_executions(tmp_path) -> None:
    """L'étape 6 ne rappelle pas le générateur : B vient des exécutions top_k_20 et des notes
    Cohere, et ses exécutions sont écrites à part (le fichier se récrit à chaque appel)."""
    import json

    from exp002_leviers.campaign import with_step6

    a = {
        "item_id": "rq-001",
        "variant": "top_k_20",
        "model": "m",
        "repeat": 0,
        "answer": "14 jours",
        "abstained": False,
        "cited": [],
        "context": [],
        "usage": {"input_tokens": 1, "output_tokens": 1},
        "latency_s": 1.0,
        "cost_usd": None,
        "tool_calls": None,
        "error": None,
        "extra": {"generation_s": 0.6},
    }
    other = {**a, "variant": "naive_rag"}

    combined = with_step6([a, other], lambda ids: {i: 0.1 for i in ids}, tmp_path)
    combined = with_step6([a, other], lambda ids: {i: 0.1 for i in ids}, tmp_path)

    written = [
        json.loads(line) for line in (tmp_path / "step6-executions.jsonl").read_text().splitlines()
    ]
    assert [e["variant"] for e in combined] == ["top_k_20", "naive_rag", "abstain_low_rerank"]
    assert written == combined[2:]
