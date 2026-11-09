"""Tire, de façon seedée, les articles qui serviront à rédiger le golden set rag-qa.

C'est le script qui choisit les articles, jamais le LLM rédacteur : laissé libre, il choisirait
les articles les plus connus. Les règles sont décrites dans golden/rag-qa/README.md (« Tirage »).

    uv run python domains/droit-consommation/consommation_rag_qa_plan.py \\
        --seed 7 --version pilot --quotas pilot
    uv run python domains/droit-consommation/consommation_rag_qa_plan.py --seed 42 --version v1 \\
        --exclude-plan domains/droit-consommation/golden/rag-qa/pilot/plan.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from itertools import combinations
from pathlib import Path

DOMAIN_DIR = Path(__file__).parent

# Items gardés par mode : (dev, test). README du golden set, « Composition ».
V1_QUOTAS: dict[str, tuple[int, int]] = {
    "direct": (10, 30),
    "reference": (8, 22),
    "paraphrase": (10, 30),
    "multi_article": (8, 22),
    "lost_context": (7, 23),
    "unanswerable": (7, 23),
}
# v2 : la v1 publiée, plus des questions sans réponse dans le `dev` (expérience 006, consigne
# d'abstention) ; le `test` est celui de la v1. 31 tâches `dev` retenues en mode `unanswerable` :
# 30 items sans réponse, plus rq-133, transformé en item avec réponse à la relecture de la v1.
V2_QUOTAS: dict[str, tuple[int, int]] = {**V1_QUOTAS, "unanswerable": (31, 23)}
# v3 : la v2, plus 40 questions sans réponse dans le `test` (expérience 006) ; les 150 items `test`
# de la v1 restent identiques. Avec 11 questions sans réponse valides sur 138 (audit de la v1),
# un effet de la consigne d'abstention sur `correct` ne pouvait pas dépasser quelques points.
V3_QUOTAS: dict[str, tuple[int, int]] = {**V1_QUOTAS, "unanswerable": (31, 63)}
# v4 : la v3, plus quatre modes tirés de la littérature RAG (CRAG, CRUMQs, Ragas). Les tailles
# suivent la capacité du corpus : ces modes se disputent les articles qui portent une valeur, et
# `bridge`, le vrai multi-hop, garde la plus grande (README du golden set, « v4 »).
V4_QUOTAS: dict[str, tuple[int, int]] = {
    **V3_QUOTAS,
    "comparison": (8, 22),
    "set": (8, 22),
    "bridge": (10, 30),
    "false_premise": (8, 22),
}
# Pilote : 20 brouillons jetés après la mise au point du prompt, sans surplus.
PILOT_QUOTAS: dict[str, tuple[int, int]] = {
    "direct": (4, 0),
    "reference": (3, 0),
    "paraphrase": (4, 0),
    "multi_article": (3, 0),
    "lost_context": (3, 0),
    "unanswerable": (3, 0),
}
# Pilotes des modes de la v4, jetés ensuite. `bridge` en a deux fois plus : son seuil de
# recouvrement se fixe sur la lecture de ses brouillons.
V4_PILOT_QUOTAS: dict[str, tuple[int, int]] = {
    "comparison": (10, 0),
    "set": (10, 0),
    "bridge": (20, 0),
    "false_premise": (10, 0),
}
# Réserve : deux fois le besoin. Au second pilote, 4 brouillons sur 20 ont été rejetés.
SURPLUS = 2.0

# Les modes au vivier le plus étroit tirent en premier : un article ne sert qu'une fois.
# Les modes de la v4 viennent après : ils ne sont tirés qu'en extension d'un plan existant, ou
# seuls dans leur pilote. Entre eux, les plus contraints d'abord.
DRAW_ORDER = (
    "lost_context",
    "multi_article",
    "reference",
    "direct",
    "paraphrase",
    "unanswerable",
    "comparison",
    "set",
    "bridge",
    "false_premise",
)

MIN_CHARS, MAX_CHARS = 200, 4000
LOST_CONTEXT = re.compile(
    r"\bprésente? (chapitre|titre|livre|section|sous-section)\b"
    r"|\b(ce|cette|ces) (délai|contrat|offre|professionnel|prêt|crédit)s?\b",
    re.IGNORECASE,
)
CITABLE_NUM = re.compile(r"^[LRD]\d")
_NUM = re.compile(r"^([LRD])(\d.*)$")
_SPACES = re.compile(r"\s+")

_NUMBER_WORDS = (
    "un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|"
    "seize|vingt|trente|quarante|cinquante|soixante|cent|mille"
)
_NUMBER = rf"(?:\d+(?:\s\d{{3}})*(?:,\d+)?|(?:{_NUMBER_WORDS})(?:[- ](?:{_NUMBER_WORDS}|et))*)"
VALUE_CLASSES = {
    "durée": re.compile(rf"\b{_NUMBER}\s+(?:jours?|mois|ans|années?|semaines?|heures?)\b", re.I),
    "montant": re.compile(rf"\b{_NUMBER}\s*(?:euros?\b|€)", re.I),
    "taux": re.compile(rf"\b{_NUMBER}\s*(?:%|pour cent\b)", re.I),
}
MIN_SET_ITEMS, MAX_SET_ITEMS = 3, 6
_ITEM_MARKERS = {
    "number": re.compile(r"^\s*\d+°"),
    "letter": re.compile(r"^\s*[a-z]\)"),
    "dash": re.compile(r"^\s*[-–]\s"),
}

Candidate = tuple[str, ...]  # les `id` d'articles d'une tâche : un seul, ou une paire A → B


# --- Viviers ------------------------------------------------------------------------------------


def eligible(article: dict) -> bool:
    text: str = article["text"]
    lines = text.split("\n")
    table_share = sum(" | " in line for line in lines) / len(lines)
    return (
        not article["num"].startswith("Annexe")
        and MIN_CHARS <= len(text) <= MAX_CHARS
        and article["valid_to"] is None
        and table_share < 0.5
    )


def lost_context_candidate(article: dict) -> bool:
    return bool(LOST_CONTEXT.search(article["text"]))


def reference_candidate(article: dict) -> bool:
    return bool(CITABLE_NUM.match(article["num"]))


def writes_number(text: str, num: str) -> bool:
    """Le texte écrit le numéro d'article `num` (« L. 312-25 » ou « L312-25 », pas
    « L. 312-25-1 »)."""
    match = _NUM.match(num)
    if not match:
        return False
    letter, rest = match.groups()
    pattern = rf"(?<![A-Za-z0-9]){letter}\s*\.?\s*{re.escape(rest)}(?![0-9-])"
    return re.search(pattern, _SPACES.sub(" ", text), re.IGNORECASE) is not None


def value_classes(text: str) -> dict[str, set[str]]:
    """Durées, montants et taux écrits dans un texte, par type. Détection par expression
    régulière : elle sert au tirage et aux contrôles, pas à la notation."""
    text = re.sub(r"[\u00a0\u202f]", " ", text)
    found = {
        name: {m.group(0).lower() for m in rx.finditer(text)} for name, rx in VALUE_CLASSES.items()
    }
    return {name: values for name, values in found.items() if values}


def enumeration(text: str) -> list[str]:
    """Éléments de premier niveau de l'énumération d'un texte (1°… ; à défaut a)… ; à défaut
    des tirets). Un élément garde ses sous-éléments ; une ligne sans marqueur le clôt."""
    lines = text.split("\n")
    top = next(
        (name for name, rx in _ITEM_MARKERS.items() if any(rx.match(line) for line in lines)),
        None,
    )
    if top is None:
        return []
    items: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if _ITEM_MARKERS[top].match(line):
            current = [line]
            items.append(current)
        elif current is not None and any(rx.match(line) for rx in _ITEM_MARKERS.values()):
            current.append(line)
        else:
            current = None
    return ["\n".join(item) for item in items]


def set_candidate(article: dict) -> bool:
    """Liste fermée de 3 à 6 éléments : au-delà, une réponse juste doit retrouver trop de
    mots-clés. « notamment » avant la liste la rend ouverte."""
    items = enumeration(article["text"])
    if not MIN_SET_ITEMS <= len(items) <= MAX_SET_ITEMS:
        return False
    preamble = article["text"][: article["text"].find(items[0])]
    return "notamment" not in preamble.lower()


def false_premise_candidate(article: dict) -> bool:
    return bool(value_classes(article["text"]))


def _title(article: dict) -> tuple:
    """Le titre du code qui contient l'article ; à défaut, son niveau au-dessus du dernier."""
    path = article["path"]
    end = next((i for i, part in enumerate(path) if part.startswith("Titre")), len(path) - 2)
    return (article["part"], tuple(path[: end + 1]))


