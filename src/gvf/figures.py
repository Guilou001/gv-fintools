"""Sept figures que les dépôts refont chacun de leur côté, écrites une fois et vérifiées.

Chaque fabrique dessine ET renvoie les nombres qu'elle a dessinés. C'est la conséquence d'une règle
apprise à l'audit du 2026-08-29 : une figure peut être vraie et ne rien montrer, et une figure peut
montrer quelque chose de faux sans que rien ne le signale. Tant que la fonction ne rend que des
pixels, aucun test ne peut la contredire. Ici le test porte sur les nombres rendus, et le dessin
n'est plus qu'une mise en forme de ce qui a déjà été vérifié.

Les sept répondent aux besoins mesurés des quatre familles minces du portefeuille : la cascade pour
décomposer un résultat, la courbe ROC et l'écart de Kolmogorov-Smirnov pour un modèle de défaut, la
matrice de transition pour les migrations de notation, l'éventail pour un jeu de trajectoires
simulées, la tornade pour une analyse de sensibilité, la crête pour comparer des distributions de
pertes, le triangle pour le développement des sinistres.
"""

from __future__ import annotations

import numpy as np

from .style import GRIS, OKABE_ITO, fr


def cascade(ax, etiquettes: list[str], valeurs: list[float], depart: float = 0.0,
            total: str | None = "Total", decimales: int = 1) -> np.ndarray:
    """Une cascade : d'où part une grandeur, ce qui l'augmente, ce qui la diminue, où elle arrive.

    Les barres flottent entre le cumul avant et le cumul après, si bien que la hauteur d'une barre
    est la contribution et sa position la valeur atteinte. Renvoie les cumuls, `depart` compris, donc
    un tableau de longueur `len(valeurs) + 1`.
    """
    valeurs = np.asarray(valeurs, dtype=float)
    cumuls = np.concatenate([[depart], depart + np.cumsum(valeurs)])
    positions = np.arange(len(valeurs))

    for i, v in enumerate(valeurs):
        bas, haut = min(cumuls[i], cumuls[i + 1]), max(cumuls[i], cumuls[i + 1])
        couleur = OKABE_ITO[2] if v >= 0 else OKABE_ITO[3]
        ax.bar(positions[i], haut - bas, bottom=bas, color=couleur, width=0.62)
        ax.annotate(("+" if v > 0 else "") + fr(v, decimales), (positions[i], haut),
                    ha="center", va="bottom", fontsize=8.5, color=GRIS)
        if i:
            ax.plot([positions[i] - 1 + 0.31, positions[i] - 0.31], [cumuls[i]] * 2,
                    color=GRIS, linewidth=0.7, linestyle=":")

    noms = list(etiquettes)
    sommets = [max(cumuls[i], cumuls[i + 1]) for i in range(len(valeurs))]
    if total is not None:
        # la barre de total part de zéro et non du cumul précédent : une barre flottante donnerait
        # à lire sa hauteur comme un total, alors qu'elle ne serait qu'une variation
        ax.bar(len(valeurs), cumuls[-1], bottom=0.0, color=OKABE_ITO[0], width=0.62)
        ax.annotate(fr(cumuls[-1], decimales), (len(valeurs), max(cumuls[-1], 0.0)),
                    ha="center", va="bottom", fontsize=8.5, color=GRIS)
        noms = noms + [total]
        sommets.append(max(cumuls[-1], 0.0))
    ax.set_xticks(range(len(noms)))
    ax.set_xticklabels(noms, rotation=20, ha="right")
    ax.axhline(0.0 if total is not None else depart, color=GRIS, linewidth=0.8)

    # de la place au-dessus des barres, sinon les valeurs annotées viennent buter dans le titre
    planchers = [min(cumuls.min(), 0.0 if total is not None else cumuls.min())]
    bas, haut = min(planchers), max(sommets)
    ax.set_ylim(bas - 0.05 * (haut - bas or 1.0), haut + 0.13 * (haut - bas or 1.0))
    return cumuls


