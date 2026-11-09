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
