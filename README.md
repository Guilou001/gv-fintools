# Les outils communs des projets Finance

Les projets Finance ont besoin des mêmes tâches pratiques. Dessiner une figure lisible, charger des relevés bancaires ou produire un rapport ne devrait pas demander de recopier du code dans chaque dépôt.

Cette bibliothèque regroupe ces outils. Les études financières gardent leurs propres hypothèses et calculs.

## Choisir l'outil selon le besoin

| Besoin | Ce que la bibliothèque fournit |
|---|---|
| Expliquer un résultat avec un graphique | Sept fonctions de dessin et un style commun |
| Interroger les comptes publics des banques canadiennes | Un chargeur des relevés du BSIF et une base DuckDB utilisable en SQL |
| Réutiliser des prix et volumes par minute | Un client de téléchargement avec cache local |
| Lire un README sous forme de rapport | Une traduction en Typst, puis une compilation en PDF |

Les modules optionnels s'installent séparément. Le générateur de PDF n'impose pas les bibliothèques de données de marché.

## Voir ce que les graphiques expliquent

![Exemples de décomposition, classement, changement de notation et incertitude](docs/figures/fabriques_1.png)

Les quatre panneaux répondent à des questions différentes. D'où vient un total ? Un score sépare-t-il deux groupes ? Comment les notations changent-elles ? Quelle dispersion ont les trajectoires simulées ?

Ce sont des données de démonstration. Aucun panneau ne présente un résultat d'investissement.

Chaque fonction renvoie aussi les nombres qu'elle a dessinés. On peut ainsi vérifier le calcul indépendamment de son apparence. La [galerie complète](docs/figures/fabriques_2.png) ajoute les analyses de sensibilité, les distributions et les sinistres.

## Un premier exemple complet

Après l'installation ci-dessous, ce code dessine un revenu de 100 dollars canadiens, des dépenses de 65 dollars et le solde de 35 dollars.

```python
import matplotlib.pyplot as plt
from gvf.figures import cascade
from gvf.style import appliquer

appliquer()
fig, ax = plt.subplots()
cumuls = cascade(ax, ["Revenus", "Dépenses"], [100, -65], total="Solde")
ax.set_ylabel("Dollars canadiens")
ax.set_title("Un exemple de budget")
fig.savefig("budget.png", facecolor="white", bbox_inches="tight")
plt.close(fig)
assert cumuls[-1] == 35
```

## Connaître les limites

Le traducteur PDF couvre le Markdown utilisé par ces projets, pas toute la norme. Les tableaux très larges et le HTML complexe demandent une vérification visuelle.

Un chargeur de données ne décide pas du sens économique des colonnes. Les dates, les unités et le périmètre des comptes restent à contrôler dans chaque étude.

Les mesures de couverture des flux intrajournaliers dépendent aussi des heures retenues. Inclure la nuit donne une image très différente de la seule séance de bourse.

## Installer et utiliser

```bash
uv sync --locked --all-extras
uv run pytest
uv run gvf rapport /chemin/vers/un/depot
```

La dernière commande écrit rapport/rapport.pdf et sa source Typst dans le dépôt indiqué. Les clients de marché nécessitent les accès du fournisseur, conservés hors du code.

## Pour aller plus loin

[Méthodes, résultats complets et références](docs/ETUDE_DETAILLEE.md) · [Présentation en PDF](rapport/rapport.pdf) · [Citer le projet](CITATION.cff) · [Licence](LICENSE).

## English summary

Shared utilities for the Finance repositories provide chart factories, Canadian bank filing ingestion, cached intraday data and README-to-PDF reports. Chart functions return their numerical inputs or summaries so arithmetic can be checked separately from visual presentation.
