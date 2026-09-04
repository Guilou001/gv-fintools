"""Le traducteur vérifié sans réseau : échappement, structures, et compilation d'un document entier."""

from pathlib import Path

import pytest

from gvf.markdown import chaine, convertir, echapper, ligne


def test_les_caracteres_speciaux_de_typst_sont_neutralises():
    """Sans cela, un dièse ou une étoile du texte deviendrait une instruction."""
    assert echapper("#set page") == "\\#set page"
    assert echapper("a * b") == "a \\* b"
    assert echapper("100 $ par mois") == "100 \\$ par mois"


def test_une_chaine_litterale_emploie_les_guillemets_droits():
    """Typst refuse l'apostrophe simple comme délimiteur : c'est l'erreur qui a fait échouer la
    première version du générateur."""
    assert chaine('a"b') == '"a\\"b"'
    assert chaine("c:\\dossier") == '"c:\\\\dossier"'
    assert chaine("deux\nlignes") == '"deux\\nlignes"'


def test_le_gras_l_italique_et_le_code_sont_traduits():
    assert ligne("un **mot** gras") == "un *mot* gras"
    assert ligne("un *mot* italique") == "un _mot_ italique"
    assert ligne("du `code` en ligne") == 'du #raw("code") en ligne'


def test_un_lien_garde_son_adresse_et_echappe_son_libelle():
    assert ligne("[le dépôt](https://exemple.org/a_b)") == '#link("https://exemple.org/a_b")[le dépôt]'


def test_le_titre_de_niveau_un_devient_le_titre_du_document():
    document = convertir("# Mon titre\n\nUn paragraphe.\n")
    assert document.titre == "Mon titre"
    assert "Mon titre" not in document.corps
    assert "Un paragraphe." in document.corps


def test_les_ecussons_distants_sont_retires_et_les_figures_gardees():
    """La distinction qui a manqué à la première version : une image distante est un écusson d'état,
    une image relative est une figure du dépôt."""
    source = (
        "# T\n\n[![ci](https://exemple.org/badge.svg)](https://exemple.org/ci)\n"
        "![python](https://img.shields.io/badge/x-y-blue)\n\n"
        "![Une figure](results/figures/a.png)\n"
    )
    corps = convertir(source, racine="..").corps
    assert "img.shields.io" not in corps and "badge.svg" not in corps
    assert 'image("../results/figures/a.png"' in corps


def test_un_tableau_devient_une_table_avec_son_entete():
    source = "# T\n\n| A | B |\n|---|---:|\n| 1 | 2 |\n| 3 | 4 |\n"
    corps = convertir(source).corps
    assert "#table(" in corps and "columns: 2" in corps
    assert "[*A*]" in corps and "[1]" in corps and "[4]" in corps


def test_une_citation_devient_un_bloc_cite():
    corps = convertir("# T\n\n> Une phrase citée.\n> Sa suite.\n").corps
    assert "#quote(block: true)[Une phrase citée. Sa suite.]" in corps


def test_un_bloc_details_devient_une_section_sans_balises_html():
    source = "# T\n\n<details>\n<summary>Résumé en anglais</summary>\n\nAn English summary.\n\n</details>\n"
    corps = convertir(source).corps
    assert "== Résumé en anglais" in corps
    assert "An English summary." in corps
    assert "<details>" not in corps and "</details>" not in corps


def test_les_listes_rattachent_leurs_continuations():
    source = "# T\n\n1. Premier élément\n   qui continue.\n2. Deuxième.\n"
    corps = convertir(source).corps
    assert "+ Premier élément qui continue." in corps
    assert "+ Deuxième." in corps


def test_un_bloc_de_code_garde_sa_langue():
    corps = convertir("# T\n\n```bash\nuv run x\n```\n").corps
    assert 'lang: "bash"' in corps and "uv run x" in corps


def test_un_document_complet_se_compile(tmp_path):
    """Le test qui compte : le Typst engendré doit passer le compilateur, pas seulement ressembler
    à du Typst."""
    from gvf.rapport import engendrer

    depot = tmp_path / "essai"
    depot.mkdir()
    (depot / "README.md").write_text(
        "# Un titre avec un # et une * étoile\n\n"
        "Un paragraphe avec du **gras**, du `code`, et un [lien](https://exemple.org).\n\n"
        "## Une section\n\n> Une citation de 2021.\n\n| A | B |\n|---|---:|\n| 1 | 2 |\n\n"
        "```python\nprint('bonjour')\n```\n\n- une puce\n- une autre\n"
    )
    chemin = engendrer(depot, date="2026-08-29")
    assert chemin.exists() and chemin.stat().st_size > 1000
    pypdf = pytest.importorskip("pypdf")
    texte = "".join(p.extract_text() or "" for p in pypdf.PdfReader(chemin).pages)
    assert "Une section" in texte
    assert "Une citation de 2021" in texte
    # le tableau doit être DANS le PDF, et pas seulement dans le Typst. La version 0.1 enfermait la
    # table dans un par(), ce que Typst 0.15 traite en la supprimant sans lever d'erreur : les
    # rapports se compilaient, et leurs tableaux étaient vides.
    for cellule in ("A", "B", "1", "2"):
        assert cellule in texte, f"cellule {cellule!r} absente du PDF : la table n'est pas rendue"


def test_un_depot_sans_readme_est_refuse(tmp_path):
    from gvf.rapport import engendrer

    with pytest.raises(FileNotFoundError):
        engendrer(tmp_path)


def test_le_depot_est_lu_dans_la_configuration_de_git(tmp_path):
    from gvf.rapport import _depot_de

    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/Guilou001/exemple.git\n'
    )
    assert _depot_de(tmp_path) == "https://github.com/Guilou001/exemple"
    assert _depot_de(Path(tmp_path / "vide")) == "https://github.com/Guilou001"
