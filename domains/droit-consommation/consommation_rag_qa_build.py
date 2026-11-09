"""Contrôle les brouillons rag-qa, sélectionne les items et prépare leur relecture.

Pour chaque tâche du plan, le brouillon passe des contrôles bloquants (il est rejeté s'il en
échoue un) et des alertes (il est alors relu). Dans chaque mode et chaque split, on garde les
premiers brouillons qui passent, dans l'ordre du tirage. Les règles sont décrites dans
golden/rag-qa/README.md.

    uv run python domains/droit-consommation/consommation_rag_qa_build.py \\
        --version pilot --quotas pilot --seed 7
    uv run python domains/droit-consommation/consommation_rag_qa_build.py \\
        --version v1 --seed 42 --publish
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

from consommation_rag_qa_plan import PILOT_QUOTAS, V1_QUOTAS, V2_QUOTAS

from ailab_evals.rag_qa import fact_found, normalize

DOMAIN_DIR = Path(__file__).parent
GOLDEN_DIR = DOMAIN_DIR / "golden" / "rag-qa"

# Seuil de recouvrement lexical du mode paraphrase, fixé au pilote du 2026-11-04 : au-dessus du
# maximum mesuré en paraphrase (0,33), au-dessous du minimum du mode direct (0,57).
OVERLAP_THRESHOLD: float | None = 0.4
# Part des items sans alerte tirés pour la relecture. Elle était de 20 % ; en v1, le rédacteur
# exprime un doute sur 148 des 200 items retenus, et l'on relit donc tout (README, « Relecture »).
REVIEW_SHARE = 1.0
# Longueur maximale d'une question, en mots, fixée au pilote 3 : le prompt vise 15 mots, le
# rédacteur écrit jusqu'à 20. Le mode multi_article demande deux faits : 5 mots de plus.
MAX_QUESTION_WORDS: int | None = 20
MULTI_EXTRA_WORDS = 5
MAX_FACTS = 3
LONG_FORM_WORDS = 6

_SPACES = re.compile(r"[\s  ]+")
_WORDS = re.compile(r"[^\W\d_]+")
_ANY_ARTICLE_NUM = re.compile(r"(?<![A-Za-z0-9])[LRD]\s*\.?\s*\d+(?:-\d+)+")
_NUM = re.compile(r"^([LRD])(\d.*)$")
# Mots vides de quatre lettres ou plus, après normalisation N (sans accents).
STOPWORDS = frozenset(
    {
        "quel",
        "quelle",
        "quels",
        "quelles",
        "combien",
        "comment",
        "quand",
        "pourquoi",
        "pour",
        "dans",
        "avec",
        "sans",
        "sous",
        "entre",
        "apres",
        "avant",
        "depuis",
        "pendant",
        "chez",
        "lors",
        "vers",
        "contre",
        "selon",
        "cette",
        "ceux",
        "celle",
        "celles",
        "leur",
        "leurs",
        "elle",
        "elles",
        "nous",
        "vous",
        "ils",
        "sont",
        "etre",
        "avoir",
        "peut",
        "peuvent",
        "doit",
        "doivent",
        "faut",
        "faire",
        "fait",
        "tout",
        "tous",
        "toute",
        "toutes",
        "plus",
        "moins",
        "tres",
        "ainsi",
        "aussi",
        "alors",
        "donc",
        "mais",
        "encore",
        "dont",
        "quoi",
        "quelqu",
        "quelque",
        "autre",
        "autres",
        "meme",
        "memes",
        "code",
        "article",
    }
)


# --- Mesures ------------------------------------------------------------------------------------


def _squash(text: str) -> str:
    return _SPACES.sub(" ", text).strip()


def question_words(question: str) -> int:
    """Nombre de mots ; la ponctuation isolée par la typographie française (« : », « ? ») n'en
    est pas un."""
    return sum(any(c.isalnum() for c in token) for token in question.split())


def quote_in_text(quote: str, text: str) -> bool:
    """L'extrait figure mot pour mot dans le texte, aux espaces près."""
    return _squash(quote) in _squash(text)


