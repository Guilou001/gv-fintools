"""Le client de barres : ses conversions, son cache, et le fait qu'il ne parte jamais sans clé.

Aucun test ne touche le réseau. Le téléchargement est remplacé par une réponse fabriquée, et ce qui
est vérifié est ce que le module en fait : la forme de la table, la pagination, le cache, et le refus
de travailler sans identifiant.
"""

from __future__ import annotations

import os

import pytest

from gvf import marches
from gvf.marches import Requete


@pytest.fixture(autouse=True)
def sans_cles(monkeypatch, tmp_path):
    """Un environnement propre : aucune clé, aucun fichier de clés à portée."""
    for nom in ("ALPACA_KEY_ID", "ALPACA_SECRET_KEY", "POLYGON_API_KEY"):
        monkeypatch.delenv(nom, raising=False)
    monkeypatch.setattr(marches, "FICHIER_DE_CLES", tmp_path / "absent.env")


def test_le_module_refuse_de_partir_sans_cle(tmp_path):
    """Mieux vaut une erreur claire qu'une requête qui part et revient vide."""
    with pytest.raises(RuntimeError, match="ALPACA_KEY_ID"):
        marches.barres_alpaca(Requete("QQQ", "2026-01-05", "2026-01-05"), cache=tmp_path)
    with pytest.raises(RuntimeError, match="POLYGON_API_KEY"):
        marches.barres_polygon(Requete("QQQ", "2026-01-05", "2026-01-05"), cache=tmp_path)


def test_le_fichier_de_cles_ne_recouvre_pas_l_environnement(monkeypatch, tmp_path):
    """Une clé déjà posée dans l'environnement l'emporte : c'est ce qui permet d'en passer une
    autre en intégration continue sans toucher au fichier de l'utilisateur."""
    fichier = tmp_path / "cles.env"
    fichier.write_text(
        "# un commentaire\nPOLYGON_API_KEY=du_fichier\nALPACA_KEY_ID=aussi\n", encoding="utf-8"
    )
    monkeypatch.setenv("POLYGON_API_KEY", "deja_pose")
    marches.charger_les_cles(fichier)
    assert os.environ["POLYGON_API_KEY"] == "deja_pose"
    assert os.environ["ALPACA_KEY_ID"] == "aussi"


def test_le_nom_de_fichier_distingue_les_deux_flux():
    """Le flux fait partie de l'identité du fichier. Sans cela, une table IEX servirait de réponse
    à une demande de consolidé, et le volume serait faux d'un facteur soixante."""
    consolide = Requete("QQQ", "2026-01-05", "2026-01-09", flux="sip")
    iex = Requete("QQQ", "2026-01-05", "2026-01-09", flux="iex")
    assert consolide.nom_de_fichier("alpaca") != iex.nom_de_fichier("alpaca")
    assert "sip" in consolide.nom_de_fichier("alpaca")


