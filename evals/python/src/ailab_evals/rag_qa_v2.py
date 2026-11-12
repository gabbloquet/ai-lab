"""Scorer de la spec rag-qa v2 (evals/spec/rag-qa/v2/SPEC.md).

Cœur de notation pur, sans DeepEval ni LLM : il est vérifié par les vecteurs de conformance. Les
numéros de section renvoient à la spec. Le scorer v1 (`rag_qa`) reste tel quel : des rapports
publiés le citent.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Collection, Iterable
from dataclasses import dataclass

from scipy import stats

KS = (1, 3, 5, 10)
WINDOW = 6  # § 5.4
MARKERS = (
    ("non",),
    ("pas",),
    ("ni",),
    ("plutot", "que"),
    ("au", "lieu", "de"),
    ("contrairement",),
    ("faux",),
    ("inexact",),
    ("errone",),
    ("incorrect",),
)
FAILURES = ("correct", "retrieval_miss", "generation_miss", "error")
PREMISES = ("corrected", "unresolved", "adopted", "missed")

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})
_LIGATURES = str.maketrans({"œ": "oe", "æ": "ae"})
_SPACE_BETWEEN_DIGITS = re.compile(r"(?<=[0-9]) (?=[0-9])")
_SPACE_BEFORE_SIGN = re.compile(r"(?<=[0-9]) (?=[%€])")
_SPACES = re.compile(r" +")
_CITATION_PREFIXES = ("articles", "article", "art.")
_SENTENCE_BREAKS = set(";!?\n\r")
_CLAUSE = re.compile(r",? et ")


# --- § 4 : normalisation -------------------------------------------------------------------------


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
    text = _SPACE_BEFORE_SIGN.sub("", text)
    return _SPACES.sub(" ", text).strip()


def _letter_or_digit(char: str) -> bool:
    return unicodedata.category(char)[0] in {"L", "N"}


def words(text: str) -> list[str]:
    """§ 5.2 : les suites maximales de lettres ou chiffres."""
    found, current = [], []
    for char in text:
        if _letter_or_digit(char):
            current.append(char)
        elif current:
            found.append("".join(current))
            current = []
    if current:
        found.append("".join(current))
    return found


# --- § 5.1 et § 5.2 : formes --------------------------------------------------------------------


def _occurrences(form: str, text: str) -> list[int]:
    """Débuts des occurrences délimitées de N(form) dans `text`, déjà normalisé."""
    needle = normalize(form)
    starts, start = [], text.find(needle)
    while start != -1:
        end = start + len(needle)
        before_ok = start == 0 or not _letter_or_digit(text[start - 1])
        after_ok = end == len(text) or not _letter_or_digit(text[end])
        if before_ok and after_ok:
            starts.append(start)
        start = text.find(needle, start + 1)
    return starts


def _tokens_found(form: dict, text: str) -> bool:
    """§ 5.2 : mots-clés dans l'ordre, au plus `window` mots entre deux mots-clés consécutifs."""
    sequence = words(text)
    tokens = [normalize(token) for token in form["tokens"]]
    window = form["window"]

    def match_from(token_index: int, position: int) -> bool:
        if token_index == len(tokens):
            return True
        last = min(len(sequence), position + window + 1)
        return any(
            sequence[p] == tokens[token_index] and match_from(token_index + 1, p + 1)
            for p in range(position, last)
        )

    return any(word == tokens[0] and match_from(1, p + 1) for p, word in enumerate(sequence))


def form_found(form: str | dict, text: str) -> bool:
    """Une forme acceptée dans un texte déjà normalisé."""
    if isinstance(form, str):
        return bool(_occurrences(form, text))
    return _tokens_found(form, text)


def fact_found(fact: dict, text: str) -> bool:
    return any(form_found(form, text) for form in fact["accepted"])


# --- § 5.3 : rattachement ------------------------------------------------------------------------


def _sentences(answer: str) -> list[str]:
    """§ 5.3 étapes 1 à 3 : phrases normalisées, non vides."""
    text = unicodedata.normalize("NFC", answer)
    parts, current = [], []
    for index, char in enumerate(text):
        if char in _SENTENCE_BREAKS:
            parts.append("".join(current))
            current = []
        elif char == "." and (index + 1 == len(text) or text[index + 1].isspace()):
            preceding = words(text[:index].casefold())
            ends_word = index > 0 and _letter_or_digit(text[index - 1])
            last = preceding[-1] if preceding and ends_word else None
            if last is not None and ((len(last) == 1 and last.isalpha()) or last == "art"):
                current.append(char)
            else:
                parts.append("".join(current))
                current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return [n for n in (normalize(part) for part in parts) if n]