def _tokens(text: str) -> list[str]:
    return _WORDS.findall(normalize(text))


def lexical_overlap(question: str, text: str) -> float:
    """Part des mots pleins de la question (au moins 4 lettres, hors mots vides) présents dans
    le texte de l'article, après normalisation N."""
    words = {w for w in _tokens(question) if len(w) >= 4 and w not in STOPWORDS}
    if not words:
        return 0.0
    return len(words & set(_tokens(text))) / len(words)


class Bm25:
    """BM25 (Okapi, k1 = 1,5, b = 0,75) sur le texte normalisé des articles : sert à montrer au
    relecteur d'un item sans réponse les articles les plus proches de la question."""

    def __init__(self, articles: list[dict], k1: float = 1.5, b: float = 0.75) -> None:
        self.ids = [a["id"] for a in articles]
        self.docs = [Counter(_tokens(a["text"])) for a in articles]
        self.lengths = [sum(doc.values()) for doc in self.docs]
        self.average = sum(self.lengths) / len(self.lengths)
        frequency: Counter[str] = Counter()
        for doc in self.docs:
            frequency.update(doc.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in frequency.items()}
        self.k1, self.b = k1, b

    def top(self, query: str, k: int) -> list[str]:
        terms = set(_tokens(query))
        scores = []
        for index, doc in enumerate(self.docs):
            norm = self.k1 * (1 - self.b + self.b * self.lengths[index] / self.average)
            score = sum(
                self.idf[t] * doc[t] * (self.k1 + 1) / (doc[t] + norm) for t in terms if t in doc
            )
            scores.append((-score, self.ids[index]))
        return [article_id for _, article_id in sorted(scores)[:k]]


# --- Contrôles ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    errors: list[str]
    alerts: list[str]
    overlap: float | None


def _cites(question: str, num: str) -> bool:
    match = _NUM.match(num)
    if not match:
        return False
    letter, rest = match.groups()
    pattern = rf"(?<![A-Za-z0-9]){letter}\s*\.?\s*{re.escape(rest)}(?![0-9-])"
    return re.search(pattern, _squash(question), re.IGNORECASE) is not None


def _found(form: str, text: str) -> bool:
    return fact_found({"accepted": [form]}, text)


