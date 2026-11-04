"""Scorer de la spec rag-qa v1 (evals/spec/rag-qa/v1/SPEC.md).

Cœur de notation pur, sans DeepEval ni LLM : il est vérifié par les vecteurs de conformance. Les
numéros de section renvoient à la spec.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ailab_evals.paired import Aggregate as Aggregate
from ailab_evals.paired import PairedScore as PairedScore
from ailab_evals.paired import aggregate as aggregate

KS = (1, 3, 5, 10)

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})
_LIGATURES = str.maketrans({"œ": "oe", "æ": "ae"})
_SPACE_BETWEEN_DIGITS = re.compile(r"(?<=[0-9]) (?=[0-9])")
_SPACES = re.compile(r" +")
_CITATION_PREFIXES = ("articles", "article", "art.")


# --- § 4 et § 5 : texte -------------------------------------------------------------------------


def normalize(text: str) -> str:
    """La normalisation N du § 4, étape par étape."""
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_APOSTROPHES)
    text = "".join(" " if char.isspace() else char for char in text)
    text = text.casefold()
    decomposed = unicodedata.normalize("NFD", text)
    text = unicodedata.normalize(
        "NFC", "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    )
    text = text.translate(_LIGATURES)
    text = _SPACE_BETWEEN_DIGITS.sub("", text)
    return _SPACES.sub(" ", text).strip()


def _letter_or_digit(char: str) -> bool:
    return unicodedata.category(char)[0] in {"L", "N"}


def _delimited_in(form: str, answer: str) -> bool:
    start = answer.find(form)
    while start != -1:
        end = start + len(form)
        before_ok = start == 0 or not _letter_or_digit(answer[start - 1])
        after_ok = end == len(answer) or not _letter_or_digit(answer[end])
        if before_ok and after_ok:
            return True
        start = answer.find(form, start + 1)
    return False


def fact_found(fact: dict, answer: str) -> bool:
    """§ 5 : l'une des formes acceptées, normalisée, apparaît délimitée dans la réponse."""
    normalized_answer = normalize(answer)
    return any(_delimited_in(normalize(form), normalized_answer) for form in fact["accepted"])


def normalize_citation(citation: str) -> str:
    """La normalisation C du § 6."""
    text = normalize(citation)
    for prefix in _CITATION_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    return text.replace(" ", "").replace(".", "").upper()


# --- § 6 : métriques par exécution ---------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionScore:
    correct: bool
    facts_found: int | None
    false_abstention: bool | None
    hallucination: bool | None
    evidence_recall: dict[int, float | None]
    all_evidence: dict[int, bool | None]
    context_size: int | None
    failure: str | None
    citation_precision: float | None
    citation_recall: float | None

    def as_dict(self) -> dict:
        """Les noms de la spec, dont `evidence_recall@k` et `all_evidence@k`."""
        return {
            "correct": self.correct,
            "facts_found": self.facts_found,
            "false_abstention": self.false_abstention,
            "hallucination": self.hallucination,
            **{f"evidence_recall@{k}": self.evidence_recall[k] for k in KS},
            **{f"all_evidence@{k}": self.all_evidence[k] for k in KS},
            "context_size": self.context_size,
            "failure": self.failure,
            "citation_precision": self.citation_precision,
            "citation_recall": self.citation_recall,
        }


def _first_occurrences(ids: list[str]) -> list[str]:
    """§ 3.2 : seule la première occurrence d'un article compte."""
    return list(dict.fromkeys(ids))


def score_execution(item: dict, execution: dict) -> ExecutionScore:
    """§ 6. `item` est une ligne du golden set, `execution` la forme canonique du § 3.2."""
    answerable: bool = item["answerable"]
    facts: list[dict] = item["expected"]["facts"]
    gold = {article["id"] for article in item["expected"]["articles"]}
    answer: str = execution["answer"]
    abstained: bool = execution["abstained"]
    failed = execution["error"] is not None
    raw_context = execution["context"]
    context = None if raw_context is None else _first_occurrences(raw_context)

    found = sum(fact_found(fact, answer) for fact in facts) if answerable else None
    if failed:
        correct = False
    elif answerable:
        correct = not abstained and found == len(facts)
    else:
        correct = abstained

    scores_context = context is not None and answerable
    recall: dict[int, float | None] = {}
    complete: dict[int, bool | None] = {}
    for k in KS:
        top = set(context[:k]) if scores_context and context is not None else None
        recall[k] = None if top is None else len(gold & top) / len(gold)
        complete[k] = None if top is None else gold <= top

    failure: str | None = None
    if scores_context and context is not None:
        if failed:
            failure = "error"
        elif correct:
            failure = "correct"
        elif gold <= set(context):
            failure = "generation_miss"
        else:
            failure = "retrieval_miss"

    precision: float | None = None
    citation_recall: float | None = None
    if answerable:
        cited = {normalize_citation(c) for c in execution["cited"]}
        expected_nums = {normalize_citation(a["num"]) for a in item["expected"]["articles"]}
        matched = len(cited & expected_nums)
        precision = matched / len(cited) if cited else None
        citation_recall = matched / len(expected_nums)

    return ExecutionScore(
        correct=correct,
        facts_found=found,
        false_abstention=None if failed or not answerable else abstained,
        hallucination=None if failed or answerable else not abstained,
        evidence_recall=recall,
        all_evidence=complete,
        context_size=None if context is None else len(context),
        failure=failure,
        citation_precision=precision,
        citation_recall=citation_recall,
    )
