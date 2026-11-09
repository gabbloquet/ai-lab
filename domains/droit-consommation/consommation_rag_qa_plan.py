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
# suivent la capacité du corpus, revue après le premier pilote : ces modes se disputent les
# articles qui portent une valeur, et `bridge`, le vrai multi-hop, garde la plus grande (README du
# golden set, « v4 »).
# `bridge` a été retiré après le second pilote : l'article de la réponse se retrouvait presque
# toujours sans le saut. Sa capacité est revenue à `comparison` et à `false_premise`.
V4_QUOTAS: dict[str, tuple[int, int]] = {
    **V3_QUOTAS,
    "comparison": (8, 22),
    "set": (5, 12),
    "false_premise": (10, 30),
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
# Second pilote, après le durcissement du tirage : les trois modes rejetés à plus de 40 %.
V4_PILOT2_QUOTAS: dict[str, tuple[int, int]] = {
    "bridge": (10, 0),
    "comparison": (6, 0),
    "set": (6, 0),
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
    "bridge",
    "comparison",
    "set",
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
# Adaptations outre-mer : des listes de remplacements de mots, que personne ne demande en chat.
OVERSEAS = re.compile(
    r"outre-mer|Saint-Pierre|Mayotte|Wallis|Polynésie|Nouvelle-Calédonie|Saint-Barthélemy"
    r"|Saint-Martin",
    re.IGNORECASE,
)
# bridge, sens aller : au-delà, le renvoi de A se perd dans une liste d'articles.
MAX_BRIDGE_CITES = 2
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


_NUMBER_VALUES = {
    w: i
    for i, w in enumerate(
        [
            "zéro",
            "un",
            "deux",
            "trois",
            "quatre",
            "cinq",
            "six",
            "sept",
            "huit",
            "neuf",
            "dix",
            "onze",
            "douze",
            "treize",
            "quatorze",
            "quinze",
            "seize",
        ]
    )
} | {"une": 1, "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50, "soixante": 60}
_UNITS = {
    "€": "euro",
    "euros": "euro",
    "années": "an",
    "année": "an",
    "ans": "an",
    "pour cent": "%",
}


def _number(words: str) -> str:
    """« vingt-quatre » vaut 24, « 15 000 » vaut 15000, « 2,5 » reste 2,5."""
    if words[0].isdigit():
        return re.sub(r"\s", "", words)
    total = current = 0
    for word in re.split(r"[- ]", words):
        if word == "cent":
            current = (current or 1) * 100
        elif word == "mille":
            total, current = total + (current or 1) * 1000, 0
        elif word != "et":
            current += _NUMBER_VALUES.get(word, 0)
    return str(total + current)


def canonical_value(value: str) -> str:
    """Forme canonique d'une valeur trouvée par `value_classes` : « 3 000 € » et « 3 000 euros »,
    « quatorze jours » et « 14 jours » ont la même."""
    value = re.sub(r"[\u00a0\u202f\s]+", " ", value.lower()).strip()
    match = re.match(rf"({_NUMBER})\s*(.*)$", value)
    if not match:
        return value
    unit = match.group(2).strip()
    unit = _UNITS.get(unit, unit[:-1] if unit.endswith("s") and unit != "mois" else unit)
    return f"{_number(match.group(1))} {_UNITS.get(unit, unit)}"


def _canonical_classes(text: str) -> dict[str, set[str]]:
    return {c: {canonical_value(v) for v in vs} for c, vs in value_classes(text).items()}


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
    mots-clés. « notamment » avant la liste la rend ouverte. Sont écartées aussi les adaptations
    outre-mer, et les listes dont plus d'un tiers des éléments renvoient à un article : leur
    contenu est ailleurs."""
    items = enumeration(article["text"])
    if not MIN_SET_ITEMS <= len(items) <= MAX_SET_ITEMS:
        return False
    if OVERSEAS.search(article["text"]) or any(OVERSEAS.search(p) for p in article["path"]):
        return False
    if sum("article" in item.lower() for item in items) > len(items) // 3:
        return False
    preamble = article["text"][: article["text"].find(items[0])]
    return "notamment" not in preamble.lower()


def false_premise_candidate(article: dict) -> bool:
    return bool(value_classes(article["text"]))


def _chapter(article: dict) -> tuple:
    """Le chapitre du code qui contient l'article ; à défaut, son niveau au-dessus du dernier."""
    path = article["path"]
    end = next((i for i, part in enumerate(path) if part.startswith("Chapitre")), len(path) - 2)
    return (article["part"], tuple(path[: end + 1]))


def _has_own_value(article: dict, other: dict) -> bool:
    """L'article porte une durée, un montant ou un taux que l'autre n'écrit pas."""
    mine, theirs = _canonical_classes(article["text"]), _canonical_classes(other["text"])
    return any(values - theirs.get(c, set()) for c, values in mine.items())


def bridge_candidates(articles: list[dict]) -> list[Candidate]:
    """(départ, réponse) : la question part du premier article, la valeur est dans le second, et
    l'un écrit le numéro de l'autre. Deux sens :
    - aller : A renvoie à B (« dans le délai mentionné à l'article L. 312-25 »), A cite au plus
      deux articles, et B porte une valeur absente de A ;
    - inversé : l'article de sanction S cite l'obligation O (« tout manquement à l'article
      L. 112-3 est passible… ») ; la question part de O, la valeur est dans S."""
    pool = {a["id"]: a for a in articles if eligible(a)}
    pairs: list[Candidate] = []
    for citing in pool.values():
        for cited_id in dict.fromkeys(citing["cites"]):
            cited = pool.get(cited_id)
            if cited is None or cited_id == citing["id"]:
                continue
            if not writes_number(citing["text"], cited["num"]):
                continue
            few_cites = len(set(citing["cites"])) <= MAX_BRIDGE_CITES
            if few_cites and _has_own_value(cited, citing):
                pairs.append((citing["id"], cited_id))
            if _has_own_value(citing, cited):
                pairs.append((cited_id, citing["id"]))
    return list(dict.fromkeys(pairs))


def comparison_candidates(articles: list[dict]) -> list[Candidate]:
    """(A, B) d'un même chapitre, avec un type de valeur en commun et aucune valeur de ce type
    partagée : deux cas voisins, réglés par deux valeurs différentes."""
    by_chapter: dict[tuple, list[dict]] = defaultdict(list)
    for a in articles:
        if eligible(a):
            by_chapter[_chapter(a)].append(a)
    pairs: list[Candidate] = []
    for group in by_chapter.values():
        values = {a["id"]: _canonical_classes(a["text"]) for a in group}
        for a, b in combinations(group, 2):
            va, vb = values[a["id"]], values[b["id"]]
            if any(va[c].isdisjoint(vb[c]) for c in va.keys() & vb.keys()):
                pairs.append((a["id"], b["id"]))
    return pairs


def _item_articles(items: list[dict]) -> set[str]:
    return {a["id"] for i in items for a in i["expected"]["articles"]} | {
        i["source_article"] for i in items if i.get("source_article")
    }


def reusable_articles(plan: list[dict], rejected: dict, items: list[dict]) -> set[str]:
    """Articles des tâches rejetées (contrôles ou relecture) qu'aucun item n'utilise : tirés,
    jamais publiés, ils peuvent servir à un nouveau mode (README du golden set, « v4 »)."""
    freed = {a for t in plan if t["task"] in rejected for a in t["articles"]}
    return freed - _item_articles(items)


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
    freed_tasks: set[str] | frozenset[str] = frozenset(),
) -> list[dict]:
    """Ajoute n tâches à un mode et un split d'un plan existant, sans toucher aux tâches déjà
    tirées : c'est la seule modification permise d'un plan, quand la réserve ne suffit pas.
    Les articles des tâches libérées (`freed_tasks`, des tâches rejetées) peuvent être tirés à
    nouveau, une seule fois : leur nouvelle tâche, elle, n'est pas libérée."""
    used = set(exclude) | {
        a for task in plan if task["task"] not in freed_tasks for a in task["articles"]
    }
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


def _version_files(golden_dir: Path, version: str) -> tuple[list[dict], dict, list[dict]]:
    base = golden_dir / version
    report = json.loads((base / "build_report.json").read_text("utf-8"))
    return _read_jsonl(base / "plan.jsonl"), report["rejected"], _read_jsonl(base / "items.jsonl")


def excluded_articles(
    plan_paths: list[Path], reuse_versions: list[str], golden_dir: Path
) -> set[str]:
    """Articles à exclure d'un tirage : ceux des plans donnés. Dans le plan d'une version de
    `reuse_versions`, les articles réutilisables sont libérés ; un article qu'un autre plan a
    déjà repris reste exclu. Les articles des items de ces versions restent exclus."""
    reusable: dict[Path, set[str]] = {
        (golden_dir / v / "plan.jsonl").resolve(): reusable_articles(*_version_files(golden_dir, v))
        for v in reuse_versions
    }
    excluded: set[str] = set()
    for path in plan_paths:
        articles = {a for task in _read_jsonl(path) for a in task["articles"]}
        excluded |= articles - reusable.get(path.resolve(), set())
    for version in reuse_versions:
        excluded |= _item_articles(_version_files(golden_dir, version)[2])
    return excluded


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--articles", type=Path, default=DOMAIN_DIR / "data/v1/articles.jsonl")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--version", required=True, help="ex. pilot, v1")
    parser.add_argument("--quotas", choices=["v1", "pilot", "pilot-v4", "pilot2-v4"], default="v1")
    parser.add_argument("--golden-dir", type=Path, default=DOMAIN_DIR / "golden/rag-qa")
    parser.add_argument("--exclude-plan", type=Path, action="append", default=[])
    parser.add_argument("--extend", help="mode:split:n, ajoute n tâches à un plan existant")
    parser.add_argument(
        "--reuse-rejected",
        action="append",
        default=[],
        help="version dont les articles des tâches rejetées peuvent être tirés à nouveau",
    )
    args = parser.parse_args(argv)

    out = args.golden_dir / args.version / "plan.jsonl"
    exclude = excluded_articles(args.exclude_plan, args.reuse_rejected, args.golden_dir)
    if args.extend:
        mode, split, n = args.extend.split(":")
        freed: set[str] = set()
        for version in args.reuse_rejected:
            _, rejected, items = _version_files(args.golden_dir, version)
            freed |= set(rejected)
            exclude |= _item_articles(items)
        extended = extend_plan(
            _read_jsonl(args.articles),
            _read_jsonl(out),
            mode=mode,
            split=split,
            n=int(n),
            seed=args.seed,
            exclude=exclude,
            freed_tasks=freed,
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
        "pilot2-v4": (V4_PILOT2_QUOTAS, 1.0),
    }[args.quotas]
    plan = make_plan(
        _read_jsonl(args.articles), seed=args.seed, quotas=quotas, surplus=surplus, exclude=exclude
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in plan), "utf-8")
    print(f"{len(plan)} tâches écrites dans {out}")


if __name__ == "__main__":
    main()
