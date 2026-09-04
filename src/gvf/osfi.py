"""Les relevés que les institutions financières déposent au BSIF, chargés une fois pour toutes.

**Pourquoi ce module existe.** Le Bureau du surintendant des institutions financières publie sur le
portail du gouvernement ouvert, institution par institution et période par période, ce que chaque
banque, société de fiducie ou assureur lui déclare. Plusieurs dépôts du portefeuille lisent les mêmes
fichiers. Recopier le chargeur dans chacun ferait vivre le même code à plusieurs endroits, et le
portail a déjà rendu un relevé inactif au premier trimestre de 2024 : le jour où une adresse change,
il vaut mieux n'avoir qu'un endroit à corriger.

**Ce que le module fait.** Il télécharge un relevé, le range dans un entrepôt DuckDB, et pose au
dessus des vues aux noms français dont les colonnes sont utilisables. Il ne calcule rien : le sens de
chaque poste appartient au dépôt qui s'en sert.

**Trois pièges que le module désamorce.**

Le premier est l'**unité de temps**. Les relevés trimestriels portent un exercice et un trimestre
fiscaux ; les relevés mensuels portent une année et un mois civils. Les deux ne se joignent pas
directement, et le portail ne publie pas la date de clôture d'exercice de chaque institution.

Le deuxième est le **type des identifiants**. Le numéro d'institution et l'adresse de point de donnée
sont des identifiants, pas des quantités. Sans forçage, un fichier dont tous les codes seraient
numériques se lirait en nombres, « 0488 » deviendrait 488, et toutes les recherches par code
échoueraient sans rien signaler.

Le troisième est le **nom des colonnes**, qui porte les deux langues séparées par une barre oblique.
Les citer tels quels dans chaque requête est illisible ; les vues les renomment une fois.

Licence des données : licence du gouvernement ouvert du Canada, usage et redistribution permis avec
attribution. Ce module ne redistribue rien, il télécharge.
"""

from __future__ import annotations

import ssl
import urllib.request
from dataclasses import dataclass
from pathlib import Path

AGENT = "Guillaume Vaudescal 88989051+Guilou001@users.noreply.github.com"
PORTAIL = "https://open.canada.ca/data/dataset"

# Les jeux du BSIF, par famille d'institution.
JEU_BANQUES = "91ed76b4-a1a2-4f87-9c4c-59cd64f7a9de"
JEU_SUCCURSALES_ETRANGERES = "c6879faf-2bc7-4c84-999c-0626ae33ec84"


@dataclass(frozen=True)
class Releve:
    """Un relevé du BSIF : son nom court, son fichier, sa ressource, sa périodicité, sa taille.

    `octets` est la taille mesurée au 30 août 2026. Elle ne sert pas à vérifier l'intégrité, ce que
    seule une empreinte ferait, mais à décider si un fichier déjà sur le disque est complet.
    """

    cle: str
    fichier: str
    ressource: str
    periodicite: str  # « trimestriel » ou « mensuel »
    octets: int
    quoi: str
    jeu: str = JEU_BANQUES

    @property
    def url(self) -> str:
        return f"{PORTAIL}/{self.jeu}/resource/{self.ressource}/download/{self.fichier}"


BANQUES = {
    "p3": Releve(
        "p3",
        "banks_quarterly_p3.csv",
        "027ee7f8-4b87-45cd-a10f-f95d3a5d4e09",
        "trimestriel",
        230_496_088,
        "compte de résultat consolidé, en cumul depuis le début de l'exercice",
    ),
    "ba": Releve(
        "ba",
        "banks_quarterly_ba.csv",
        "fe7617f7-a676-4966-aae3-c4cfbab4b935",
        "trimestriel",
        149_615_442,
        "normes de fonds propres de Bâle III",
    ),
    "e3": Releve(
        "e3",
        "banks_quarterly_e3.csv",
        "1f86e088-7d29-49c2-94de-ddbfe6559725",
        "trimestriel",
        0,
        "provisions pour pertes de crédit attendues",
    ),
    "lr": Releve(
        "lr",
        "banks_quarterly_lr.csv",
        "817d4005-aa4a-4c4f-9dad-6ce7eca40700",
        "trimestriel",
        0,
        "exigences de levier",
    ),
    "m4": Releve(
        "m4",
        "banks_monthly_m4.csv",
        "d0f6040e-671c-4301-a235-e9e7ba164604",
        "mensuel",
        748_730_698,
        "bilan consolidé",
    ),
}


def _contexte() -> ssl.SSLContext:
    """Le magasin de certificats du système, faute de quoi Python échoue là où curl passe."""
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:  # pragma: no cover - dépend de l'environnement
        return ssl.create_default_context()