def bridge_candidates(articles: list[dict]) -> list[Candidate]:
    """(A, B) : A cite B dans les liens LEGI, et le texte de A écrit le numéro de B."""
    pool = {a["id"]: a for a in articles if eligible(a)}
    return [
        (a["id"], b)
        for a in pool.values()
        for b in a["cites"]
        if b in pool and b != a["id"] and writes_number(a["text"], pool[b]["num"])
    ]


def comparison_candidates(articles: list[dict]) -> list[Candidate]:
    """(A, B) d'un même titre, avec un type de valeur en commun, chacun portant une valeur de
    ce type que l'autre n'a pas."""
    by_title: dict[tuple, list[dict]] = defaultdict(list)
    for a in articles:
        if eligible(a):
            by_title[_title(a)].append(a)
    pairs: list[Candidate] = []
    for group in by_title.values():
        values = {a["id"]: value_classes(a["text"]) for a in group}
        for a, b in combinations(group, 2):
            va, vb = values[a["id"]], values[b["id"]]
            if any(va[c] - vb[c] and vb[c] - va[c] for c in va.keys() & vb.keys()):
                pairs.append((a["id"], b["id"]))
    return pairs


def livre(article: dict) -> str:
    """Le livre du code, premier niveau sous la partie : « Livre II : … » devient « Livre II »."""
    level = article["path"][1] if len(article["path"]) > 1 else article["path"][0]
    return level.split(" :")[0].strip()


