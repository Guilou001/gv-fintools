"""Les barres de marché intrajournalières, téléchargées une fois et gardées sur le disque.

**Pourquoi ce module existe.** Trois dépôts du portefeuille travaillent sur des barres d'une minute :
la réplication du signal VWAP, le momentum d'indice de la dernière demi-heure, et la comparaison du
flux IEX au flux consolidé. Ils lisent les mêmes symboles sur les mêmes fenêtres. Recopier le
téléchargement dans chacun ferait vivre trois fois le même code, trois fois la même gestion de
pagination et trois fois le même risque de laisser filtrer une clé.

**Ce que le module fait.** Il télécharge des barres chez deux fournisseurs derrière une seule
interface, les range en Parquet sur le disque, et ne redemande jamais ce qu'il a déjà. Il ne calcule
rien : le sens des barres appartient au dépôt qui s'en sert.

**Les clés ne sont jamais dans le code.** Elles se lisent dans l'environnement, ou dans un fichier
local que l'appelant désigne. Aucune valeur par défaut, aucune clé écrite en dur, et le module refuse
de travailler plutôt que de partir sans identifiant.

**Deux flux, deux profondeurs.** Mesuré le 30 août 2026 sur un compte simulé gratuit : le flux
consolidé remonte à **janvier 2016**, le flux IEX à **août 2020** seulement. Et IEX ne capte qu'une
part minuscule de l'activité : sur QQQ en juin 2026, 19 976 963 actions contre 1 104 221 836 au
consolidé, soit **1,81 %**, et il manque 57 % des minutes, faute d'y avoir vu une transaction. Un
travail qui calculerait un prix moyen pondéré par les volumes sur le seul flux IEX le calculerait
donc sur un cinquantième du marché, ce qui est le sujet d'un des trois dépôts.

**Le piège de l'ajustement, mesuré.** Les deux fournisseurs proposent un prix « ajusté », et ils
n'entendent pas la même chose. Sur QQQ en juin 2026 : leurs prix **bruts coïncident exactement**,
écart médian de zéro au centième de cent. Leurs prix ajustés diffèrent de **0,79 dollar**, soit onze
points de base, et cet écart tombe à zéro pile le 22 juin. C'est la date de détachement du dividende
trimestriel : Alpaca l'applique, Polygon non, son ajustement ne portant que sur les divisions
d'actions. Mélanger les deux sources en mode ajusté poserait donc une marche de onze points de base
dans la série à chaque trimestre, ce qui est fatal à une étude qui mesure des rendements de quelques
points de base. Le module demande donc du **brut par défaut**, et l'ajustement fait partie de
l'identité du fichier mis en cache.

**Ce sur quoi les deux fournisseurs s'accordent, et ce sur quoi ils divergent.** En brut, sur les
19 875 barres d'une minute de QQQ en juin 2026 : les prix de clôture coïncident sur **la totalité**
des barres, au dixième de cent près, écart maximal d'un centième de cent. Les **volumes**, eux,
diffèrent : Alpaca en déclare **3,45 % de plus** que Polygon sur exactement les mêmes barres. Une
étude de prix peut donc prendre l'un ou l'autre indifféremment ; une étude de volume, non, et un prix
moyen pondéré par les volumes tombe entre les deux.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

CACHE = Path("data/marches")
FICHIER_DE_CLES = Path.home() / ".config" / "marches" / "cles.env"

# Les profondeurs mesurées le 2026-08-30, pour qu'un appelant sache ce qu'il peut demander avant de
# demander. Elles bougent : le flux IEX est une fenêtre glissante.
PROFONDEUR = {
    ("alpaca", "sip"): "2016-01-04",
    ("alpaca", "iex"): "2020-08-01",
    ("polygon", None): "deux ans glissants",
}


def charger_les_cles(fichier: Path | None = None) -> None:
    """Les clés d'un fichier local versées dans l'environnement, si le fichier existe.

    Le fichier n'est jamais lu depuis un dépôt : il vit dans le répertoire de configuration de
    l'utilisateur, avec des droits de lecture pour lui seul. Une clé déjà présente dans
    l'environnement n'est pas écrasée, ce qui permet de la passer autrement en intégration continue.
    """
    # le chemin se résout à l'appel et non à la définition : lier le défaut au chargement du
    # module rendrait la variable impossible à remplacer, y compris dans un test
    fichier = Path(fichier) if fichier is not None else FICHIER_DE_CLES
    if not fichier.exists():
        return
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, valeur = ligne.split("=", 1)
        os.environ.setdefault(cle.strip(), valeur.strip())


def _cle(nom: str) -> str:
    charger_les_cles()
    valeur = os.environ.get(nom)
    if not valeur:
        raise RuntimeError(
            f"la variable {nom} est absente. La renseigner dans l'environnement ou dans "
            f"{FICHIER_DE_CLES}, jamais dans le code ni dans un dépôt."
        )
    return valeur


@dataclass(frozen=True)
class Requete:
    """Ce qu'on demande : un symbole, une fenêtre, un pas, et un flux."""

    symbole: str
    debut: str  # date ISO, incluse
    fin: str  # date ISO, incluse
    pas: str = "1Min"
    flux: str = "sip"  # « sip » pour le consolidé, « iex » pour le seul flux IEX
    ajustement: str = "brut"  # « brut » ou « ajuste » ; voir le piège en tête de module

    def __post_init__(self) -> None:
        if self.flux not in ("sip", "iex"):
            raise ValueError("le flux est « sip » pour le consolidé ou « iex »")
        if self.ajustement not in ("brut", "ajuste"):
            raise ValueError("l'ajustement est « brut » ou « ajuste »")

    def nom_de_fichier(self, source: str) -> str:
        return (
            f"{source}_{self.symbole}_{self.pas}_{self.flux}_{self.ajustement}"
            f"_{self.debut}_{self.fin}.parquet"
        )


