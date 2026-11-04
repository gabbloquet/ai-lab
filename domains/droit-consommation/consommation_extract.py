"""Extrait le Code de la consommation de l'archive LEGI de la DILA, dans son état à une date.

Lit l'archive complète en un seul passage, sans la décompresser sur disque, garde les versions
d'article en vigueur à la date d'état, puis écrit `articles.jsonl` et `MANIFEST.json`.

    curl -fO https://echanges.dila.gouv.fr/OPENDATA/LEGI/Freemium_legi_global_20250713-140000.tar.gz
    uv run python domains/droit-consommation/consommation_extract.py \\
        --archive Freemium_legi_global_20250713-140000.tar.gz --version v1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

CODE_ID = "LEGITEXT000006069565"
STATE_DATE = date(2025, 7, 13)
ARCHIVE_SHA256 = "f862b4a2238e11ec3c48ec70f3b1c68bac0bb1985907841666b98608653d4eca"
SOURCE_BASE_URL = "https://echanges.dila.gouv.fr/OPENDATA/LEGI/"
LICENCE = "Licence Ouverte / Open Licence (Etalab)"

# LEGI marque une date de fin ouverte par cette valeur.
OPEN_END = "2999-01-01"
# Racines du plan : celles de la recodification de 2016, puis celles des versions antérieures.
PARTS = {
    "Partie législative nouvelle": "legislative",
    "Partie réglementaire nouvelle": "regulatory",
    "Partie législative": "legislative",
    "Partie réglementaire": "regulatory",
}
# États d'une version qui n'est jamais entrée en vigueur, quelles que soient ses dates.
NEVER_IN_FORCE = {"MODIFIE_MORT_NE", "ANNULE"}

# Balises qui coupent une ligne ; les autres (b, i, em, sup…) restent dans la ligne.
BLOCK_TAGS = {"CONTENU", "p", "div", "table", "tbody", "thead"}
CELL_TAGS = {"td", "th"}
# Espaces insécables, fréquentes dans les montants (« 1 500 euros »).
SPACES = re.compile(r"[\s  ]+")


@dataclass(frozen=True)
class LegiArticle:
    id: str
    num: str
    state: str
    valid_from: date
    valid_to: date | None
    path: tuple[str, ...]
    section_id: str
    part: str
    text: str
    nota: str
    cited_nums: tuple[str, ...]


# --- Texte --------------------------------------------------------------------------------------


def _flat(value: str | None) -> str:
    """Le texte brut d'un nœud : ses retours à la ligne sont de la mise en page XML, pas du sens."""
    return SPACES.sub(" ", value) if value else ""


def _render(element: ET.Element) -> str:
    tag = element.tag
    if tag == "br":
        return "\n" + _flat(element.tail)
    if tag == "tr":
        cells = [
            _render_children(cell).replace("\n", " ") for cell in element if cell.tag in CELL_TAGS
        ]
        row = " | ".join(SPACES.sub(" ", cell).strip() for cell in cells)
        return "\n" + row + "\n" + _flat(element.tail)
    inner = _render_children(element)
    if tag in BLOCK_TAGS:
        return "\n" + inner + "\n" + _flat(element.tail)
    return inner + _flat(element.tail)


def _render_children(element: ET.Element) -> str:
    return _flat(element.text) + "".join(_render(child) for child in element)


def html_to_text(content: ET.Element | None) -> str:
    """Le texte d'un bloc CONTENU : une ligne par alinéa, une ligne par rangée de tableau."""
    if content is None:
        return ""
    lines = (SPACES.sub(" ", line).strip() for line in _render(content).split("\n"))
    return "\n".join(line for line in lines if line)


# --- Article ------------------------------------------------------------------------------------


def parse_article(xml: bytes) -> LegiArticle:
    root = ET.fromstring(xml)
    meta = root.find("META/META_SPEC/META_ARTICLE")
    if meta is None:
        raise ValueError("article sans META_ARTICLE")
    titles = list(root.iter("TITRE_TM"))
    path = tuple((title.text or "").strip() for title in titles)
    if not path or path[0] not in PARTS:
        raise ValueError(f"racine du plan inconnue : {path[:1]}")
    text_id = root.find("CONTEXTE/TEXTE")
    code = text_id.get("cid") if text_id is not None else None
    cited = tuple(
        link.get("num", "")
        for link in root.iterfind("LIENS/LIEN")
        if link.get("typelien") == "CITATION"
        and link.get("sens") == "source"
        and link.get("cidtexte") == code
    )
    end = meta.findtext("DATE_FIN", OPEN_END)
    return LegiArticle(
        id=root.findtext("META/META_COMMUN/ID", ""),
        num=meta.findtext("NUM", "").strip(),
        state=meta.findtext("ETAT", ""),
        valid_from=date.fromisoformat(meta.findtext("DATE_DEBUT", "")),
        valid_to=None if end == OPEN_END else date.fromisoformat(end),
        path=path,
        section_id=titles[-1].get("id", ""),
        part=PARTS[path[0]],
        text=html_to_text(root.find("BLOC_TEXTUEL/CONTENU")),
        nota=html_to_text(root.find("NOTA/CONTENU")),
        cited_nums=cited,
    )