def check(
    task: dict,
    draft: dict | None,
    by_id: dict[str, dict],
    *,
    overlap_threshold: float | None = OVERLAP_THRESHOLD,
    max_question_words: int | None = MAX_QUESTION_WORDS,
) -> Check:
    errors: list[str] = []
    alerts: list[str] = []
    output = draft.get("output") if draft else None
    if not isinstance(output, dict):
        reason = draft.get("stop_reason") if draft else "aucun brouillon"
        return Check([f"brouillon absent ou inexploitable ({reason})"], [], None)

    mode = task["mode"]
    articles = [by_id[i] for i in task["articles"]]
    by_num = {a["num"]: a for a in articles}
    question = str(output.get("question", ""))
    overlap = lexical_overlap(question, articles[0]["text"]) if question.strip() else None

    if not question.strip():
        errors.append("question vide")
    if max_question_words is not None:
        limit = max_question_words + (MULTI_EXTRA_WORDS if mode == "multi_article" else 0)
        if question_words(question) > limit:
            errors.append(f"question de {question_words(question)} mots, au-delà de {limit}")
    if draft and draft.get("model") != draft.get("model_requested"):
        alerts.append(f"rédigé par {draft.get('model')} au lieu de {draft.get('model_requested')}")
    if str(output.get("doubt", "")).strip():
        alerts.append(f"doute du rédacteur : {output['doubt'].strip()}")
    if mode in {"lost_context", "unanswerable"}:
        alerts.append(f"mode {mode} : relu systématiquement")

    if mode == "reference":
        if not _cites(question, articles[0]["num"]):
            errors.append(f"la question ne cite pas l'article {articles[0]['num']}")
    elif _ANY_ARTICLE_NUM.search(question):
        errors.append("la question cite un numéro d'article")

    if mode == "unanswerable":
        if output.get("facts"):
            errors.append("un item sans réponse ne doit donner aucun fait")
        if not str(output.get("why_unanswerable", "")).strip():
            errors.append("raison de l'absence de réponse manquante")
        return Check(errors, alerts, overlap)

    # Les brouillons du premier pilote n'avaient pas ce champ : son absence vaut « utilisable ».
    if output.get("usable") is False:
        errors.append("article inutilisable selon le rédacteur")
    facts = output.get("facts") or []
    if not 1 <= len(facts) <= MAX_FACTS:
        errors.append(f"{len(facts)} faits au lieu de 1 à {MAX_FACTS}")
    for index, fact in enumerate(facts, start=1):
        forms = [str(f) for f in fact.get("accepted", [])]
        quote = str(fact.get("quote", ""))
        article = by_num.get(str(fact.get("article", "")))
        if not forms:
            errors.append(f"fait {index} : aucune forme acceptée")
        if any(not normalize(f) for f in forms):
            errors.append(f"fait {index} : forme vide après normalisation")
        if article is None:
            errors.append(f"fait {index} : article {fact.get('article')!r} hors de la tâche")
        elif not quote.strip() or not quote_in_text(quote, article["text"]):
            errors.append(f"fait {index} : extrait introuvable dans l'article {article['num']}")
        if quote.strip() and forms and not any(_found(f, quote) for f in forms if normalize(f)):
            errors.append(f"fait {index} : aucune forme acceptée ne figure dans l'extrait")
        for form in forms:
            if normalize(form) and _found(form, question):
                errors.append(f"fait {index} : la question contient la réponse « {form} »")
            if len(form.split()) > LONG_FORM_WORDS:
                alerts.append(f"fait {index} : forme longue « {form} »")
            if (
                article is not None
                and normalize(form)
                and not any(c.isdigit() for c in form)
                and not _found(form, article["text"])
            ):
                alerts.append(f"fait {index} : forme sans chiffre absente du texte « {form} »")

    if mode == "multi_article":
        cited = {str(f.get("article", "")) for f in facts}
        missing = [a["num"] for a in articles if a["num"] not in cited]
        if missing:
            errors.append(f"aucun fait tiré de {', '.join(missing)}")
    if (
        mode == "paraphrase"
        and overlap_threshold is not None
        and overlap is not None
        and overlap > overlap_threshold
    ):
        errors.append(f"recouvrement lexical {overlap:.2f} > {overlap_threshold:.2f}")
    return Check(errors, alerts, overlap)


# --- Items --------------------------------------------------------------------------------------


def _unique_forms(forms: list[str]) -> list[str]:
    seen: set[str] = set()
    kept = []
    for form in forms:
        key = normalize(form)
        if key and key not in seen:
            seen.add(key)
            kept.append(form)
    return kept


def make_item(task: dict, output: dict, by_id: dict[str, dict]) -> dict:
    articles = [by_id[i] for i in task["articles"]]
    by_num = {a["num"]: a for a in articles}
    answerable = task["mode"] != "unanswerable"
    item: dict = {
        "id": None,
        "split": task["split"],
        "mode": task["mode"],
        "answerable": answerable,
        "question": output["question"].strip(),
    }
    if not answerable:
        item["expected"] = {"facts": [], "articles": []}
        item["evidence"] = []
        item["source_article"] = articles[0]["id"]
        return item
    facts = output["facts"]
    item["expected"] = {
        "facts": [{"accepted": _unique_forms(f["accepted"])} for f in facts],
        "articles": [{"id": a["id"], "num": a["num"]} for a in articles],
    }
    item["evidence"] = [{"article": by_num[f["article"]]["id"], "quote": f["quote"]} for f in facts]
    return item


