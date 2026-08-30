"""Les sept fabriques de figures, vérifiées sur leurs nombres et non sur leurs pixels."""

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from gvf.figures import (  # noqa: E402
    cascade,
    eventail,
    matrice_transition,
    ridgeline,
    roc_ks,
    tornade,
    triangle,
)
from gvf.style import ESPACE_FINE, OKABE_ITO, appliquer, enregistrer, formateur, fr  # noqa: E402


@pytest.fixture
def axe():
    fig, ax = plt.subplots()
    yield ax
    plt.close(fig)


def test_la_palette_est_celle_d_okabe_ito_et_ne_change_pas():
    """Huit couleurs distinguables par les trois formes courantes de daltonisme. Le test fige la
    liste : une couleur qui change silencieusement casse la comparaison entre deux dépôts."""
    assert len(OKABE_ITO) == 8
    assert OKABE_ITO[0] == "#0072B2" and OKABE_ITO[-1] == "#000000"
    assert len(set(OKABE_ITO)) == 8


def test_les_nombres_s_ecrivent_en_francais():
    assert fr(12.5, 1) == "12,5"
    assert fr(1234567.0, 0) == "1\u202f234\u202f567"   # espace fine insécable
    assert fr(0.5) == "0,5"


def test_le_formateur_applique_son_facteur_et_son_suffixe():
    """Afficher en millions sans toucher aux données : c'est le rôle du facteur."""
    f = formateur(1, " M$", 1e-6)
    assert f(3_400_000, None) == "3,4 M$"
    assert ESPACE_FINE in formateur(0)(1_500_000, None)


def test_la_figure_part_en_png_et_en_pdf(tmp_path):
    """La moitié des figures du portefeuille n'existait qu'en PNG, donc se pixelisait au rapport."""
    appliquer()
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    ecrits = enregistrer(fig, tmp_path / "figures", "essai")
    plt.close(fig)
    assert [c.suffix for c in ecrits] == [".png", ".pdf"]
    assert all(c.exists() and c.stat().st_size > 500 for c in ecrits)
    assert ecrits[1].read_bytes().startswith(b"%PDF")


def test_la_cascade_rend_les_cumuls_et_finit_sur_la_somme(axe):
    """Vérité arithmétique : partir de 100, ajouter 20, retrancher 45, arriver à 75."""
    cumuls = cascade(axe, ["hausse", "baisse"], [20.0, -45.0], depart=100.0)
    assert list(cumuls) == [100.0, 120.0, 75.0]


def test_la_cascade_sans_total_ne_dessine_que_ses_postes(axe):
    cumuls = cascade(axe, ["a", "b", "c"], [1.0, 2.0, 3.0], total=None)
    assert len(cumuls) == 4 and cumuls[-1] == pytest.approx(6.0)
    assert [t.get_text() for t in axe.get_xticklabels()] == ["a", "b", "c"]


def test_l_aire_sous_la_courbe_vaut_la_proportion_de_paires_bien_classees(axe):
    """Vérité connue calculée à la main : deux défauts (0,35 et 0,80), deux sains (0,10 et 0,40),
    trois des quatre paires sont dans le bon ordre, donc l'aire vaut exactement 0,75."""
    mesures = roc_ks(axe, [0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8])
    assert mesures["aire"] == pytest.approx(0.75)
    assert mesures["gini"] == pytest.approx(0.5)
    assert mesures["defauts"] == 2 and mesures["sains"] == 2


def test_une_separation_parfaite_donne_une_aire_de_un_et_un_ks_de_un(axe):
    verite = [0] * 50 + [1] * 50
    score = list(np.linspace(0, 0.49, 50)) + list(np.linspace(0.5, 1.0, 50))
    mesures = roc_ks(axe, verite, score)
    assert mesures["aire"] == pytest.approx(1.0)
    assert mesures["ks"] == pytest.approx(1.0)


def test_un_score_constant_ne_separe_rien_malgre_les_ex_aequo(axe):
    """Le piège que le rang moyen répare : sans lui, l'ordre de tri décide de l'aire."""
    mesures = roc_ks(axe, [0, 1, 0, 1], [1.0, 1.0, 1.0, 1.0])
    assert mesures["aire"] == pytest.approx(0.5)
    assert mesures["gini"] == pytest.approx(0.0)