# --- Sélection ----------------------------------------------------------------------------------


def _in_force(article: LegiArticle, on: date) -> bool:
    if article.state in NEVER_IN_FORCE:
        return False
    return article.valid_from <= on and (article.valid_to is None or on < article.valid_to)


def select_in_force(
    articles: Iterable[LegiArticle], on: date
) -> tuple[list[LegiArticle], list[str]]:
    """Une version par numéro d'article, en vigueur le jour `on`.

    LEGI laisse parfois deux versions ouvertes pour un même numéro : on garde celle qui commence
    le plus tard, et on le signale.
    """
    by_num: dict[str, list[LegiArticle]] = defaultdict(list)
    for article in articles:
        if _in_force(article, on):
            by_num[article.num].append(article)

    kept: list[LegiArticle] = []
    anomalies: list[str] = []
    for num in sorted(by_num):
        candidates = sorted(by_num[num], key=lambda a: (a.valid_from, a.id), reverse=True)
        kept.append(candidates[0])
        if len(candidates) > 1:
            dropped = ", ".join(f"{a.id} (début {a.valid_from})" for a in candidates[1:])
            anomalies.append(
                f"{num} : {len(candidates)} versions en vigueur, conservée {candidates[0].id} "
                f"(début {candidates[0].valid_from}), écartée{'s' if len(candidates) > 2 else ''} "
                f"{dropped}"
            )
    kept.sort(key=lambda a: a.id)
    return kept, anomalies


# --- Extraction ---------------------------------------------------------------------------------


def _iter_article_files(archive: Path, text_id: str) -> Iterator[bytes]:
    marker = f"/{text_id}/article/"
    with tarfile.open(archive, "r|gz") as tar:
        for member in tar:
            if member.isfile() and marker in member.name and member.name.endswith(".xml"):
                handle = tar.extractfile(member)
                if handle is not None:
                    yield handle.read()


def extract(
    archive: Path, out_dir: Path, *, text_id: str = CODE_ID, on: date = STATE_DATE
) -> dict[str, Any]:
    """Écrit `articles.jsonl` dans `out_dir` et renvoie les comptes et les anomalies."""
    versions = [parse_article(xml) for xml in _iter_article_files(archive, text_id)]
    kept, anomalies = select_in_force(versions, on)

    by_num = {article.num: article for article in kept}
    cites_total = unresolved = 0
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "articles.jsonl").open("w", encoding="utf-8") as f:
        for article in kept:
            cites: set[str] = set()
            for num in article.cited_nums:
                if num == article.num:
                    continue
                target = by_num.get(num)
                if target is None:
                    unresolved += 1
                else:
                    cites.add(target.id)
            cites_total += len(cites)
            row = {
                "id": article.id,
                "num": article.num,
                "part": article.part,
                "path": list(article.path),
                "section_id": article.section_id,
                "text": article.text,
                "nota": article.nota,
                "valid_from": article.valid_from.isoformat(),
                "valid_to": article.valid_to.isoformat() if article.valid_to else None,
                "cites": sorted(cites),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "counts": {
            "article_versions_read": len(versions),
            "articles": len(kept),
            "cites": cites_total,
            "unresolved_cites": unresolved,
        },
        "anomalies": anomalies,
    }


# --- Ligne de commande --------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--version", required=True, help="ex. v1")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent / "data")
    parser.add_argument("--expected-sha256", default=ARCHIVE_SHA256)
    args = parser.parse_args(argv)

    version_dir: Path = args.data_dir / args.version
    if version_dir.exists() and any(version_dir.iterdir()):
        sys.exit(f"{version_dir} existe déjà : une version publiée ne se réécrit pas.")
    archive_sha = _sha256(args.archive)
    if archive_sha != args.expected_sha256:
        sys.exit(
            f"empreinte de l'archive inattendue : {archive_sha} (attendue {args.expected_sha256})"
        )

    stats = extract(args.archive, version_dir)
    manifest = {
        "dataset": "droit-consommation/data",
        "version": args.version,
        "extractor": "domains/droit-consommation/consommation_extract.py",
        "source": {
            "archive": args.archive.name,
            "url": SOURCE_BASE_URL + args.archive.name,
            "sha256": archive_sha,
            "licence": LICENCE,
        },
        "text_id": CODE_ID,
        "state_date": STATE_DATE.isoformat(),
        **stats,
        "files": {"articles.jsonl": _sha256(version_dir / "articles.jsonl")},
    }
    (version_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(stats["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
