"""Connexion au Langfuse local : clés de .env, ou à défaut celles créées par infra/langfuse."""

import os
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "http://localhost:3000"


def credentials(infra_env: Path) -> tuple[str, str, str]:
    """(base_url, public_key, secret_key) : LANGFUSE_* prime sur infra/langfuse/.env."""
    local = _read_env(infra_env) if infra_env.exists() else {}
    public = os.environ.get("LANGFUSE_PUBLIC_KEY") or local.get("LANGFUSE_INIT_PROJECT_PUBLIC_KEY")
    secret = os.environ.get("LANGFUSE_SECRET_KEY") or local.get("LANGFUSE_INIT_PROJECT_SECRET_KEY")
    base_url = os.environ.get("LANGFUSE_BASE_URL") or DEFAULT_BASE_URL
    if not public or not secret:
        raise SystemExit(f"Clés Langfuse introuvables : LANGFUSE_* dans .env, ou {infra_env}.")
    return base_url, public, secret


def check_reachable(base_url: str) -> None:
    try:
        with urllib.request.urlopen(f"{base_url}/api/public/health", timeout=5) as response:
            if response.status == 200:
                return
    except OSError as error:
        raise SystemExit(f"Langfuse ne répond pas sur {base_url} ({error}).") from error
    raise SystemExit(f"Langfuse ne répond pas sur {base_url}.")


def _read_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"')
    return values