def _lire_json(url: str, entetes: dict[str, str], essais: int = 4):
    """Une requête, avec reprise sur les erreurs de débit et les coupures passagères."""
    attente = 2.0
    derniere: Exception | None = None
    for _ in range(essais):
        requete = urllib.request.Request(url, headers=entetes)
        try:
            with urllib.request.urlopen(requete, timeout=120) as reponse:
                return json.loads(reponse.read())
        except urllib.error.HTTPError as erreur:
            derniere = erreur
            if erreur.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError) as erreur:  # pragma: no cover - réseau
            derniere = erreur
        time.sleep(attente)
        attente *= 2
    raise RuntimeError(f"la requête a échoué après {essais} essais : {derniere}")


def _en_table(lignes: list[dict], colonnes: dict[str, str]):
    import pandas as pd

    if not lignes:
        return pd.DataFrame(
            columns=[
                "horodatage",
                "ouverture",
                "haut",
                "bas",
                "cloture",
                "volume",
                "transactions",
                "prix_moyen",
            ]
        )
    table = pd.DataFrame(lignes).rename(columns=colonnes)
    manquantes = [c for c in ("transactions", "prix_moyen") if c not in table]
    for c in manquantes:
        table[c] = float("nan")
    # les deux sources horodatent différemment : Alpaca en texte ISO, Polygon en millisecondes
    # depuis l'époque. La conversion se fait ici, AVANT le tri : la faire après trierait sur des
    # dates mal lues, et le tri apparierait ensuite les prix aux mauvaises minutes. Ce défaut a
    # existé, il ne se voyait sur aucun test de forme, et il déplaçait un tiers des barres.
    horodatage = table["horodatage"]
    if pd.api.types.is_numeric_dtype(horodatage):
        table["horodatage"] = pd.to_datetime(horodatage, unit="ms", utc=True)
    else:
        table["horodatage"] = pd.to_datetime(horodatage, utc=True, format="mixed")
    ordre = ["horodatage", "ouverture", "haut", "bas", "cloture", "volume", "transactions", "prix_moyen"]
    return table[ordre].sort_values("horodatage").reset_index(drop=True)