def telecharger(releve: Releve, racine: Path | str = Path("data/raw"), force: bool = False) -> Path:
    """Un relevé sur le disque. Un fichier déjà présent et de taille plausible n'est pas repris."""
    racine = Path(racine)
    racine.mkdir(parents=True, exist_ok=True)
    dest = racine / releve.fichier
    if dest.exists() and not force and dest.stat().st_size > releve.octets // 2:
        return dest
    requete = urllib.request.Request(releve.url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(requete, context=_contexte(), timeout=1800) as reponse:
        dest.write_bytes(reponse.read())
    return dest


def tout_telecharger(releves, racine: Path | str = Path("data/raw"), force: bool = False) -> dict[str, Path]:
    return {r.cle: telecharger(r, racine, force) for r in releves}


# Les identifiants sont forcés en texte à la lecture. Voir le troisième piège en tête de module : le
# faire après coup ne rendrait plus le zéro de tête d'un code comme « 0488 ».
TYPES_FORCES = {"Id": "VARCHAR", "Data Point Address/Adresse de point de donnée": "VARCHAR"}

_COLONNES_COMMUNES = """       CAST("Id" AS VARCHAR) AS institution,
       "Total All Banks/Total Industry Groups/FIs" AS nom,
       "Industry Group" AS groupe,
       "Data Point Address/Adresse de point de donnée" AS poste,
       "Data Point Address Label" AS libelle,
       "Measure Value/Valeur de mesure" AS valeur"""

_VUE_TRIMESTRIELLE = f"""
CREATE OR REPLACE VIEW {{vue}} AS
SELECT CAST("Fiscal Year/Année fiscale" AS INTEGER) AS exercice,
       CAST(substr("Fiscal Quarter", 2, 1) AS INTEGER) AS trimestre,
{_COLONNES_COMMUNES}
FROM {{table}}
WHERE "Measure Value/Valeur de mesure" IS NOT NULL
"""

_VUE_MENSUELLE = f"""
CREATE OR REPLACE VIEW {{vue}} AS
SELECT "Calendar Month/Mois civil" AS fin_de_mois,
{_COLONNES_COMMUNES}
FROM {{table}}
WHERE "Measure Value/Valeur de mesure" IS NOT NULL
"""


def construire_entrepot(
    releves,
    vues: dict[str, str],
    racine: Path | str = Path("data/raw"),
    entrepot: Path | str = Path("data/osfi.duckdb"),
):
    """L'entrepôt DuckDB, une table par relevé, et les vues que l'appelant nomme.

    `vues` associe le nom de la vue à la clé du relevé qu'elle expose, par exemple
    `{"resultat": "p3", "bilan": "m4"}`. Le nom français appartient au dépôt qui s'en sert : le même
    relevé P3 s'appelle « resultat » dans un dépôt de rentabilité et « produits » dans un autre.
    """
    import duckdb

    racine, entrepot = Path(racine), Path(entrepot)
    entrepot.parent.mkdir(parents=True, exist_ok=True)
    co = duckdb.connect(str(entrepot))
    par_cle = {r.cle: r for r in releves}
    for releve in releves:
        chemin = racine / releve.fichier
        if not chemin.exists():
            raise FileNotFoundError(f"{chemin} manque : télécharger le relevé d'abord")
        co.execute(f"""
            CREATE OR REPLACE TABLE {releve.cle} AS
            SELECT * FROM read_csv_auto('{chemin.as_posix()}', header=true, sample_size=-1,
                types={TYPES_FORCES!r})""")
    for vue, cle in vues.items():
        releve = par_cle[cle]
        gabarit = _VUE_MENSUELLE if releve.periodicite == "mensuel" else _VUE_TRIMESTRIELLE
        co.execute(gabarit.format(vue=vue, table=releve.cle))
    return co


def ouvrir(entrepot: Path | str = Path("data/osfi.duckdb"), lecture_seule: bool = True):
    """L'entrepôt déjà construit."""
    import duckdb

    entrepot = Path(entrepot)
    if not entrepot.exists():
        raise FileNotFoundError(f"{entrepot} manque : construire l'entrepôt d'abord")
    return duckdb.connect(str(entrepot), read_only=lecture_seule)


def mesurer(co, vues: list[str]) -> dict[str, int]:
    """Ce que l'entrepôt contient, compté plutôt qu'annoncé."""
    mesures: dict[str, int] = {}
    for vue in vues:
        mesures[f"lignes_{vue}"] = co.execute(f"SELECT count(*) FROM {vue}").fetchone()[0]
        mesures[f"postes_{vue}"] = co.execute(f"SELECT count(DISTINCT poste) FROM {vue}").fetchone()[0]
    mesures["lignes_total"] = sum(v for k, v in mesures.items() if k.startswith("lignes_"))
    mesures["institutions"] = co.execute(f"SELECT count(DISTINCT institution) FROM {vues[0]}").fetchone()[0]
    return mesures


def noms_courants(co, vue: str) -> dict[str, str]:
    """Le nom que chaque institution porte à son dernier dépôt.

    Une banque change de nom : la Pacific & Western est devenue VersaBank, l'ING Bank of Canada est
    devenue Tangerine. Prendre un nom au hasard dans l'histoire afficherait des banques disparues.
    """
    colonnes = [c[0] for c in co.execute(f"DESCRIBE {vue}").fetchall()]
    ordre = "exercice DESC, trimestre DESC" if "exercice" in colonnes else "fin_de_mois DESC"
    return dict(
        co.execute(f"""
        SELECT institution, nom FROM (
          SELECT institution, nom,
                 row_number() OVER (PARTITION BY institution ORDER BY {ordre}) AS rang
          FROM {vue})
        WHERE rang = 1""").fetchall()
    )