def _pools(articles: list[dict]) -> dict[str, list[Candidate]]:
    pool = [a for a in articles if eligible(a)]
    ids = {a["id"] for a in pool}

    def singles(keep: Callable[[dict], bool]) -> list[Candidate]:
        return [(a["id"],) for a in pool if keep(a)]

    pairs = [(a["id"], b) for a in pool for b in a["cites"] if b in ids and b != a["id"]]
    everything = singles(lambda a: True)
    return {
        "direct": everything,
        "reference": singles(reference_candidate),
        "paraphrase": everything,
        "multi_article": pairs,
        "lost_context": singles(lost_context_candidate),
        "unanswerable": everything,
        "comparison": comparison_candidates(articles),
        "set": singles(set_candidate),
        "bridge": bridge_candidates(articles),
        "false_premise": singles(false_premise_candidate),
    }


# --- Répartition --------------------------------------------------------------------------------


def allocate(available: dict[str, int], n: int) -> dict[str, int]:
    """Répartit n tirages entre les livres au prorata de leur vivier (plus forts restes),
    sans jamais demander plus que ce qu'un livre contient."""
    targets = {key: 0 for key in available}
    remaining = n
    open_keys = {key for key, count in available.items() if count > 0}
    while remaining > 0 and open_keys:
        total = sum(available[key] - targets[key] for key in open_keys)
        shares = {key: remaining * (available[key] - targets[key]) / total for key in open_keys}
        floors = {
            key: min(math.floor(share), available[key] - targets[key])
            for key, share in shares.items()
        }
        leftover = remaining - sum(floors.values())
        by_remainder = sorted(open_keys, key=lambda key: (-(shares[key] - floors[key]), key))
        for key in by_remainder:
            if leftover == 0:
                break
            if floors[key] < available[key] - targets[key]:
                floors[key] += 1
                leftover -= 1
        for key, extra in floors.items():
            targets[key] += extra
            remaining -= extra
        open_keys = {key for key in open_keys if targets[key] < available[key]}
    return targets


# --- Tirage -------------------------------------------------------------------------------------


def _draw(
    candidates: list[Candidate],
    n: int,
    used: set[str],
    livre_of: dict[str, str],
    rng: random.Random,
) -> list[Candidate]:
    free = [c for c in candidates if not used & set(c)]
    rng.shuffle(free)
    by_livre: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in free:
        by_livre[livre_of[candidate[0]]].append(candidate)
    targets = allocate({key: len(group) for key, group in sorted(by_livre.items())}, n)

    drawn: list[Candidate] = []

    def take(group: Iterable[Candidate], limit: int) -> None:
        for candidate in group:
            if limit == 0:
                return
            if used & set(candidate):
                continue
            drawn.append(candidate)
            used.update(candidate)
            limit -= 1

    for key in sorted(by_livre):
        take(by_livre[key], targets[key])
    # Une paire peut entrer en conflit avec une paire déjà tirée : on complète dans l'ordre mélangé.
    take(free, n - len(drawn))
    return drawn


