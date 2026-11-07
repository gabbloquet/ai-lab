"""Traces et scores des exécutions de la 002 dans Langfuse. Les fichiers JSONL restent la source
de vérité : Langfuse sert à explorer un run, pas à le noter."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any, Protocol

from ailab_evals.rag_qa import KS

type Observe = Callable[[dict[str, Any], dict[str, Any]], None]
"""Rattache une exécution et son score (spec rag-qa, § 6) à leur trace."""

NUMERIC_SCORES = (
    "facts_found",
    *(f"evidence_recall@{k}" for k in KS),
    "context_size",
    "citation_precision",
    "citation_recall",
)
BOOLEAN_SCORES = (
    "correct",
    "false_abstention",
    "hallucination",
    *(f"all_evidence@{k}" for k in KS),
)


class Tracer(Protocol):
    def execution(
        self, *, item: dict[str, Any], variant: str, repeat: int
    ) -> AbstractContextManager[Observe]: ...


class NoTracing:
    @contextmanager
    def execution(self, *, item: dict[str, Any], variant: str, repeat: int) -> Iterator[Observe]:
        yield lambda execution, score: None


NO_TRACING = NoTracing()


class LangfuseTracing:
    """Une trace par exécution, regroupées par run (session), avec les scores de la spec."""

    def __init__(
        self,
        client: Any,
        *,
        run_id: str,
        split: str,
        model: str,
        propagate: Callable[..., AbstractContextManager[Any]] | None = None,
        instrument: bool = True,
    ) -> None:
        if propagate is None:
            from langfuse import propagate_attributes

            propagate = propagate_attributes
        if instrument:
            from pydantic_ai import Agent

            # Les requêtes au modèle, prompt et extraits compris, passent par OpenTelemetry, que
            # le client Langfuse exporte.
            Agent.instrument_all()
        self._client = client
        self._propagate = propagate
        self._run_id = run_id
        self._split = split
        self._model = model

    @contextmanager
    def execution(self, *, item: dict[str, Any], variant: str, repeat: int) -> Iterator[Observe]:
        name = f"{item['id']} {variant} #{repeat}"
        with (
            self._propagate(
                session_id=self._run_id,
                trace_name=name,
                tags=[self._split, variant, item["mode"]],
                metadata={
                    "item_id": item["id"],
                    "variant": variant,
                    "repeat": str(repeat),
                    "split": self._split,
                    "model": self._model,
                    "mode": item["mode"],
                    "answerable": str(item["answerable"]),
                },
            ),
            self._client.start_as_current_observation(
                name=name, as_type="agent", input=item["question"]
            ) as span,
        ):
            trace_id = self._client.get_current_trace_id()

            def observe(execution: dict[str, Any], score: dict[str, Any]) -> None:
                span.update(
                    output={
                        key: execution[key]
                        for key in ("answer", "abstained", "cited", "context", "error")
                    }
                )
                if trace_id is not None:
                    self._score(trace_id, score)

            yield observe

    def flush(self) -> None:
        self._client.flush()

    def _score(self, trace_id: str, score: dict[str, Any]) -> None:
        for name in BOOLEAN_SCORES:
            if score[name] is not None:
                self._client.create_score(
                    name=name, value=float(score[name]), trace_id=trace_id, data_type="BOOLEAN"
                )
        for name in NUMERIC_SCORES:
            if score[name] is not None:
                self._client.create_score(
                    name=name, value=float(score[name]), trace_id=trace_id, data_type="NUMERIC"
                )
        if score["failure"] is not None:
            self._client.create_score(
                name="failure", value=score["failure"], trace_id=trace_id, data_type="CATEGORICAL"
            )