def test_la_courbe_roc_refuse_un_echantillon_sans_defaut(axe):
    with pytest.raises(ValueError, match="au moins un défaut"):
        roc_ks(axe, [0, 0, 0], [0.1, 0.2, 0.3])


def test_l_echelle_de_la_matrice_de_transition_ignore_la_diagonale(axe):
    """Sans cela, une persistance de 91 % écrase toutes les migrations dans la même nuance."""
    m = np.array([[91.0, 8.0, 1.0], [5.0, 90.0, 5.0], [1.0, 9.0, 90.0]])
    rendu = matrice_transition(axe, m, ["A", "B", "C"])
    assert rendu.shape == (3, 3)
    assert axe.images[0].get_clim() == (0.0, 9.0)
    assert np.allclose(rendu.sum(axis=1), 100.0)


def test_la_matrice_de_transition_refuse_une_forme_incoherente(axe):
    with pytest.raises(ValueError, match="carrée"):
        matrice_transition(axe, np.ones((2, 3)), ["A", "B", "C"])


def test_l_eventail_rend_exactement_les_quantiles_demandes(axe):
    rng = np.random.default_rng(30)
    trajectoires = rng.normal(0.0, 1.0, (2000, 12)).cumsum(axis=1)
    bandes = eventail(axe, np.arange(12), trajectoires, quantiles=(5, 50, 95))
    for p in (5, 50, 95):
        assert np.allclose(bandes[p], np.percentile(trajectoires, p, axis=0))
    # la bande s'élargit avec l'horizon : c'est la propriété que la figure doit montrer
    largeur = bandes[95] - bandes[5]
    assert largeur[-1] > largeur[0]


def test_la_tornade_trie_par_amplitude_la_plus_large_en_haut(axe):
    """L'axe des ordonnées croît vers le haut, donc le tri croissant place la plus large en haut."""
    ordre = tornade(axe, ["petit", "grand", "moyen"], [-1.0, -9.0, -4.0], [1.0, 9.0, 4.0])
    assert [["petit", "grand", "moyen"][i] for i in ordre] == ["petit", "moyen", "grand"]
    assert [t.get_text() for t in axe.get_yticklabels()][-1] == "grand"


def test_la_crete_retrouve_le_mode_de_chaque_distribution(axe):
    """Deux lois normales centrées en 0 et en 5 : le lissage doit retrouver les deux modes.

    La tolérance de 0,15 n'est pas décorative. Le mode d'une densité lissée porte l'erreur
    d'échantillonnage du tirage et la largeur de la fenêtre, ici 0,9 fois l'écart type divisé par
    n puissance un cinquième : sur 40 000 tirages elle vaut 0,11, et le mode ne peut pas être plus
    précis que cela."""
    rng = np.random.default_rng(30)
    resume = ridgeline(axe, {"gauche": rng.normal(0, 1, 40_000), "droite": rng.normal(5, 1, 40_000)})
    assert resume["gauche"]["mode"] == pytest.approx(0.0, abs=0.15)
    assert resume["droite"]["mode"] == pytest.approx(5.0, abs=0.15)
    assert resume["droite"]["mediane"] > resume["gauche"]["mediane"]


def test_le_triangle_garde_ses_cases_vides(axe):
    """La partie inférieure droite n'est pas encore arrivée : elle doit rester vide, pas valoir zéro."""
    m = np.array([[100.0, 150.0, 170.0], [110.0, 165.0, np.nan], [120.0, np.nan, np.nan]])
    rendu = triangle(axe, m, annees=[2023, 2024, 2025], retards=[1, 2, 3])
    assert np.isnan(rendu[2, 1]) and np.isnan(rendu[1, 2])
    assert [t.get_text() for t in axe.get_yticklabels()] == ["2023", "2024", "2025"]
    # une seule case porte du texte par valeur connue, six au total
    assert len([t for t in axe.texts if t.get_text()]) == 6
