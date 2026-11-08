"""Utilitaires communs aux lignes de commande des campagnes de la série RAG.

Repris à l'identique des 002 et 003, qui gardent leur propre copie : leur code est la trace de
ce qui a tourné pour leurs runs finaux. Chaque fonction reçoit la racine du dépôt.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ailab_rag.tracing import LangfuseTracing


def display_path(path: Path, root: Path) -> str:
    """Le chemin relatif à la racine du dépôt s'il y est, absolu sinon."""
    resolved = path.resolve()
    return str(resolved.relative_to(root)) if resolved.is_relative_to(root) else str(resolved)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def git_is_clean(root: Path) -> bool:
    """Vrai si rien n'est modifié ni non suivi : condition d'un run final."""
    return _git(root, "status", "--porcelain") == ""


def current_commit(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD")


def langfuse_tracer(root: Path, *, run_id: str, split: str, model: str) -> LangfuseTracing:
    """Le traceur du Langfuse local (`infra/langfuse/.env`), après avoir vérifié qu'il répond."""
    from langfuse import Langfuse

    from ailab_evals.langfuse_setup import check_reachable, credentials

    base_url, public_key, secret_key = credentials(root / "infra/langfuse/.env")
    check_reachable(base_url)
    client = Langfuse(public_key=public_key, secret_key=secret_key, base_url=base_url)
    return LangfuseTracing(client, run_id=run_id, split=split, model=model)