def roc_ks(ax, verite, score, etiquette: str = "modèle", tracer_ks: bool = True) -> dict:
    """La courbe ROC d'un score de défaut, avec l'aire, le Gini et l'écart de Kolmogorov-Smirnov.

    Le score est supposé croissant avec le risque : plus il est haut, plus le défaut est probable.
    L'aire sous la courbe se calcule par la statistique de Mann et Whitney, donc exactement, ex aequo
    compris, et non par intégration approchée. Le Gini vaut deux fois l'aire moins un.

    L'écart de Kolmogorov-Smirnov est la plus grande distance verticale entre les deux fonctions de
    répartition, celle des défauts et celle des sains : c'est le point où le modèle sépare le mieux,
    et le seuil qui l'atteint est celui qu'un service de crédit retient pour trancher.
    """
    verite = np.asarray(verite).astype(int)
    score = np.asarray(score, dtype=float)
    positifs, negatifs = verite.sum(), (1 - verite).sum()
    if positifs == 0 or negatifs == 0:
        raise ValueError("la courbe ROC exige au moins un défaut et un sain")

    ordre = np.argsort(-score, kind="mergesort")
    tpr = np.concatenate([[0.0], np.cumsum(verite[ordre]) / positifs])
    fpr = np.concatenate([[0.0], np.cumsum(1 - verite[ordre]) / negatifs])

    rangs = _rangs_moyens(score)
    aire = (rangs[verite == 1].sum() - positifs * (positifs + 1) / 2) / (positifs * negatifs)

    ecarts = tpr - fpr
    i_ks = int(np.argmax(ecarts))
    ks = float(ecarts[i_ks])
    seuil = float(score[ordre][min(i_ks, len(ordre) - 1)]) if i_ks else float(score.max())

    ax.plot(fpr, tpr, color=OKABE_ITO[0], label=f"{etiquette} : aire {fr(aire, 3)}")
    ax.plot([0, 1], [0, 1], color=GRIS, linewidth=0.9, linestyle="--", label="hasard : aire 0,500")
    if tracer_ks:
        ax.vlines(fpr[i_ks], fpr[i_ks], tpr[i_ks], color=OKABE_ITO[3], linewidth=1.6)
        ax.annotate(f"KS = {fr(ks, 3)}", (fpr[i_ks], (tpr[i_ks] + fpr[i_ks]) / 2),
                    xytext=(8, 0), textcoords="offset points", fontsize=9, color=OKABE_ITO[3])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Part des sains classés au-dessus du seuil")
    ax.set_ylabel("Part des défauts classés au-dessus du seuil")
    ax.legend(loc="lower right")
    return {"aire": float(aire), "gini": float(2 * aire - 1), "ks": ks, "seuil_ks": seuil,
            "defauts": int(positifs), "sains": int(negatifs)}


