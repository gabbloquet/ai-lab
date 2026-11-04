import hashlib
import io
import json
import tarfile
from datetime import date
from pathlib import Path

import pytest
from consommation_extract import (
    CODE_ID,
    extract,
    html_to_text,
    main,
    parse_article,
    select_in_force,
)

ON = date(2025, 7, 13)
OPEN_END = "2999-01-01"
LEG = "Partie législative nouvelle"
REG = "Partie réglementaire nouvelle"


def article_xml(
    art_id: str,
    num: str,
    *,
    start: str = "2016-07-01",
    end: str = OPEN_END,
    state: str = "VIGUEUR",
    path: tuple[tuple[str, str], ...] = (
        ("LEGISCTA000000000001", LEG),
        ("LEGISCTA000000000002", "Livre II : CONTRATS"),
    ),
    body: str = "<p>Texte.</p>",
    nota: str = "",
    links: tuple[dict[str, str], ...] = (),
    text_id: str = CODE_ID,
) -> bytes:
    """Un fichier article au format LEGI, réduit aux balises que lit l'extracteur."""
    tm = ""
    for section_id, title in path:
        tm += f'<TM><TITRE_TM fin="{OPEN_END}" id="{section_id}">{title}</TITRE_TM>'
    tm += "</TM>" * len(path)
    lien = '<LIEN cidtexte="{cid}" id="{id}" num="{num}" sens="{sens}" typelien="{type}">x</LIEN>'
    liens = "".join(
        lien.format(**{"cid": CODE_ID, "sens": "source", "type": "CITATION", **link})
        for link in links
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ARTICLE>
<META>
<META_COMMUN><ID>{art_id}</ID><NATURE>Article</NATURE></META_COMMUN>
<META_SPEC><META_ARTICLE>
<NUM>{num}</NUM>
<ETAT>{state}</ETAT>
<DATE_DEBUT>{start}</DATE_DEBUT>
<DATE_FIN>{end}</DATE_FIN>
<TYPE>AUTONOME</TYPE>
</META_ARTICLE></META_SPEC>
</META>
<CONTEXTE><TEXTE cid="{text_id}" nature="CODE">{tm}</TEXTE></CONTEXTE>
<NOTA><CONTENU>{nota}</CONTENU></NOTA>
<BLOC_TEXTUEL><CONTENU>{body}</CONTENU></BLOC_TEXTUEL>
<LIENS>{liens}</LIENS>
</ARTICLE>""".encode()


def member_path(art_id: str, text_id: str = CODE_ID) -> str:
    return (
        "legi/global/code_et_TNC_en_vigueur/code_en_vigueur/LEGI/TEXT/00/00/06/06/95/"
        f"{text_id}/article/LEGI/ARTI/00/00/00/00/00/{art_id}.xml"
    )


def make_archive(directory: Path, members: dict[str, bytes]) -> Path:
    archive = directory / "legi.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return archive


def parse(xml: bytes):
    return parse_article(xml)


# --- Texte des articles -------------------------------------------------------------------------


def test_text_keeps_line_breaks_and_collapses_layout_whitespace() -> None:
    xml = article_xml(
        "LEGIARTI000000000010",
        "L221-18",
        body="<p>\n<br/>Le consommateur   dispose d'un délai de quatorze jours. "
        "<br/>Le délai court : <br/>1° De la conclusion du contrat ;</p>",
    )
    assert parse(xml).text == (
        "Le consommateur dispose d'un délai de quatorze jours.\nLe délai court :\n"
        "1° De la conclusion du contrat ;"
    )


def test_text_keeps_inline_markup_inside_the_line() -> None:
    xml = article_xml("LEGIARTI000000000011", "L1", body="<p>Le 1<sup>er</sup> <b>janvier</b>.</p>")
    assert parse(xml).text == "Le 1er janvier."


def test_text_replaces_non_breaking_spaces() -> None:
    xml = article_xml("LEGIARTI000000000012", "L1", body="<p>1 500 euros</p>")
    assert parse(xml).text == "1 500 euros"


def test_text_renders_table_rows_as_lines_and_cells_with_a_separator() -> None:
    xml = article_xml(
        "LEGIARTI000000000013",
        "L1",
        body=(
            "<div>Tableau ci-après :<br/>"
            "<table><tbody>"
            "<tr><th><br/>ARTICLES <br/></th><th>RÉDACTION</th></tr>"
            "<tr><td>\nL. 311-1\n</td><td><br/>Loi n° 2017-203<br/></td></tr>"
            "</tbody></table></div>"
        ),
    )
    assert parse(xml).text == "Tableau ci-après :\nARTICLES | RÉDACTION\nL. 311-1 | Loi n° 2017-203"


def test_empty_content_gives_empty_text() -> None:
    assert html_to_text(None) == ""


def test_nota_is_kept_apart_from_the_text() -> None:
    xml = article_xml(
        "LEGIARTI000000000014", "L1", body="<p>Corps.</p>", nota="<p>Entre en vigueur en 2017.</p>"
    )
    article = parse(xml)
    assert (article.text, article.nota) == ("Corps.", "Entre en vigueur en 2017.")


# --- Métadonnées --------------------------------------------------------------------------------


def test_metadata_and_plan_path() -> None:
    xml = article_xml(
        "LEGIARTI000000000020",
        "R542-1",
        start="2022-07-04",
        path=(("LEGISCTA000000000101", REG), ("LEGISCTA000000000102", "Livre V : ENQUÊTES")),
    )
    article = parse(xml)
    assert article.id == "LEGIARTI000000000020"
    assert article.num == "R542-1"
    assert article.valid_from == date(2022, 7, 4)
    assert article.valid_to is None
    assert article.path == (REG, "Livre V : ENQUÊTES")
    assert article.section_id == "LEGISCTA000000000102"
    assert article.part == "regulatory"


def test_legislative_part_comes_from_the_root_of_the_plan() -> None:
    assert parse(article_xml("LEGIARTI000000000021", "liminaire")).part == "legislative"


def test_versions_from_before_the_2016_recodification_have_a_part_too() -> None:
    old_leg = parse(
        article_xml("LEGIARTI000000000023", "L121-21", path=(("S1", "Partie législative"),))
    )
    old_reg = parse(
        article_xml("LEGIARTI000000000024", "R1", path=(("S2", "Partie réglementaire"),))
    )
    assert (old_leg.part, old_reg.part) == ("legislative", "regulatory")


def test_unknown_root_of_the_plan_is_rejected() -> None:
    xml = article_xml("LEGIARTI000000000022", "L1", path=(("LEGISCTA1", "Partie arrêtés"),))
    with pytest.raises(ValueError, match="Partie arrêtés"):
        parse(xml)


def test_only_outgoing_citations_to_the_same_code_are_kept() -> None:
    xml = article_xml(
        "LEGIARTI000000000030",
        "L221-18",
        links=(
            {"id": "LEGIARTI000000000031", "num": "L221-23"},
            {"id": "LEGIARTI000000000032", "num": "L221-19", "sens": "cible"},
            {"id": "LEGIARTI000000000033", "num": "L121-21", "type": "CONCORDANCE"},
            {"id": "LEGIARTI000000000034", "num": "Annexe 3-0", "cid": "LEGITEXT000006074069"},
        ),
    )
    assert parse(xml).cited_nums == ("L221-23",)


# --- Versions en vigueur ------------------------------------------------------------------------


def versions(*specs: tuple[str, str, str, str]):
    return [parse(article_xml(i, n, start=s, end=e)) for i, n, s, e in specs]


def test_in_force_window_includes_its_start_day_and_excludes_its_end_day() -> None:
    kept, anomalies = select_in_force(
        versions(
            ("LEGIARTI000000000040", "L1", "2025-07-13", OPEN_END),
            ("LEGIARTI000000000041", "L2", "2016-07-01", "2025-07-13"),
            ("LEGIARTI000000000042", "L3", "2016-07-01", "2025-07-14"),
            ("LEGIARTI000000000043", "L4", "2025-07-14", OPEN_END),
        ),
        on=ON,
    )
    assert [a.id for a in kept] == ["LEGIARTI000000000040", "LEGIARTI000000000042"]
    assert anomalies == []


@pytest.mark.parametrize("state", ["MODIFIE_MORT_NE", "ANNULE"])
def test_versions_that_never_took_effect_are_not_in_force(state: str) -> None:
    stillborn = parse(article_xml("LEGIARTI000000000044", "L5", start="2020-01-01", state=state))
    assert select_in_force([stillborn], on=ON) == ([], [])


def test_two_versions_in_force_for_one_number_keep_the_latest_and_report_it() -> None:
    kept, anomalies = select_in_force(
        versions(
            ("LEGIARTI000000000050", "R542-1", "2021-04-01", OPEN_END),
            ("LEGIARTI000000000051", "R542-1", "2022-07-04", OPEN_END),
        ),
        on=ON,
    )
    assert [a.id for a in kept] == ["LEGIARTI000000000051"]
    assert anomalies == [
        "R542-1 : 2 versions en vigueur, conservée LEGIARTI000000000051 (début 2022-07-04), "
        "écartée LEGIARTI000000000050 (début 2021-04-01)"
    ]


# --- Extraction complète ------------------------------------------------------------------------


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    members = {
        member_path("LEGIARTI000000000101"): article_xml(
            "LEGIARTI000000000101",
            "L221-18",
            body="<p>Quatorze jours, sauf l'article L. 221-28.</p>",
            links=(
                {"id": "LEGIARTI000000000777", "num": "L221-28"},  # version ancienne de la cible
                {"id": "LEGIARTI000000000101", "num": "L221-18"},  # renvoi à soi-même
                {"id": "LEGIARTI000000000888", "num": "L999-1"},  # cible absente
                {"id": "", "num": ""},  # lien sans numéro
            ),
        ),
        member_path("LEGIARTI000000000102"): article_xml("LEGIARTI000000000102", "L221-28"),
        member_path("LEGIARTI000000000103"): article_xml(
            "LEGIARTI000000000103", "L221-28", start="2010-01-01", end="2016-07-01", state="MODIFIE"
        ),
        member_path("LEGIARTI000000000104"): article_xml(
            "LEGIARTI000000000104", "D111-8", path=(("LEGISCTA000000000201", REG),)
        ),
        member_path("LEGIARTI000000000900", "LEGITEXT000006074069"): article_xml(
            "LEGIARTI000000000900", "L1", text_id="LEGITEXT000006074069"
        ),
        "legi/global/code_et_TNC_en_vigueur/code_en_vigueur/LEGI/TEXT/00/00/06/06/95/"
        f"{CODE_ID}/section_ta/LEGI/SCTA/00/00/00/00/00/LEGISCTA000000000001.xml": b"<SECTION_TA/>",
    }
    return make_archive(tmp_path, members)


def test_extract_writes_in_force_articles_of_the_code_only(archive: Path, tmp_path: Path) -> None:
    out = tmp_path / "v1"
    extract(archive, out, on=ON)

    rows = [json.loads(line) for line in (out / "articles.jsonl").read_text().splitlines()]
    assert [r["id"] for r in rows] == [
        "LEGIARTI000000000101",
        "LEGIARTI000000000102",
        "LEGIARTI000000000104",
    ]
    assert rows[0] == {
        "id": "LEGIARTI000000000101",
        "num": "L221-18",
        "part": "legislative",
        "path": [LEG, "Livre II : CONTRATS"],
        "section_id": "LEGISCTA000000000002",
        "text": "Quatorze jours, sauf l'article L. 221-28.",
        "nota": "",
        "valid_from": "2016-07-01",
        "valid_to": None,
        "cites": ["LEGIARTI000000000102"],
    }


def test_citations_resolve_by_number_to_the_version_in_force(archive: Path, tmp_path: Path) -> None:
    out = tmp_path / "v1"
    stats = extract(archive, out, on=ON)

    assert stats["counts"] == {
        "article_versions_read": 4,
        "articles": 3,
        "cites": 1,
        "unresolved_cites": 2,
    }


def test_extract_is_byte_for_byte_reproducible(archive: Path, tmp_path: Path) -> None:
    extract(archive, tmp_path / "a", on=ON)
    extract(archive, tmp_path / "b", on=ON)
    assert (tmp_path / "a" / "articles.jsonl").read_bytes() == (
        tmp_path / "b" / "articles.jsonl"
    ).read_bytes()


# --- Ligne de commande --------------------------------------------------------------------------


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_cli(archive: Path, data_dir: Path, *extra: str) -> None:
    main(
        [
            "--archive",
            str(archive),
            "--version",
            "v1",
            "--data-dir",
            str(data_dir),
            "--expected-sha256",
            sha256(archive),
            *extra,
        ]
    )


def test_cli_writes_a_manifest_with_source_counts_and_file_hashes(
    archive: Path, tmp_path: Path
) -> None:
    run_cli(archive, tmp_path / "data")

    out = tmp_path / "data" / "v1"
    manifest = json.loads((out / "MANIFEST.json").read_text())
    assert manifest["dataset"] == "droit-consommation/data"
    assert manifest["version"] == "v1"
    assert manifest["source"]["archive"] == "legi.tar.gz"
    assert manifest["source"]["sha256"] == sha256(archive)
    assert manifest["text_id"] == CODE_ID
    assert manifest["state_date"] == "2025-07-13"
    assert manifest["counts"]["articles"] == 3
    assert manifest["anomalies"] == []
    assert manifest["files"] == {"articles.jsonl": sha256(out / "articles.jsonl")}


def test_cli_refuses_an_archive_whose_hash_differs(archive: Path, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "--archive",
                str(archive),
                "--version",
                "v1",
                "--data-dir",
                str(tmp_path / "data"),
                "--expected-sha256",
                "0" * 64,
            ]
        )
    assert not (tmp_path / "data" / "v1").exists()


def test_cli_refuses_to_overwrite_a_published_version(archive: Path, tmp_path: Path) -> None:
    run_cli(archive, tmp_path / "data")
    before = (tmp_path / "data" / "v1" / "articles.jsonl").read_bytes()

    with pytest.raises(SystemExit):
        run_cli(archive, tmp_path / "data")

    assert (tmp_path / "data" / "v1" / "articles.jsonl").read_bytes() == before