def _apply_correction(item: dict, correction: dict, by_num: dict[str, dict]) -> dict:
    """Applique la correction d'un relecteur. Elle peut changer la question et les formes
    acceptées, et aussi le statut d'un item : `answerable`, `mode`, `articles` (par numéro) et
    `evidence`, dont chaque extrait est vérifié dans son article."""
    item = json.loads(json.dumps(item))
    if "question" in correction:
        item["question"] = correction["question"]
    if "mode" in correction:
        item["mode"] = correction["mode"]
    if "answerable" in correction:
        item["answerable"] = correction["answerable"]
        if item["answerable"]:
            item.pop("source_article", None)
    if "facts" in correction:
        item["expected"]["facts"] = [
            {"accepted": _unique_forms(f["accepted"])} for f in correction["facts"]
        ]
    if "articles" in correction:
        item["expected"]["articles"] = [
            {"id": by_num[num]["id"], "num": num} for num in correction["articles"]
        ]
    if "evidence" in correction:
        evidence = []
        for entry in correction["evidence"]:
            article = by_num[entry["article"]]
            if not quote_in_text(entry["quote"], article["text"]):
                raise ValueError(
                    f"correction : extrait introuvable dans l'article {article['num']}"
                )
            evidence.append({"article": article["id"], "quote": entry["quote"]})
        item["evidence"] = evidence
    return item


# --- Sélection ----------------------------------------------------------------------------------


@dataclass
class Selected:
    task: dict
    item: dict
    alerts: list[str]
    overlap: float | None
    needs_review: bool = False


@dataclass
class BuildResult:
    selected: list[Selected]
    shortages: dict[tuple[str, str], int]
    rejected: dict[str, list[str]]
    pending_review: list[str]
    checks: dict[str, tuple[dict, dict | None, Check]] = field(default_factory=dict)


def _sample_rank(seed: int, task_name: str) -> str:
    return hashlib.sha256(f"{seed}:{task_name}".encode()).hexdigest()


def build(
    plan: list[dict],
    drafts: dict[str, dict],
    by_id: dict[str, dict],
    quotas: dict[str, tuple[int, int]],
    *,
    seed: int,
    review: dict[str, dict] | None = None,
    overlap_threshold: float | None = OVERLAP_THRESHOLD,
    max_question_words: int | None = MAX_QUESTION_WORDS,
) -> BuildResult:
    review = review or {}
    by_num = {article["num"]: article for article in by_id.values()}
    checks: dict[str, tuple[dict, dict | None, Check]] = {}
    rejected: dict[str, list[str]] = {}
    passing: dict[str, Selected] = {}
    for task in plan:
        name = task["task"]
        draft = drafts.get(name)
        result = check(
            task,
            draft,
            by_id,
            overlap_threshold=overlap_threshold,
            max_question_words=max_question_words,
        )
        checks[name] = (task, draft, result)
        verdict = review.get(name, {})
        if result.errors:
            rejected[name] = result.errors
            continue
        if verdict.get("verdict") == "rejete":
            rejected[name] = [f"rejeté à la relecture : {verdict.get('note', '')}".strip()]
            continue
        assert draft is not None
        item = make_item(task, draft["output"], by_id)
        if verdict.get("verdict") == "corrige":
            item = _apply_correction(item, verdict.get("correction", {}), by_num)
        passing[name] = Selected(task, item, result.alerts, result.overlap)

    selected: list[Selected] = []
    shortages: dict[tuple[str, str], int] = {}
    for mode, (n_dev, n_test) in quotas.items():
        for split, quota in (("dev", n_dev), ("test", n_test)):
            group = sorted(
                (t for t in plan if t["mode"] == mode and t["split"] == split),
                key=lambda t: t["rank"],
            )
            kept = [passing[t["task"]] for t in group if t["task"] in passing][:quota]
            selected.extend(kept)
            if len(kept) < quota:
                shortages[(mode, split)] = quota - len(kept)

    unflagged = sorted(
        (s for s in selected if not s.alerts), key=lambda s: _sample_rank(seed, s.task["task"])
    )
    sampled = {s.task["task"] for s in unflagged[: math.ceil(REVIEW_SHARE * len(unflagged))]}
    for s in selected:
        s.needs_review = bool(s.alerts) or s.task["task"] in sampled
    reviewed = {name for name, v in review.items() if v.get("verdict") in {"ok", "corrige"}}
    pending = [
        s.task["task"] for s in selected if s.needs_review and s.task["task"] not in reviewed
    ]
    return BuildResult(selected, shortages, rejected, pending, checks)


