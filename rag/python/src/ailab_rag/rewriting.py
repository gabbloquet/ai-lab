"""Levier « réécriture de requête » : avant la recherche, un modèle traduit la question du
particulier dans la langue du Code de la consommation.

Le modèle ne voit pas le corpus : il s'appuie sur ce qu'il sait de la langue juridique. Seule
la recherche utilise la réécriture ; le modèle qui répond reçoit la question d'origine. Les
réécritures sont gardées sur disque : une question n'est réécrite qu'une fois par modèle et
par prompt, et toutes les répétitions cherchent avec la même réécriture.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from ailab_rag.corpus import Passage

# Prompts validés le 2026-11-07.
REFORMULATE = (
    "Réécris cette question d'un particulier avec le vocabulaire juridique du Code de la "
    "consommation français, en une seule phrase, sans y répondre."
)
# Cycle 1 de B dans la 003 (2026-11-08) : au run 0, la reformulation perdait le numéro d'article
# cité et l'un des sujets des questions sur plusieurs articles.
REFORMULATE_KEEP = (
    REFORMULATE
    + " Garde tel quel tout numéro d'article cité, et garde tous les sujets de la question."
)
HYDE = (
    "Écris en deux ou trois phrases l'extrait d'article du Code de la consommation français qui "
    "répondrait à cette question, dans le style du code."
)


class QueryRewriter:
    def __init__(self, model: str | Model, instructions: str, cache_dir: Path) -> None:
        self._model_name = model if isinstance(model, str) else model.model_name
        self._agent = Agent(
            model, instructions=instructions, model_settings=ModelSettings(temperature=0.0)
        )
        self._instructions = instructions
        self._cache_dir = cache_dir

    def _path(self, question: str) -> Path:
        key = f"{self._model_name}\n{self._instructions}\n{question}"
        return self._cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()}.txt"

    def _store(self, question: str, output: object) -> str:
        text = str(output).strip()
        if not text:
            return question
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._path(question).write_text(text, encoding="utf-8")
        return text

    def rewrite(self, question: str) -> str:
        """La réécriture, ou la question d'origine si le modèle ne renvoie rien d'utile."""
        path = self._path(question)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return self._store(question, self._agent.run_sync(question).output)

    def rewrite_all(self, questions: list[str], workers: int = 8) -> None:
        """Réécrit d'avance toutes les questions, en parallèle, avant la campagne : pendant les
        runs, la recherche ne lit plus que le cache. Une seule boucle asyncio : le client du
        modèle ne peut pas être partagé entre plusieurs boucles (incident du 2026-11-08, où des
        threads ayant chacun leur boucle se le partageaient)."""
        pending = list(dict.fromkeys(q for q in questions if not self._path(q).exists()))
        if pending:
            asyncio.run(self._rewrite_all(pending, workers))

    async def _rewrite_all(self, questions: list[str], workers: int) -> None:
        semaphore = asyncio.Semaphore(workers)

        async def one(question: str) -> None:
            async with semaphore:
                self._store(question, (await self._agent.run(question)).output)

        await asyncio.gather(*(one(q) for q in questions))


class RewritingRetriever:
    def __init__(self, rewriter: QueryRewriter, inner: Callable[[str, int], list[Passage]]) -> None:
        self._rewriter = rewriter
        self._inner = inner

    def retrieve(self, question: str, k: int) -> list[Passage]:
        return self._inner(self._rewriter.rewrite(question), k)