def barres_alpaca(r: Requete, cache: Path = CACHE, force: bool = False):
    """Les barres d'Alpaca, paginées jusqu'au bout et rangées en Parquet.

    Le flux se choisit à l'appel. Le consolidé remonte à 2016 et porte tout le marché ; le flux IEX
    ne remonte qu'à 2020 et n'en porte qu'un soixantième. Demander l'un pour l'autre change le
    résultat d'un facteur soixante sur les volumes, et le module ne devine donc jamais.
    """
    import pandas as pd

    cache = Path(cache)
    chemin = cache / r.nom_de_fichier("alpaca")
    if chemin.exists() and not force:
        return pd.read_parquet(chemin)

    entetes = {"APCA-API-KEY-ID": _cle("ALPACA_KEY_ID"), "APCA-API-SECRET-KEY": _cle("ALPACA_SECRET_KEY")}
    parametres = {
        "symbols": r.symbole,
        "timeframe": r.pas,
        "feed": r.flux,
        "limit": "10000",
        "start": f"{r.debut}T00:00:00Z",
        "end": f"{r.fin}T23:59:59Z",
        "adjustment": "raw" if r.ajustement == "brut" else "all",
    }
    lignes: list[dict] = []
    jeton = None
    while True:
        if jeton:
            parametres["page_token"] = jeton
        url = "https://data.alpaca.markets/v2/stocks/bars?" + urllib.parse.urlencode(parametres)
        reponse = _lire_json(url, entetes)
        lignes.extend((reponse.get("bars") or {}).get(r.symbole) or [])
        jeton = reponse.get("next_page_token")
        if not jeton:
            break
    table = _en_table(
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
    chemin.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(chemin, index=False)
    return table


def barres_polygon(r: Requete, cache: Path = CACHE, force: bool = False, pause: float = 13.0):
    """Les barres de Polygon, avec la pause qu'impose son forfait gratuit.

    Le forfait gratuit accepte cinq requêtes par minute, d'où la pause entre deux appels. Cela pèse
    moins qu'il n'y paraît : un seul appel rend cinquante mille barres, soit cinquante-trois séances,
    et deux ans de barres minute tiennent donc en dix requêtes.
    """
    import pandas as pd

    cache = Path(cache)
    chemin = cache / r.nom_de_fichier("polygon")
    if chemin.exists() and not force:
        return pd.read_parquet(chemin)

    multiplicateur, unite = ("1", "minute") if r.pas.endswith("Min") else ("1", "day")
    if r.pas.endswith("Min") and r.pas[:-3].isdigit():
        multiplicateur = r.pas[:-3]
    cle = _cle("POLYGON_API_KEY")
    ajuste = "false" if r.ajustement == "brut" else "true"
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{r.symbole}/range/{multiplicateur}/{unite}/"
        f"{r.debut}/{r.fin}?adjusted={ajuste}&sort=asc&limit=50000&apiKey={cle}"
    )
    lignes: list[dict] = []
    premier = True
    while url:
        if not premier:
            time.sleep(pause)
        premier = False
        reponse = _lire_json(url, {})
        lignes.extend(reponse.get("results") or [])
        suite = reponse.get("next_url")
        url = f"{suite}&apiKey={cle}" if suite else None
    table = _en_table(
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
    chemin.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(chemin, index=False)
    return table


def barres(source: str, r: Requete, cache: Path = CACHE, force: bool = False):
    """Les barres d'une source ou de l'autre, derrière la même interface."""
    if source == "alpaca":
        return barres_alpaca(r, cache, force)
    if source == "polygon":
        return barres_polygon(r, cache, force)
    raise ValueError("la source est « alpaca » ou « polygon »")


def part_du_volume(consolide, iex) -> float:
    """La part du volume consolidé que le flux IEX capte, sur une fenêtre commune.

    C'est le nombre qui décide si un prix moyen pondéré par les volumes calculé sur IEX veut dire
    quelque chose. Mesuré à 1,81 % sur QQQ en juin 2026, sur un mois entier.
    """
    total = float(consolide["volume"].sum())
    if total <= 0:
        raise ValueError("le volume consolidé est nul : la fenêtre ne contient aucune séance")
    return float(iex["volume"].sum()) / total