# --- Publication --------------------------------------------------------------------------------


MODE_ORDER = list(V1_QUOTAS)
QUOTAS: dict[str, dict[str, tuple[int, int]]] = {
    "v1": V1_QUOTAS,
    "v2": V2_QUOTAS,
    "pilot": PILOT_QUOTAS,
}


def assign_ids(result: BuildResult, *, seed: int) -> dict[str, str]:
    """Identifiant de chaque tâche retenue : numéros mélangés (seedés), attribués sur l'ensemble des
    items retenus dans l'ordre (mode, split, rang). Remplacer un item `test` ne change pas ceux du
    `dev`."""
    ordered = sorted(
        result.selected,
        key=lambda s: (MODE_ORDER.index(s.task["mode"]), s.task["split"], s.task["rank"]),
    )
    numbers = list(range(1, len(ordered) + 1))
    random.Random(f"{seed}-ids").shuffle(numbers)
    return {
        chosen.task["task"]: f"rq-{number:03d}"
        for number, chosen in zip(numbers, ordered, strict=True)
    }


def _extension_ids(result: BuildResult, *, seed: int, base_ids: dict[str, str]) -> dict[str, str]:
    """Les tâches de la version de base gardent leur identifiant ; les nouvelles sont numérotées à
    la suite (après le plus grand numéro de la base), dans un ordre mélangé et seedé."""
    new = sorted(
        (s for s in result.selected if s.task["task"] not in base_ids),
        key=lambda s: (MODE_ORDER.index(s.task["mode"]), s.task["split"], s.task["rank"]),
    )
    start = max((int(rq.removeprefix("rq-")) for rq in base_ids.values()), default=0) + 1
    numbers = list(range(start, start + len(new)))
    random.Random(f"{seed}-ids-extension-{start}").shuffle(numbers)
    ids = {task: rq for task, rq in base_ids.items()}
    ids |= {s.task["task"]: f"rq-{n:03d}" for n, s in zip(numbers, new, strict=True)}
    return ids


def publish(
    result: BuildResult,
    out_dir: Path,
    *,
    seed: int,
    split: str | None = None,
    base_ids: dict[str, str] | None = None,
    base_items: list[dict] | None = None,
) -> list[dict]:
    """Attribue les identifiants et écrit `items.jsonl`, ou `items-<split>.jsonl` pour un seul
    split. Une version qui en étend une autre (`base_ids`, `base_items`) garde les identifiants et
    le contenu exact des items de la base : un item de base absent ou modifié bloque la
    publication."""
    shortages = {k: n for k, n in result.shortages.items() if split is None or k[1] == split}
    if shortages:
        missing = ", ".join(f"{m}/{s} : {n}" for (m, s), n in sorted(shortages.items()))
        raise ValueError(f"il manque des items : {missing}")
    in_split = {
        s.task["task"] for s in result.selected if split is None or s.task["split"] == split
    }
    pending = [name for name in result.pending_review if name in in_split]
    if pending:
        raise ValueError(f"{len(pending)} items attendent leur relecture")
    ids = (
        assign_ids(result, seed=seed)
        if base_ids is None
        else _extension_ids(result, seed=seed, base_ids=base_ids)
    )
    items = [
        {**chosen.item, "id": ids[chosen.task["task"]]}
        for chosen in result.selected
        if chosen.task["task"] in in_split
    ]
    if base_items is not None:
        by_id = {item["id"]: item for item in items}
        for expected in base_items:
            if split is not None and expected["split"] != split:
                continue
            if by_id.get(expected["id"]) != expected:
                raise ValueError(f"l'item {expected['id']} diffère de la version de base")
    items.sort(key=lambda item: item["id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    name = "items.jsonl" if split is None else f"items-{split}.jsonl"
    (out_dir / name).write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items), encoding="utf-8"
    )
    return items


