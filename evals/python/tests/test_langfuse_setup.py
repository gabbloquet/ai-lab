import pytest

from ailab_evals.langfuse_setup import credentials


@pytest.fixture
def infra_env(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "# commentaire\n"
        "LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk-local\n"
        'LANGFUSE_INIT_PROJECT_SECRET_KEY="sk-local"\n',
        encoding="utf-8",
    )
    return path


def test_falls_back_to_the_keys_created_by_the_local_install(infra_env, monkeypatch):
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        monkeypatch.setenv(name, "")

    assert credentials(infra_env) == ("http://localhost:3000", "pk-local", "sk-local")


def test_prefers_the_keys_given_in_the_environment(infra_env, monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-env")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-env")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "http://127.0.0.1:3001")

    assert credentials(infra_env) == ("http://127.0.0.1:3001", "pk-env", "sk-env")


def test_refuses_to_start_without_keys(tmp_path, monkeypatch):
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        monkeypatch.setenv(name, "")

    with pytest.raises(SystemExit, match="introuvables"):
        credentials(tmp_path / "absent.env")
