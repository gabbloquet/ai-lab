"""Traces et scores des exécutions dans Langfuse. Les fichiers JSONL restent la source de vérité."""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from langfuse import Langfuse

    from exp001_agent.campaign import Record

type Observe = Callable[["Record"], None]
"""Rattache le résultat noté d'une exécution à sa trace."""


class Tracer(Protocol):
    def execution(
        self, *, item: dict[str, Any], variant: str, repeat: int
    ) -> AbstractContextManager[Observe]: ...


class NoTracing:
    @contextmanager
    def execution(self, *, item: dict[str, Any], variant: str, repeat: int) -> Iterator[Observe]:
        yield lambda record: None


NO_TRACING = NoTracing()


class LangfuseTracing:
    """Une trace par exécution, regroupées par run (session), avec les scores de la spec."""

    def __init__(self, client: "Langfuse", *, run_id: str, split: str, model: str) -> None:
        from pydantic_ai import Agent

        # Les spans de Pydantic AI (requêtes au modèle, appels d'outils) passent par OpenTelemetry,
        # que le client Langfuse exporte.
        Agent.instrument_all()
        self._client = client
        self._run_id = run_id
        self._split = split
        self._model = model

    @contextmanager
    def execution(self, *, item: dict[str, Any], variant: str, repeat: int) -> Iterator[Observe]:
        from langfuse import propagate_attributes

        name = f"{item['id']} {variant} #{repeat}"
        with (
            propagate_attributes(
                session_id=self._run_id,
                trace_name=name,
                tags=[self._split, variant],
                metadata={
                    "item_id": item["id"],
                    "variant": variant,
                    "repeat": str(repeat),
                    "split": self._split,
                    "model": self._model,
                    "intent": item["tags"][0],
                },
            ),
            self._client.start_as_current_observation(
                name=name, as_type="agent", input=item["question"]
            ) as span,
        ):
            trace_id = self._client.get_current_trace_id()

            def observe(record: "Record") -> None:
                span.update(
                    output={
                        "answer": record.execution.answer,
                        "calls": record.execution.calls,
                        "error": record.execution.error,
                    }
                )
                if trace_id is not None:
                    self._score(trace_id, record)

            yield observe

    def flush(self) -> None:
        self._client.flush()

    def _score(self, trace_id: str, record: "Record") -> None:
        score = record.score
        for name, value in (("success", score.success), ("strict_success", score.strict_success)):
            self._client.create_score(
                name=name, value=float(value), trace_id=trace_id, data_type="BOOLEAN"
            )
        numeric = {
            "tool_recall": score.tool_recall,
            "args_recall": score.args_recall,
            "precision": score.precision,
            "n_calls": score.n_calls,
            "extra_calls": score.extra_calls,
        }
        for name, number in numeric.items():
            if number is not None:
                self._client.create_score(
                    name=name, value=float(number), trace_id=trace_id, data_type="NUMERIC"
                )