# --- Page de relecture --------------------------------------------------------------------------


def _highlight(text: str, quotes: list[str]) -> str:
    rendered = html.escape(_squash(text))
    for quote in quotes:
        target = html.escape(_squash(quote))
        if target and target in rendered:
            rendered = rendered.replace(target, f"<mark>{target}</mark>", 1)
    return rendered


def _card(
    name: str,
    task: dict,
    draft: dict | None,
    result: Check,
    status: str,
    by_id: dict[str, dict],
    index: Bm25 | None,
) -> str:
    output = (draft or {}).get("output") or {}
    question = str(output.get("question", ""))
    facts = output.get("facts") or []
    quotes = [str(f.get("quote", "")) for f in facts]
    parts = [
        f'<section class="card {status}" data-task="{html.escape(name)}">',
        f"<h2>{html.escape(name)} <small>{html.escape(status)}</small></h2>",
        f'<p class="question">{html.escape(question)}</p>',
    ]
    if facts:
        rows = "".join(
            f"<tr><td>{html.escape(' · '.join(map(str, f.get('accepted', []))))}</td>"
            f"<td>{html.escape(str(f.get('article', '')))}</td>"
            f"<td>{html.escape(str(f.get('quote', '')))}</td></tr>"
            for f in facts
        )
        parts.append(f"<table><tr><th>Formes</th><th>Art.</th><th>Extrait</th></tr>{rows}</table>")
    if output.get("why_unanswerable"):
        parts.append(f"<p><b>Sans réponse :</b> {html.escape(output['why_unanswerable'])}</p>")
    for error in result.errors:
        parts.append(f'<p class="error">✗ {html.escape(error)}</p>')
    for alert in result.alerts:
        parts.append(f'<p class="alert">! {html.escape(alert)}</p>')
    if result.overlap is not None:
        parts.append(f"<p class='meta'>Recouvrement lexical : {result.overlap:.2f}</p>")
    for article_id in task["articles"]:
        article = by_id[article_id]
        parts.append(
            f"<details open><summary>{html.escape(article['num'])} — "
            f"{html.escape(' > '.join(article['path'][1:]))}</summary>"
            f"<p class='text'>{_highlight(article['text'], quotes)}</p></details>"
        )
    if task["mode"] == "unanswerable" and index is not None and question:
        neighbours = "".join(
            f"<li><b>{html.escape(by_id[i]['num'])}</b> {html.escape(by_id[i]['text'][:240])}…</li>"
            for i in index.top(question, 10)
        )
        parts.append(
            f"<details><summary>10 articles les plus proches (BM25)</summary>"
            f"<ol>{neighbours}</ol></details>"
        )
    correction = {
        "question": question,
        "facts": [{"accepted": f.get("accepted", [])} for f in facts],
    }
    parts.append(
        '<div class="verdict">'
        + "".join(
            f'<label><input type="radio" name="v-{html.escape(name)}" value="{v}"> {v}</label>'
            for v in ("ok", "corrige", "rejete")
        )
        + '<textarea class="note" placeholder="Note"></textarea>'
        + f'<textarea class="correction">{html.escape(json.dumps(correction, ensure_ascii=False))}'
        + "</textarea></div></section>"
    )
    return "\n".join(parts)