def segments(answer: str) -> list[str]:
    """§ 5.3 : toutes les phrases et toutes les propositions."""
    found = []
    for sentence in _sentences(answer):
        found.append(sentence)
        found.extend(clause for clause in _CLAUSE.split(sentence) if clause.strip())
    return found


def _anchored(facts: list[dict]) -> bool:
    return bool(facts) and all("anchor" in fact for fact in facts)


def fact_attached(facts: list[dict], index: int, answer: str) -> bool:
    own = facts[index]["anchor"]
    others = [form for j, fact in enumerate(facts) if j != index for form in fact["anchor"]]
    return any(
        fact_found(facts[index], segment)
        and any(form_found(form, segment) for form in own)
        and not any(form_found(form, segment) for form in others)
        for segment in segments(answer)
    )


# --- § 5.4 : prémisse ----------------------------------------------------------------------------


def _marked(text: str, start: int) -> bool:
    before = words(text[:start])[-WINDOW:]
    return any(
        tuple(before[i : i + len(marker)]) == marker
        for marker in MARKERS
        for i in range(len(before) - len(marker) + 1)
    )


def false_value_taken(false_value: dict, text: str) -> bool:
    """§ 5.4 : au moins une occurrence délimitée n'est pas marquée."""
    return any(
        not _marked(text, start)
        for form in false_value["accepted"]
        for start in _occurrences(form, text)
    )


# --- § 6 : métriques par exécution ---------------------------------------------------------------


def normalize_citation(citation: str) -> str:
    """La normalisation C du § 6."""
    text = normalize(citation)
    for prefix in _CITATION_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    return text.replace(" ", "").replace(".", "").upper()


def _first_occurrences(ids: list[str]) -> list[str]:
    return list(dict.fromkeys(ids))


def score_execution(item: dict, execution: dict) -> dict:
    """§ 6 : les métriques d'une exécution, sous les noms de la spec."""
    answerable: bool = item["answerable"]
    facts: list[dict] = item["expected"]["facts"]
    gold = {article["id"] for article in item["expected"]["articles"]}
    answer = execution["answer"]
    text = normalize(answer)
    abstained: bool = execution["abstained"]
    failed = execution["error"] is not None
    raw_context = execution["context"]
    context = None if raw_context is None else _first_occurrences(raw_context)
    tool_calls = execution["tool_calls"]
    false_value = item.get("false_value")

    found_each = [fact_found(fact, text) for fact in facts]
    found = sum(found_each) if answerable else None
    attached = None
    if answerable and _anchored(facts):
        attached = sum(fact_attached(facts, i, answer) for i in range(len(facts)))
    taken = false_value_taken(false_value, text) if false_value is not None else None

    if failed:
        correct = False
    elif answerable:
        correct = (
            not abstained
            and all(found_each)
            and (attached is None or attached == len(facts))
            and not taken
        )
    else:
        correct = abstained

    premise = None
    if false_value is not None:
        premise = {
            (True, False): "corrected",
            (True, True): "unresolved",
            (False, True): "adopted",
            (False, False): "missed",
        }[(all(found_each), bool(taken))]

    scores_context = context is not None and answerable
    ranked = scores_context and (tool_calls is None or tool_calls <= 1)
    recall: dict[int, float | None] = {}
    complete: dict[int, bool | None] = {}
    for k in KS:
        top = set(context[:k]) if ranked and context is not None else None
        recall[k] = None if top is None else len(gold & top) / len(gold)
        complete[k] = None if top is None else gold <= top

    failure = None
    if scores_context and context is not None:
        if failed:
            failure = "error"
        elif correct:
            failure = "correct"
        elif gold <= set(context):
            failure = "generation_miss"
        else:
            failure = "retrieval_miss"

    precision = citation_recall = None
    if answerable:
        cited = {normalize_citation(c) for c in execution["cited"]}
        expected_nums = {normalize_citation(a["num"]) for a in item["expected"]["articles"]}
        matched = len(cited & expected_nums)
        precision = matched / len(cited) if cited else None
        citation_recall = matched / len(expected_nums)

    return {
        "correct": correct,
        "facts_found": found,
        "facts_attached": attached,
        "premise": premise,
        "false_abstention": None if failed or not answerable else abstained,
        "hallucination": None if failed or answerable else not abstained,
        **{f"evidence_recall@{k}": recall[k] for k in KS},
        **{f"all_evidence@{k}": complete[k] for k in KS},
        "all_evidence": gold <= set(context) if scores_context and context is not None else None,
        "context_size": None if context is None else len(context),
        "failure": failure,
        "citation_precision": precision,
        "citation_recall": citation_recall,
        "tool_calls": tool_calls,
        "latency_s": execution["latency_s"],
        "cost_usd": execution["cost_usd"],
    }