def make_plan(
    articles: list[dict],
    *,
    seed: int,
    quotas: dict[str, tuple[int, int]],
    surplus: float = SURPLUS,
    exclude: set[str] | frozenset[str] = frozenset(),
) -> list[dict]:
    pools = _pools(articles)
    livre_of = {a["id"]: livre(a) for a in articles}
    used = set(exclude)
    plan: list[dict] = []
    drawn_by_mode: dict[str, list[dict]] = {}
    for mode in DRAW_ORDER:
        if mode not in quotas:
            continue
        dev, test = quotas[mode]
        n_dev, n_test = math.ceil(surplus * dev), math.ceil(surplus * test)
        rng = random.Random(f"{seed}-{mode}")
        drawn = _draw(pools[mode], n_dev + n_test, used, livre_of, rng)
        if len(drawn) < n_dev + n_test:
            raise ValueError(
                f"{mode} : {len(drawn)} candidats disponibles pour {n_dev + n_test} tirages"
            )
        rng.shuffle(drawn)
        tasks = []
        for split, chunk in (("dev", drawn[:n_dev]), ("test", drawn[n_dev:])):
            for rank, candidate in enumerate(chunk, start=1):
                tasks.append(
                    {
                        "task": f"{mode}-{split}-{rank:03d}",
                        "mode": mode,
                        "split": split,
                        "rank": rank,
                        "articles": list(candidate),
                        "livre": livre_of[candidate[0]],
                    }
                )
        drawn_by_mode[mode] = tasks
    for mode in quotas:  # ordre de sortie : celui des quotas, lisible
        plan.extend(drawn_by_mode[mode])
    return plan


def extend_plan(
    articles: list[dict],
    plan: list[dict],
    *,
    mode: str,
    split: str,
    n: int,
    seed: int,
    exclude: set[str] | frozenset[str] = frozenset(),
) -> list[dict]:
    """Ajoute n tâches à un mode et un split d'un plan existant, sans toucher aux tâches déjà
    tirées : c'est la seule modification permise d'un plan, quand la réserve ne suffit pas."""
    used = set(exclude) | {a for task in plan for a in task["articles"]}
    group = [t for t in plan if t["mode"] == mode and t["split"] == split]
    last = max((t["rank"] for t in group), default=0)
    rng = random.Random(f"{seed}-{mode}-{split}-extension-{last}")
    livre_of = {a["id"]: livre(a) for a in articles}
    drawn = _draw(_pools(articles)[mode], n, used, livre_of, rng)
    if len(drawn) < n:
        raise ValueError(f"{mode} : {len(drawn)} candidats disponibles pour {n} tirages")
    rng.shuffle(drawn)
    added = [
        {
            "task": f"{mode}-{split}-{rank:03d}",
            "mode": mode,
            "split": split,
            "rank": rank,
            "articles": list(candidate),
            "livre": livre_of[candidate[0]],
            "extension": True,
        }
        for rank, candidate in enumerate(drawn, start=last + 1)
    ]
    return [*plan, *added]


# --- Ligne de commande --------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--articles", type=Path, default=DOMAIN_DIR / "data/v1/articles.jsonl")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--version", required=True, help="ex. pilot, v1")
    parser.add_argument("--quotas", choices=["v1", "pilot", "pilot-v4"], default="v1")
    parser.add_argument("--golden-dir", type=Path, default=DOMAIN_DIR / "golden/rag-qa")
    parser.add_argument("--exclude-plan", type=Path, action="append", default=[])
    parser.add_argument("--extend", help="mode:split:n, ajoute n tâches à un plan existant")
    args = parser.parse_args(argv)

    out = args.golden_dir / args.version / "plan.jsonl"
    exclude = {
        a for path in args.exclude_plan for task in _read_jsonl(path) for a in task["articles"]
    }
    if args.extend:
        mode, split, n = args.extend.split(":")
        extended = extend_plan(
            _read_jsonl(args.articles),
            _read_jsonl(out),
            mode=mode,
            split=split,
            n=int(n),
            seed=args.seed,
            exclude=exclude,
        )
        out.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in extended), "utf-8")
        print(f"{n} tâches {mode}/{split} ajoutées à {out}")
        return
    if out.exists():
        sys.exit(f"{out} existe déjà : un plan ne se retire pas.")
    quotas, surplus = {
        "v1": (V1_QUOTAS, SURPLUS),
        "pilot": (PILOT_QUOTAS, 1.0),
        "pilot-v4": (V4_PILOT_QUOTAS, 1.0),
    }[args.quotas]
    plan = make_plan(
        _read_jsonl(args.articles), seed=args.seed, quotas=quotas, surplus=surplus, exclude=exclude
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in plan), "utf-8")
    print(f"{len(plan)} tâches écrites dans {out}")


if __name__ == "__main__":
    main()
