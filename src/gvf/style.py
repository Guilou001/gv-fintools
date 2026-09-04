"""La feuille de style des figures du portefeuille, à un seul endroit.

Jusqu'ici chaque dépôt recopiait sa palette et sa fonction de réglage. Mesuré le 2026-08-30 sur les
399 fichiers Python du portefeuille : la palette apparaît dans 24 fichiers et `use_style()` est
redéfini 21 fois. Une correction de graisse de trait devait donc être faite 21 fois, et ne l'était
jamais. Ce module la fait une fois.

Deux choix qui ne vont pas de soi. La palette est celle d'Okabe et Ito, huit couleurs distinguables
par les trois formes courantes de daltonisme, et c'est la seule raison de son choix. Et les nombres
s'écrivent avec la virgule décimale, parce que les figures sont lues en français ; un axe qui affiche
« 12.5 » dans un rapport français est une faute que personne ne signale et que tout le monde voit.
"""

from __future__ import annotations

from pathlib import Path

OKABE_ITO = [
    "#0072B2",  # bleu
    "#E69F00",  # orange
    "#009E73",  # vert
    "#D55E00",  # vermillon
    "#CC79A7",  # rose
    "#56B4E9",  # bleu ciel
    "#F0E442",  # jaune
    "#000000",  # noir
]

GRIS = "#4D4D4D"

# L'espace fine insécable est le séparateur de milliers du français. Le glyphe existe dans DejaVu
# Sans, la police par défaut de matplotlib, vérifié le 2026-08-30 dans sa table de caractères.
ESPACE_FINE = "\u202f"


def appliquer(taille_base: float = 11.0) -> None:
    """Les réglages communs à toutes les figures du portefeuille.

    Les axes du haut et de droite disparaissent, la grille passe derrière en transparence faible, et
    la légende perd son cadre : trois décisions qui retirent de l'encre sans retirer d'information.
    """
    import matplotlib as mpl
    from cycler import cycler

    mpl.rcParams.update(
        {
            "figure.dpi": 200,
            "savefig.dpi": 200,
            "savefig.bbox": "tight",
            # les polices sont embarquées en TrueType dans les PDF plutôt que converties en dessins :
            # le texte d'une figure reste ainsi sélectionnable et cherchable dans le rapport
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.constrained_layout.use": True,
            "font.size": taille_base,
            "axes.titlesize": taille_base + 1,
            "axes.labelsize": taille_base - 0.5,
            "axes.prop_cycle": cycler(color=OKABE_ITO),
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.alpha": 0.3,
            "grid.linewidth": 0.5,
            "legend.frameon": False,
            "legend.fontsize": taille_base - 2,
            "lines.linewidth": 1.7,
            "xtick.labelsize": taille_base - 2,
            "ytick.labelsize": taille_base - 2,
        }
    )


def fr(valeur: float, decimales: int | None = None) -> str:
    """Un nombre écrit en français : virgule décimale, espace fine pour les milliers.

    Sans `decimales`, le format `g` choisit lui-même, ce qui convient aux graduations d'axe.
    """
    brut = f"{valeur:,.{decimales}f}" if decimales is not None else f"{valeur:g}"
    return brut.replace(",", ESPACE_FINE).replace(".", ",")


def formateur(decimales: int | None = None, suffixe: str = "", facteur: float = 1.0):
    """Un formateur d'axe en français, à passer à `set_major_formatter`.

    Le facteur sert à afficher en millions ou en points de pourcentage sans toucher aux données :
    `formateur(1, " M$", 1e-6)` transforme 3 400 000 en « 3,4 M$ ».
    """
    from matplotlib.ticker import FuncFormatter

    return FuncFormatter(lambda v, _: fr(v * facteur, decimales) + suffixe)


def axe_log_lisible(ax, decimales: int | None = None, suffixe: str = "", facteur: float = 1.0) -> None:
    """L'axe des ordonnées en échelle logarithmique, gradué en nombres ordinaires à 1, 2 et 5.

    Par défaut, matplotlib n'écrit que les puissances de dix, et une courbe qui va de 1 à 40
    ne montre que « 10 » entre ses deux bornes. Ici les graduations principales restent aux
    puissances de dix et les secondaires tombent à 2 et 5 fois chacune, toutes écrites en
    français avec le même formateur : 1, 2, 5, 10, 20, 50. Mesuré le 2026-09-04 sur les
    figures de richesse cumulée du portefeuille, qui n'avaient qu'une ou deux graduations.
    """
    from matplotlib.ticker import LogLocator

    ax.set_yscale("log")
    ax.yaxis.set_major_locator(LogLocator(base=10.0))
    ax.yaxis.set_minor_locator(LogLocator(base=10.0, subs=(2.0, 5.0)))
    ax.yaxis.set_major_formatter(formateur(decimales, suffixe, facteur))
    ax.yaxis.set_minor_formatter(formateur(decimales, suffixe, facteur))


def enregistrer(fig, dossier: Path | str, nom: str, vectoriel: bool = True) -> list[Path]:
    """La figure écrite en PNG et, par défaut, en PDF vectoriel.

    Le PNG sert au README lu sur GitHub, le PDF au rapport imprimé. Mesuré le 2026-08-30 : 13 des 20
    appels `savefig` du portefeuille n'écrivaient que du PNG, donc la moitié des figures n'existait
    sous aucune forme vectorielle et se pixelisait dans les rapports.
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    ecrits = [dossier / f"{nom}.png"]
    if vectoriel:
        ecrits.append(dossier / f"{nom}.pdf")
    for chemin in ecrits:
        fig.savefig(chemin)
    return ecrits