# --- § 7 : agrégats par variante -----------------------------------------------------------------


def _as_number(value) -> float | None:
    if value is None:
        return None
    return float(value)


def _mean(values: Iterable) -> float | None:
    present = [_as_number(v) for v in values if v is not None]
    return sum(present) / len(present) if present else None


def _strict_mean(values: list) -> float | None:
    """Moyenne seulement si aucune valeur n'est nulle (§ 7, cinq dernières clés)."""
    if not values or any(v is None for v in values):
        return None
    return sum(float(v) for v in values) / len(values)


def percentile(values: list[float], q: float) -> float:
    """§ 7 : interpolation linéaire entre les rangs (méthode 7 de Hyndman et Fan)."""
    ordered = sorted(values)
    h = (len(ordered) - 1) * q
    low = math.floor(h)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (h - low) * (ordered[high] - ordered[low])


def _distribution(values: list, keys: tuple[str, ...]) -> dict[str, float] | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return {key: sum(v == key for v in present) / len(present) for key in keys}


def _kept(items: list[dict], split: str, excluded: Collection[str]) -> dict[str, dict]:
    """§ 7 et § 8.4 : les items du split, hors items exclus."""
    return {i["id"]: i for i in items if i["split"] == split and i["id"] not in set(excluded)}


def variant_aggregates(
    items: list[dict], executions: list[dict], *, split: str, excluded: Collection[str] = ()
) -> dict:
    """§ 7 : les exécutions d'une variante avec un modèle."""
    kept = _kept(items, split, excluded)
    rows = [(kept[e["item_id"]], e) for e in executions if e["item_id"] in kept]
    scores = [score_execution(item, e) for item, e in rows]

    tokens = [
        None
        if e["usage"]["input_tokens"] is None or e["usage"]["output_tokens"] is None
        else e["usage"]["input_tokens"] + e["usage"]["output_tokens"]
        for _, e in rows
    ]
    latencies = [e["latency_s"] for _, e in rows]
    complete_latencies = bool(latencies) and all(v is not None for v in latencies)
    by_mode: dict[str, list[bool]] = {}
    for (item, _), score in zip(rows, scores, strict=True):
        by_mode.setdefault(item["mode"], []).append(score["correct"])

    result = {
        "n_executions": len(rows),
        "correct": _mean(s["correct"] for s in scores),
        "correct_answerable": _mean(
            s["correct"] for (item, _), s in zip(rows, scores, strict=True) if item["answerable"]
        ),
        "false_abstention_rate": _mean(s["false_abstention"] for s in scores),
        "hallucination_rate": _mean(s["hallucination"] for s in scores),
        "error_rate": _mean(e["error"] is not None for _, e in rows),
    }
    for k in KS:
        result[f"evidence_recall@{k}"] = _mean(s[f"evidence_recall@{k}"] for s in scores)
        result[f"all_evidence@{k}"] = _mean(s[f"all_evidence@{k}"] for s in scores)
    result |= {
        "all_evidence": _mean(s["all_evidence"] for s in scores),
        "context_size": _mean(s["context_size"] for s in scores),
        "failure": _distribution([s["failure"] for s in scores], FAILURES),
        "premise": _distribution([s["premise"] for s in scores], PREMISES),
        "correct_by_mode": {mode: _mean(values) for mode, values in by_mode.items()},
        "tokens_mean": _strict_mean(tokens),
        "cost_usd_mean": _strict_mean([e["cost_usd"] for _, e in rows]),
        "latency_s_median": percentile(latencies, 0.5) if complete_latencies else None,
        "latency_s_p95": percentile(latencies, 0.95) if complete_latencies else None,
        "tool_calls_mean": _strict_mean([e["tool_calls"] for _, e in rows]),
    }
    return result


# --- § 8 : comparaison et verdicts ---------------------------------------------------------------


@dataclass(frozen=True)
class PairedScore:
    item_id: str
    split: str
    p_a: float
    p_b: float


def _oriented(low: float, high: float, direction: str) -> tuple[bool, bool]:
    """(s'améliore, se dégrade), selon le sens de la métrique (§ 8.1, étape 5)."""
    if direction == "higher_better":
        return low > 0, high < 0
    return high < 0, low > 0