def _rangs_moyens(x: np.ndarray) -> np.ndarray:
    """Les rangs croissants, les ex aequo recevant leur rang moyen.

    C'est ce qui rend l'aire exacte quand des scores sont égaux, cas fréquent sur un score discret.
    """
    ordre = np.argsort(x, kind="mergesort")
    tries = x[ordre]
    rangs = np.empty(len(x), dtype=float)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and tries[j + 1] == tries[i]:
            j += 1
        rangs[ordre[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return rangs


def matrice_transition(ax, matrice, etats: list[str], decimales: int = 2,
                       unite: str = "%") -> np.ndarray:
    """Une matrice de migration : ligne, l'état de départ ; colonne, l'état d'arrivée.

    La diagonale porte la persistance et concentre presque toute la masse, ce qui écrase l'échelle
    de couleur. Elle est donc bornée au plus grand terme hors diagonale, et la diagonale s'écrit en
    clair par-dessus. Renvoie la matrice telle qu'elle est dessinée.
    """
    m = np.asarray(matrice, dtype=float)
    if m.shape[0] != m.shape[1] or m.shape[0] != len(etats):
        raise ValueError("la matrice doit être carrée et de la taille de la liste d'états")
    hors_diagonale = m[~np.eye(len(etats), dtype=bool)]
    plafond = float(hors_diagonale.max()) if hors_diagonale.size else float(m.max())

    image = ax.imshow(m, cmap="Blues", vmin=0.0, vmax=max(plafond, 1e-12))
    for i in range(len(etats)):
        for j in range(len(etats)):
            fonce = i == j or m[i, j] > 0.6 * plafond
            ax.text(j, i, fr(m[i, j], decimales), ha="center", va="center", fontsize=8,
                    color="white" if fonce else GRIS)
    ax.set_xticks(range(len(etats)), etats)
    ax.set_yticks(range(len(etats)), etats)
    ax.set_xlabel("État à la fin de l'année")
    ax.set_ylabel("État au début de l'année")
    ax.grid(False)
    barre = ax.figure.colorbar(image, ax=ax, fraction=0.045)
    barre.set_label(f"Probabilité de transition ({unite}), échelle bornée hors diagonale",
                    fontsize=8.5)
    return m


def eventail(ax, x, trajectoires, quantiles=(5, 25, 50, 75, 95), couleur: str = OKABE_ITO[0],
             etiquette_mediane: str = "médiane") -> dict:
    """Un éventail de trajectoires simulées, résumé par ses quantiles.

    Dessiner mille trajectoires produit une tache noire. Dessiner leurs quantiles produit une bande
    dont la largeur EST l'incertitude. Les quantiles se lisent par paires symétriques autour de la
    médiane, du plus large au plus étroit. Renvoie un dictionnaire quantile vers série.
    """
    trajectoires = np.asarray(trajectoires, dtype=float)
    if trajectoires.ndim != 2:
        raise ValueError("trajectoires doit être une matrice, une ligne par tirage")
    q = {p: np.percentile(trajectoires, p, axis=0) for p in quantiles}

    bas = sorted(p for p in quantiles if p < 50)
    for rang, p in enumerate(bas):
        haut = 100 - p
        if haut not in q:
            continue
        ax.fill_between(x, q[p], q[haut], color=couleur, alpha=0.15 + 0.13 * rang, linewidth=0,
                        label=f"{fr(100 - 2 * p)} % des tirages")
    if 50 in q:
        ax.plot(x, q[50], color=couleur, linewidth=2.0, label=etiquette_mediane)
    return {p: v for p, v in q.items()}


def tornade(ax, noms: list[str], bas, haut, base: float = 0.0, decimales: int = 1) -> list[int]:
    """Une tornade : l'effet de chaque hypothèse quand on la pousse vers le bas puis vers le haut.

    Les barres sont triées par amplitude décroissante, la plus large en haut, ce qui répond d'un coup
    d'oeil à la seule question posée à une analyse de sensibilité : de quoi le résultat dépend-il
    vraiment. Renvoie l'ordre de tri, en indices d'entrée.
    """
    bas, haut = np.asarray(bas, dtype=float), np.asarray(haut, dtype=float)
    amplitude = np.abs(haut - bas)
    ordre = list(np.argsort(amplitude))  # le plus large finit en haut de l'axe

    for rang, i in enumerate(ordre):
        gauche, droite = min(bas[i], base), max(bas[i], base)
        ax.barh(rang, droite - gauche, left=gauche, color=OKABE_ITO[3], height=0.6)
        gauche, droite = min(haut[i], base), max(haut[i], base)
        ax.barh(rang, droite - gauche, left=gauche, color=OKABE_ITO[2], height=0.6)
        ax.annotate(f"{fr(bas[i], decimales)} … {fr(haut[i], decimales)}",
                    (max(bas[i], haut[i]), rang), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8, color=GRIS)
    ax.axvline(base, color=GRIS, linewidth=1.0)
    ax.set_yticks(range(len(ordre)), [noms[i] for i in ordre])
    ax.set_ylim(-0.7, len(ordre) - 0.3)
    return ordre


def ridgeline(ax, groupes: dict, points: int = 256, hauteur: float = 1.6,
              etendue: float = 0.08) -> dict:
    """Des distributions empilées, une par groupe, pour les comparer sans les superposer.

    Chaque densité est lissée par un noyau gaussien de largeur choisie par la règle de Silverman,
    qui est le compromis usuel entre une courbe hachée et une courbe si lisse qu'elle efface les
    modes. Renvoie, par groupe, la moyenne, la médiane et le mode de la densité tracée.
    """
    noms = list(groupes)
    valeurs = [np.asarray(groupes[n], dtype=float) for n in noms]
    tous = np.concatenate(valeurs)
    marge = etendue * (tous.max() - tous.min() or 1.0)
    grille = np.linspace(tous.min() - marge, tous.max() + marge, points)

    resume = {}
    for rang, (nom, v) in enumerate(zip(noms, valeurs, strict=True)):
        densite = _noyau_gaussien(v, grille)
        y = rang * hauteur
        ax.fill_between(grille, y, y + densite / densite.max() * hauteur * 0.92,
                        color=OKABE_ITO[rang % len(OKABE_ITO)], alpha=0.72, linewidth=0)
        ax.plot(grille, y + densite / densite.max() * hauteur * 0.92, color=GRIS, linewidth=0.7)
        resume[nom] = {"moyenne": float(v.mean()), "mediane": float(np.median(v)),
                       "mode": float(grille[int(np.argmax(densite))])}
    ax.set_yticks([r * hauteur for r in range(len(noms))], noms)
    ax.set_ylim(-hauteur * 0.15, (len(noms) - 1) * hauteur + hauteur)
    ax.grid(axis="y", visible=False)
    return resume


def _noyau_gaussien(echantillon: np.ndarray, grille: np.ndarray) -> np.ndarray:
    """La densité lissée, largeur de fenêtre par la règle de Silverman."""
    n = len(echantillon)
    dispersion = min(echantillon.std(ddof=1), (np.percentile(echantillon, 75)
                                               - np.percentile(echantillon, 25)) / 1.349)
    if not dispersion:
        dispersion = 1.0
    h = 0.9 * dispersion * n ** (-0.2)
    ecarts = (grille[:, None] - echantillon[None, :]) / h
    return np.exp(-0.5 * ecarts ** 2).sum(axis=1) / (n * h * np.sqrt(2 * np.pi))


def triangle(ax, matrice, annees=None, retards=None, decimales: int = 0,
             titre_valeur: str = "Sinistres cumulés") -> np.ndarray:
    """Le triangle de développement : ligne, l'année de survenance ; colonne, le retard de règlement.

    La partie inférieure droite est vide parce qu'elle n'est pas encore arrivée : c'est exactement ce
    qu'un provisionnement doit remplir, et la figure le montre en creux. La couleur suit le rang de
    la valeur dans sa colonne et non sa valeur brute, sans quoi les colonnes les plus anciennes,
    seules complètes, écraseraient tout. Renvoie la matrice telle quelle.
    """
    m = np.asarray(matrice, dtype=float)
    annees = list(annees) if annees is not None else list(range(m.shape[0]))
    retards = list(retards) if retards is not None else list(range(1, m.shape[1] + 1))

    rangs = np.full(m.shape, np.nan)
    for j in range(m.shape[1]):
        colonne = m[:, j]
        connus = ~np.isnan(colonne)
        if connus.sum() > 1:
            ordre = np.argsort(np.argsort(colonne[connus]))
            rangs[connus, j] = ordre / (connus.sum() - 1)
        elif connus.sum() == 1:
            rangs[connus, j] = 0.5

    ax.imshow(np.ma.masked_invalid(rangs), cmap="Blues", vmin=0.0, vmax=1.0, aspect="auto")
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            if np.isnan(m[i, j]):
                continue
            ax.text(j, i, fr(m[i, j], decimales), ha="center", va="center", fontsize=7.5,
                    color="white" if rangs[i, j] > 0.62 else GRIS)
    ax.set_xticks(range(m.shape[1]), [str(r) for r in retards])
    ax.set_yticks(range(m.shape[0]), [str(a) for a in annees])
    ax.set_xlabel(f"Retard de développement, en années\n{titre_valeur}, couleur selon le rang "
                  "dans la colonne")
    ax.set_ylabel("Année de survenance")
    ax.grid(False)
    return m
