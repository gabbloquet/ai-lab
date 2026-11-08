"""Les utilitaires communs aux lignes de commande des campagnes : chemins affichés, état git."""

import subprocess
import threading
import time
from pathlib import Path

import pytest

from ailab_rag.cli import current_commit, display_path, flush_with_deadline, git_is_clean


def git_repo(path: Path) -> Path:
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "lab@example.com")
    git("config", "user.name", "lab")
    (path / "a.txt").write_text("a")
    git("add", "a.txt")
    git("commit", "-q", "-m", "init")
    return path


def test_a_path_inside_the_repository_is_shown_relative_to_it(tmp_path: Path) -> None:
    assert display_path(tmp_path / "golden" / "items.jsonl", tmp_path) == "golden/items.jsonl"


def test_a_relative_path_is_resolved_before_being_shown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "golden").mkdir()
    monkeypatch.chdir(tmp_path / "golden")

    assert display_path(Path("items.jsonl"), tmp_path) == "golden/items.jsonl"


def test_a_path_outside_the_repository_is_shown_absolute(tmp_path: Path) -> None:
    outside = Path("/elsewhere/items.jsonl")

    assert display_path(outside, tmp_path) == str(outside.resolve())


def test_a_freshly_committed_tree_is_clean(tmp_path: Path) -> None:
    assert git_is_clean(git_repo(tmp_path))


def test_an_untracked_file_makes_the_tree_dirty(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "b.txt").write_text("b")

    assert not git_is_clean(repo)


def test_the_current_commit_is_the_full_hash_of_head(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()

    assert current_commit(repo) == head
    assert len(head) == 40


def test_a_flush_that_finishes_in_time_is_reported_as_done() -> None:
    calls = []

    assert flush_with_deadline(lambda: calls.append("flushed"), seconds=1.0)
    assert calls == ["flushed"]


def test_a_flush_that_hangs_is_abandoned_at_the_deadline() -> None:
    """Leçon de la 003 : un Langfuse qui ne répond plus ne doit pas bloquer la campagne."""
    never = threading.Event()
    start = time.monotonic()

    assert not flush_with_deadline(never.wait, seconds=0.1)
    assert time.monotonic() - start < 1.0


def test_a_flush_that_fails_is_reported_as_not_done() -> None:
    def fail() -> None:
        raise ConnectionError("Langfuse injoignable")

    assert not flush_with_deadline(fail, seconds=1.0)