def paired_comparison(pairs: list[PairedScore], direction: str) -> dict:
    """§ 8.1 étapes 3 à 5, et p-value du § 8.3, sur les pᵢ du split `test`."""
    differences = [p.p_b - p.p_a for p in pairs if p.split == "test"]
    n = len(differences)
    if n < 2:
        return {
            "n": n,
            "delta": None,
            "ci_low": None,
            "ci_high": None,
            "verdict": None,
            "p_value": None,
        }
    delta = sum(differences) / n
    deviation = math.sqrt(sum((d - delta) ** 2 for d in differences) / (n - 1))
    half_width = float(stats.t.ppf(0.975, n - 1)) * deviation / math.sqrt(n)
    low, high = delta - half_width, delta + half_width
    improves, worsens = _oriented(low, high, direction)
    if deviation == 0.0:
        p_value = 1.0 if delta == 0.0 else 0.0
    else:
        t = delta / (deviation / math.sqrt(n))
        p_value = float(2 * stats.t.sf(abs(t), n - 1))
    return {
        "n": n,
        "delta": delta,
        "ci_low": low,
        "ci_high": high,
        "verdict": "b_better" if improves else "b_worse" if worsens else "inconclusive",
        "p_value": p_value,
    }


def _per_item(
    kept: dict[str, dict], executions: list[dict], variant: str, metric: str
) -> dict[str, float]:
    """§ 8.1 étape 1 : moyenne de la métrique sur les exécutions notées de chaque item."""
    values: dict[str, list[float]] = {}
    for execution in executions:
        item = kept.get(execution["item_id"])
        if item is None or execution["variant"] != variant:
            continue
        value = score_execution(item, execution)[metric]
        if value is not None:
            values.setdefault(item["id"], []).append(float(value))
    return {item_id: sum(v) / len(v) for item_id, v in values.items()}


def compare(
    items: list[dict],
    executions: list[dict],
    *,
    baseline: str,
    variant: str,
    metric: str,
    direction: str,
    split: str,
    excluded: Collection[str] = (),
) -> dict:
    """§ 8.1 : comparaison appariée de B à A sur une métrique."""
    kept = _kept(items, split, excluded)
    p_a = _per_item(kept, executions, baseline, metric)
    p_b = _per_item(kept, executions, variant, metric)
    pairs = [
        PairedScore(item_id, "test", p_a[item_id], p_b[item_id])
        for item_id in kept
        if item_id in p_a and item_id in p_b
    ]
    return paired_comparison(pairs, direction)


def joint_verdict(
    main: dict, guard: dict, *, main_direction: str, guard_direction: str, margin: float
) -> str | None:
    """§ 8.2 : verdict à deux critères."""
    if main["delta"] is None or guard["delta"] is None:
        return None
    improves, worsens = _oriented(main["ci_low"], main["ci_high"], main_direction)
    if guard_direction == "lower_better":
        holds, broken = guard["ci_high"] < margin, guard["ci_low"] > margin
    else:
        holds, broken = guard["ci_low"] > -margin, guard["ci_high"] < -margin
    if worsens or broken:
        return "b_worse"
    if improves:
        return "b_better" if holds else "tradeoff"
    return "inconclusive"


def joint_comparison(
    items: list[dict],
    executions: list[dict],
    *,
    baseline: str,
    variant: str,
    main: tuple[str, str],
    guard: tuple[str, str],
    margin: float,
    split: str,
    excluded: Collection[str] = (),
) -> dict:
    """§ 8.2 : les deux comparaisons et le verdict."""
    common = {"baseline": baseline, "variant": variant, "split": split, "excluded": excluded}
    main_result = compare(items, executions, metric=main[0], direction=main[1], **common)
    guard_result = compare(items, executions, metric=guard[0], direction=guard[1], **common)
    return {
        "main": main_result,
        "guard": guard_result,
        "verdict": joint_verdict(
            main_result,
            guard_result,
            main_direction=main[1],
            guard_direction=guard[1],
            margin=margin,
        ),
    }


@dataclass(frozen=True)
class FamilyMember:
    name: str
    direction: str
    pairs: list[PairedScore]


def holm_family(members: list[FamilyMember], *, alpha: float = 0.05) -> list[dict]:
    """§ 8.3 : p-values, ajustement de Holm et verdict corrigé, dans l'ordre reçu."""
    results = [paired_comparison(member.pairs, member.direction) for member in members]
    raw = [r["p_value"] for r in results]
    filled = [1.0 if p is None else p for p in raw]
    m = len(filled)
    order = sorted(range(m), key=lambda i: filled[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * filled[i]))
        adjusted[i] = running

    output = []
    for member, result, p, p_holm in zip(members, results, raw, adjusted, strict=True):
        if p is None:
            output.append(
                {"name": member.name, "p_value": None, "p_holm": None, "verdict_holm": None}
            )
            continue
        if p_holm < alpha:
            improves = (result["delta"] > 0) == (member.direction == "higher_better")
            verdict = "b_better" if improves else "b_worse"
        else:
            verdict = "inconclusive"
        output.append(
            {"name": member.name, "p_value": p, "p_holm": p_holm, "verdict_holm": verdict}
        )
    return output