# Gabarit de la page (string.Template : $version, $summary, $cards).
_PAGE = Template((DOMAIN_DIR / "consommation_rag_qa_review.html").read_text(encoding="utf-8"))


def render_review_page(
    result: BuildResult, by_id: dict[str, dict], *, version: str, include_all: bool = False
) -> str:
    index = (
        Bm25(list(by_id.values()))
        if any(task["mode"] == "unanswerable" for task, _, _ in result.checks.values())
        else None
    )
    selected = {s.task["task"]: s for s in result.selected}
    cards = []
    order = sorted(
        result.checks.items(),
        key=lambda entry: (
            entry[1][0]["split"] != "dev",
            MODE_ORDER.index(entry[1][0]["mode"]),
            entry[1][0]["rank"],
        ),
    )
    current_split = None
    for name, (task, draft, checked) in order:
        chosen = selected.get(name)
        if chosen is not None:
            status = "à relire" if name in result.pending_review else "retenu"
            if not include_all and name not in result.pending_review:
                continue
        elif name in result.rejected:
            status = "rejected"
            if not include_all:
                continue
        else:
            status = "surplus"
            if not include_all:
                continue
        if task["split"] != current_split:
            current_split = task["split"]
            cards.append(f"<h2>Split {html.escape(current_split)}</h2>")
        cards.append(_card(name, task, draft, checked, status, by_id, index))
    summary = (
        f"{len(result.selected)} items retenus, {len(result.pending_review)} à relire, "
        f"{len(result.rejected)} brouillons rejetés, manques : {len(result.shortages)}."
    )
    return _PAGE.substitute(version=html.escape(version), summary=summary, cards="\n".join(cards))


