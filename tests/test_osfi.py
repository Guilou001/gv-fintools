"""Le chargeur des relevés du BSIF, éprouvé sur des fichiers de deux lignes au format du portail."""

from __future__ import annotations

import datetime as dt

import pytest

from gvf import osfi

ENTETE_TRIMESTRIEL = (
    '"Fiscal Year/Année fiscale","Fiscal Quarter","Trimestre fiscal","Id",'
    '"Total All Banks/Total Industry Groups/FIs","Total Banques/Total des groupe sectoriel/IFFs",'
    '"Industry Group","Groupe Sectoriel","Return/Relevé","Return Title","Titre du relevé",'
    '"Data Point Address/Adresse de point de donnée","Data Point Address Label",'
    "\"Libellé de l'adresse du point de données\",\"FI Inactive Date/Date d'inactivité IFF\","
    '"Measure Value/Valeur de mesure"')
ENTETE_MENSUEL = (
    '"Calendar Year/Année civile","Calendar Month/Mois civil","Id",'
    '"Total All Banks/Total Industry Groups/FIs","Total Banques/Total des groupe sectoriel/IFFs",'
    '"Industry Group","Groupe Sectoriel","Return/Relevé","Return Title","Titre du relevé",'
    '"Data Point Address/Adresse de point de donnée","Data Point Address Label",'
    "\"Libellé de l'adresse du point de données\",\"FI Inactive Date/Date d'inactivité IFF\","
    '"Measure Value/Valeur de mesure"')


@pytest.fixture
def racine(tmp_path):
    """Deux fichiers minuscules, un trimestriel et un mensuel, au format exact du portail.

    Le code du poste porte un zéro de tête : c'est lui qui prouve que le forçage de type marche.
    """
    d = tmp_path / "raw"
    d.mkdir()
    (d / osfi.BANQUES["p3"].fichier).write_text(
        f'{ENTETE_TRIMESTRIEL}\n'
        '"2025","Q4 - 2025","T4 - 2025","27997","Banque Royale","Banque Royale","Domestic Banks",'
        '"Banques nationales","P3","t","t","8408","revenu net","revenu net","9999-12-31","1234.00"\n'
        '"2024","Q4 - 2024","T4 - 2024","27997","Ancien nom","Ancien nom","Domestic Banks",'
        '"Banques nationales","P3","t","t","0488","autre","autre","9999-12-31","99.00"\n',
        encoding="utf-8")
    (d / osfi.BANQUES["m4"].fichier).write_text(
        f'{ENTETE_MENSUEL}\n'
        '"2025","2025-10-31","27997","Banque Royale","Banque Royale","Domestic Banks",'
        '"Banques nationales","M4","t","t","1045","actif","actif","9999-12-31","5678.00"\n',
        encoding="utf-8")
    return d


@pytest.fixture
def entrepot(racine, tmp_path):
    return osfi.construire_entrepot(
        [osfi.BANQUES["p3"], osfi.BANQUES["m4"]],
        vues={"resultat": "p3", "bilan": "m4"},
        racine=racine, entrepot=tmp_path / "essai.duckdb")


def test_la_vue_trimestrielle_porte_l_exercice_et_le_trimestre(entrepot):
    ligne = entrepot.execute("""SELECT institution, exercice, trimestre, poste, valeur
                                FROM resultat WHERE poste = '8408'""").fetchone()
    assert ligne == ("27997", 2025, 4, "8408", 1234.0)


def test_la_vue_mensuelle_porte_une_date(entrepot):
    ligne = entrepot.execute("SELECT institution, fin_de_mois, valeur FROM bilan").fetchone()
    assert ligne == ("27997", dt.date(2025, 10, 31), 5678.0)


def test_l_identifiant_reste_du_texte(entrepot):
    """Sans forçage, le numéro d'institution deviendrait un entier et toute comparaison avec la
    chaîne « 27997 » échouerait sans rien signaler."""
    valeur = entrepot.execute("SELECT institution FROM resultat LIMIT 1").fetchone()[0]
    assert isinstance(valeur, str)


def test_le_zero_de_tete_d_un_code_est_conserve(entrepot):
    """C'est le piège que le forçage de type existe pour éviter : lu en nombre, « 0488 » devient
    488, et le dépôt qui cherche « 0488 » ne trouve rien tout en continuant de tourner."""
    postes = {p for (p,) in entrepot.execute("SELECT DISTINCT poste FROM resultat").fetchall()}
    assert "0488" in postes


def test_le_nom_retenu_est_celui_du_dernier_depot(entrepot):
    """Le fichier porte « Ancien nom » en 2024 et « Banque Royale » en 2025 : c'est le second qui
    doit sortir, sans quoi les figures afficheraient des banques qui n'existent plus."""
    assert osfi.noms_courants(entrepot, "resultat") == {"27997": "Banque Royale"}


def test_la_mesure_compte_ce_qu_il_y_a(entrepot):
    mesures = osfi.mesurer(entrepot, ["resultat", "bilan"])
    assert mesures["lignes_resultat"] == 2
    assert mesures["lignes_bilan"] == 1
    assert mesures["lignes_total"] == 3
    assert mesures["institutions"] == 1


def test_un_fichier_absent_est_signale(tmp_path):
    with pytest.raises(FileNotFoundError):
        osfi.construire_entrepot([osfi.BANQUES["p3"]], vues={"resultat": "p3"},
                                 racine=tmp_path, entrepot=tmp_path / "x.duckdb")


def test_l_adresse_de_telechargement_se_compose_du_jeu_et_de_la_ressource():
    releve = osfi.BANQUES["p3"]
    assert releve.url.startswith(osfi.PORTAIL)
    assert releve.jeu in releve.url
    assert releve.ressource in releve.url
    assert releve.url.endswith(releve.fichier)


def test_chaque_releve_declare_une_periodicite_connue():
    for releve in osfi.BANQUES.values():
        assert releve.periodicite in ("trimestriel", "mensuel")
