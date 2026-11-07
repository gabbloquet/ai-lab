"""La ligne de commande de la 002 : garde-fous du run final, chemins cités, commit enregistré."""

from pathlib import Path

import pytest

from exp002_rag.campaign import ROOT, current_commit, default_golden, display_path, main

# --- Ligne de commande --------------------------------------------------------------------------


def test_the_test_split_needs_the_final_flag() -> None:
    with pytest.raises(SystemExit, match="--final"):
        main(
            ["--split", "test", "--model", "mistral:mistral-small-2603"], git_is_clean=lambda: True
        )


def test_a_final_run_needs_a_clean_git_tree() -> None:
    with pytest.raises(SystemExit, match="gel"):
        main(
            ["--split", "test", "--final", "--model", "mistral:mistral-small-2603"],
            git_is_clean=lambda: False,
        )


def test_reports_cite_paths_relative_to_the_repository(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(ROOT)
    golden = Path("domains/droit-consommation/golden/rag-qa/v1/items.jsonl")

    assert display_path(golden) == "domains/droit-consommation/golden/rag-qa/v1/items.jsonl"
    assert display_path(ROOT / golden) == "domains/droit-consommation/golden/rag-qa/v1/items.jsonl"
    assert display_path(tmp_path / "x.jsonl") == str((tmp_path / "x.jsonl").resolve())


def test_dev_runs_read_the_dev_file_and_the_final_run_the_whole_set() -> None:
    assert default_golden("dev").name == "items-dev.jsonl"
    assert default_golden("test").name == "items.jsonl"
    assert default_golden("dev").parent == default_golden("test").parent


def test_a_run_records_the_commit_it_ran_on() -> None:
    commit = current_commit()

    assert len(commit) == 40 and all(c in "0123456789abcdef" for c in commit)