# --- Ligne de commande --------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _drafts_and_review(golden_dir: Path, version: str) -> tuple[dict, dict]:
    drafts_dir = golden_dir / "drafts" / version
    drafts = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(drafts_dir.glob("*.json"))
    }
    review_path = golden_dir / "review" / f"{version}.jsonl"
    review = (
        {entry["task"]: entry for entry in _read_jsonl(review_path)} if review_path.exists() else {}
    )
    return drafts, review


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--version", required=True)
    parser.add_argument("--quotas", choices=["v1", "v2", "pilot"], default="v1")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--articles", type=Path, default=DOMAIN_DIR / "data/v1/articles.jsonl")
    parser.add_argument("--golden-dir", type=Path, default=GOLDEN_DIR)
    parser.add_argument("--page", type=Path, default=None)
    parser.add_argument("--overlap-threshold", type=float, default=OVERLAP_THRESHOLD)
    parser.add_argument("--max-question-words", type=int, default=MAX_QUESTION_WORDS)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument(
        "--publish-split", choices=["dev", "test"], help="écrit items-<split>.jsonl seulement"
    )
    parser.add_argument(
        "--base-version",
        help="version publiée que celle-ci étend : brouillons, relecture et identifiants repris",
    )
    parser.add_argument("--base-quotas", choices=["v1", "v2", "pilot"], default="v1")
    args = parser.parse_args(argv)

    version_dir = args.golden_dir / args.version
    plan = _read_jsonl(version_dir / "plan.jsonl")
    by_id = {a["id"]: a for a in _read_jsonl(args.articles)}
    quotas = QUOTAS[args.quotas]
    review_path = args.golden_dir / "review" / f"{args.version}.jsonl"
    drafts, review = _drafts_and_review(args.golden_dir, args.version)
    base_ids: dict[str, str] | None = None
    base_items: list[dict] | None = None
    if args.base_version:
        base_dir = args.golden_dir / args.base_version
        base_drafts, base_review = _drafts_and_review(args.golden_dir, args.base_version)
        base = build(
            _read_jsonl(base_dir / "plan.jsonl"),
            base_drafts,
            by_id,
            QUOTAS[args.base_quotas],
            seed=args.seed,
            review=base_review,
            overlap_threshold=args.overlap_threshold,
            max_question_words=args.max_question_words,
        )
        base_ids = assign_ids(base, seed=args.seed)
        base_items = _read_jsonl(base_dir / "items.jsonl")
        # La version étendue reprend les brouillons et les verdicts de sa base ; les siens
        # s'y ajoutent, et l'emportent pour une même tâche.
        drafts, review = base_drafts | drafts, base_review | review

    result = build(
        plan,
        drafts,
        by_id,
        quotas,
        seed=args.seed,
        review=review,
        overlap_threshold=args.overlap_threshold,
        max_question_words=args.max_question_words,
    )
    report = {
        "version": args.version,
        "seed": args.seed,
        "overlap_threshold": args.overlap_threshold,
        "max_question_words": args.max_question_words,
        "tasks": len(plan),
        "drafts": len(drafts),
        "selected": len(result.selected),
        "pending_review": result.pending_review,
        "shortages": {f"{m}/{s}": n for (m, s), n in sorted(result.shortages.items())},
        "rejected": result.rejected,
        "alerts": {s.task["task"]: s.alerts for s in result.selected if s.alerts},
        "overlap": {
            name: round(checked.overlap, 3)
            for name, (_, _, checked) in result.checks.items()
            if checked.overlap is not None
        },
        "question_words": {
            name: question_words(str((draft or {}).get("output", {}).get("question", "")))
            for name, (_, draft, _) in result.checks.items()
            if draft and isinstance(draft.get("output"), dict)
        },
        "writer_models": sorted({d.get("model", "") for d in drafts.values()}),
        "prompt_sha256": sorted({d.get("prompt_sha256", "") for d in drafts.values()}),
    }
    (version_dir / "build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    page = args.page or DOMAIN_DIR / ".cache" / f"rag-qa-review-{args.version}.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        render_review_page(result, by_id, version=args.version, include_all=args.quotas == "pilot"),
        encoding="utf-8",
    )
    print(
        f"{report['selected']} retenus, {len(result.pending_review)} à relire, "
        f"{len(result.rejected)} rejetés, manques {report['shortages']} ; page : {page}"
    )

    if args.publish_split:
        items = publish(
            result,
            version_dir,
            seed=args.seed,
            split=args.publish_split,
            base_ids=base_ids,
            base_items=base_items,
        )
        print(
            f"{len(items)} items {args.publish_split} écrits dans items-{args.publish_split}.jsonl"
        )
    if args.publish:
        items = publish(
            result, version_dir, seed=args.seed, base_ids=base_ids, base_items=base_items
        )
        manifest = {
            "dataset": "droit-consommation/golden/rag-qa",
            "version": args.version,
            "generators": [
                "domains/droit-consommation/consommation_rag_qa_plan.py",
                "domains/droit-consommation/consommation_rag_qa_draft.py",
                "domains/droit-consommation/consommation_rag_qa_build.py",
            ],
            "seed": args.seed,
            "base_version": args.base_version,
            "data_version": "v1",
            "spec": "evals/spec/rag-qa/v1",
            "writer_models": report["writer_models"],
            "prompt_sha256": report["prompt_sha256"],
            "overlap_threshold": args.overlap_threshold,
            "counts": dict(Counter(f"{i['mode']}/{i['split']}" for i in items)),
            "files": {
                "items.jsonl": _sha256(version_dir / "items.jsonl"),
                "plan.jsonl": _sha256(version_dir / "plan.jsonl"),
                f"review/{args.version}.jsonl": _sha256(review_path),
                **(
                    {
                        f"review/{args.base_version}.jsonl": _sha256(
                            args.golden_dir / "review" / f"{args.base_version}.jsonl"
                        )
                    }
                    if args.base_version
                    else {}
                ),
            },
        }
        (version_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{len(items)} items publiés dans {version_dir / 'items.jsonl'}")


if __name__ == "__main__":
    main()