def test_la_table_porte_les_colonnes_attendues():
    lignes = [
        {"t": "2026-01-05T14:30:00Z", "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 100, "n": 7, "vw": 1.4}
    ]
    table = marches._en_table(
        lignes,
        {
            "t": "horodatage",
            "o": "ouverture",
            "h": "haut",
            "l": "bas",
            "c": "cloture",
            "v": "volume",
            "n": "transactions",
            "vw": "prix_moyen",
        },
    )
    assert list(table.columns) == [
        "horodatage",
        "ouverture",
        "haut",
        "bas",
        "cloture",
        "volume",
        "transactions",
        "prix_moyen",
    ]
    assert float(table["cloture"].iloc[0]) == 1.5


def test_une_table_vide_garde_ses_colonnes():
    """Un jour férié rend zéro barre. Le reste du code doit pouvoir concaténer sans se soucier du
    cas, donc la table vide porte quand même son schéma."""
    table = marches._en_table([], {})
    assert len(table) == 0
    assert "horodatage" in table.columns


def test_les_colonnes_absentes_de_la_source_sont_comblees():
    """Le nombre de transactions et le prix moyen manquent selon la source et le flux. Ils doivent
    exister quand même, à valeur manquante, pour que le schéma soit le même partout."""
    lignes = [{"t": "2026-01-05T14:30:00Z", "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 100}]
    table = marches._en_table(
        lignes, {"t": "horodatage", "o": "ouverture", "h": "haut", "l": "bas", "c": "cloture", "v": "volume"}
    )
    assert table["transactions"].isna().all()


def test_la_table_est_triee_dans_le_temps():
    lignes = [
        {"t": "2026-01-05T14:32:00Z", "o": 1, "h": 1, "l": 1, "c": 3, "v": 1},
        {"t": "2026-01-05T14:30:00Z", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1},
    ]
    table = marches._en_table(
        lignes, {"t": "horodatage", "o": "ouverture", "h": "haut", "l": "bas", "c": "cloture", "v": "volume"}
    )
    assert list(table["cloture"]) == [1, 3]


def test_le_cache_evite_le_reseau(monkeypatch, tmp_path):
    """Une fois la table sur le disque, aucune requête ne repart. C'est ce qui rend une étude
    reproductible sans dépendre du fournisseur ni du débit."""
    monkeypatch.setenv("ALPACA_KEY_ID", "essai")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "essai")
    appels = {"n": 0}

    def fausse_reponse(url, entetes, essais=4):
        appels["n"] += 1
        return {
            "bars": {
                "QQQ": [
                    {
                        "t": "2026-01-05T14:30:00Z",
                        "o": 1,
                        "h": 2,
                        "l": 0.5,
                        "c": 1.5,
                        "v": 100,
                        "n": 7,
                        "vw": 1.4,
                    }
                ]
            },
            "next_page_token": None,
        }

    monkeypatch.setattr(marches, "_lire_json", fausse_reponse)
    r = Requete("QQQ", "2026-01-05", "2026-01-05")
    premiere = marches.barres_alpaca(r, cache=tmp_path)
    seconde = marches.barres_alpaca(r, cache=tmp_path)
    assert appels["n"] == 1
    assert len(premiere) == len(seconde) == 1


def test_la_pagination_va_jusqu_au_bout(monkeypatch, tmp_path):
    """Alpaca rend au plus dix mille barres par page. Une étude qui s'arrêterait à la première page
    perdrait la fin de sa fenêtre sans que rien ne le signale."""
    monkeypatch.setenv("ALPACA_KEY_ID", "essai")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "essai")
    pages = [
        {
            "bars": {"QQQ": [{"t": "2026-01-05T14:30:00Z", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1}]},
            "next_page_token": "suite",
        },
        {
            "bars": {"QQQ": [{"t": "2026-01-05T14:31:00Z", "o": 1, "h": 1, "l": 1, "c": 2, "v": 1}]},
            "next_page_token": None,
        },
    ]
    monkeypatch.setattr(marches, "_lire_json", lambda *a, **k: pages.pop(0))
    table = marches.barres_alpaca(Requete("QQQ", "2026-01-05", "2026-01-05"), cache=tmp_path)
    assert len(table) == 2


def test_la_part_du_volume_se_calcule_et_refuse_un_denominateur_nul():
    import pandas as pd

    consolide = pd.DataFrame({"volume": [600.0, 400.0]})
    iex = pd.DataFrame({"volume": [10.0, 6.0]})
    assert marches.part_du_volume(consolide, iex) == pytest.approx(0.016)
    with pytest.raises(ValueError):
        marches.part_du_volume(pd.DataFrame({"volume": [0.0]}), iex)


def test_la_source_inconnue_est_refusee():
    with pytest.raises(ValueError):
        marches.barres("databento", Requete("QQQ", "2026-01-05", "2026-01-05"))


def test_les_profondeurs_mesurees_sont_declarees():
    """Un appelant doit pouvoir savoir ce qu'il peut demander avant de le demander."""
    assert marches.PROFONDEUR[("alpaca", "sip")].startswith("2016")
    assert marches.PROFONDEUR[("alpaca", "iex")].startswith("2020")


def test_l_ajustement_fait_partie_de_l_identite_du_fichier():
    """Le piège mesuré le 2026-08-30 : les prix bruts des deux fournisseurs coïncident exactement,
    leurs prix ajustés diffèrent de onze points de base parce que l'un applique le dividende et
    l'autre non. Servir une table ajustée à une demande de brut poserait donc une marche dans la
    série à chaque détachement."""
    brut = Requete("QQQ", "2026-06-01", "2026-06-30", ajustement="brut")
    ajuste = Requete("QQQ", "2026-06-01", "2026-06-30", ajustement="ajuste")
    assert brut.nom_de_fichier("alpaca") != ajuste.nom_de_fichier("alpaca")
    assert "brut" in brut.nom_de_fichier("polygon")


def test_le_brut_est_le_defaut():
    """C'est le seul mode sur lequel les deux fournisseurs s'accordent, donc le seul qui permette
    de mêler les deux sources sans y poser un décalage."""
    assert Requete("QQQ", "2026-06-01", "2026-06-30").ajustement == "brut"


def test_un_flux_ou_un_ajustement_inconnu_est_refuse():
    with pytest.raises(ValueError, match="flux"):
        Requete("QQQ", "2026-06-01", "2026-06-30", flux="nasdaq")
    with pytest.raises(ValueError, match="ajustement"):
        Requete("QQQ", "2026-06-01", "2026-06-30", ajustement="peut-etre")


def test_les_horodatages_en_millisecondes_sont_lus_avant_le_tri():
    """Le défaut qui a existé : Polygon horodate en millisecondes depuis l'époque. Lus comme des
    nanosecondes, ils donnaient des dates de 1970 dans le désordre, et le tri appariait ensuite les
    prix aux mauvaises minutes. Un tiers des barres se retrouvait décalé, et aucun test de forme ne
    le voyait : la table avait le bon nombre de lignes et les bonnes colonnes."""
    import pandas as pd

    lignes = [
        {"t": 1781000160000, "o": 1, "h": 1, "l": 1, "c": 2.0, "v": 1},
        {"t": 1781000100000, "o": 1, "h": 1, "l": 1, "c": 1.0, "v": 1},
    ]
    table = marches._en_table(
        lignes, {"t": "horodatage", "o": "ouverture", "h": "haut", "l": "bas", "c": "cloture", "v": "volume"}
    )
    assert list(table["cloture"]) == [1.0, 2.0]
    assert table["horodatage"].iloc[0].year > 2000
    assert (table["horodatage"].iloc[1] - table["horodatage"].iloc[0]) == pd.Timedelta(minutes=1)
