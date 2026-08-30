# gv-fintools : le rapport PDF d'un dépôt, engendré depuis son README

Les dépôts du portefeuille portent tout leur contenu dans leur README : la question, la méthode, les
tableaux avec leur lecture guidée, les figures avec leur mode d'emploi, les limites avec leur statut.
Il leur manquait une forme imprimable. Cet outil la produit sans rien réécrire.

[![ci](https://github.com/Guilou001/gv-fintools/actions/workflows/ci.yml/badge.svg)](https://github.com/Guilou001/gv-fintools/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.12-blue)
![licence](https://img.shields.io/badge/code-MIT-green)

**Résultat en une phrase.** Une commande transforme le README d'un dépôt en un rapport PDF composé,
paginé et citable, en traduisant le Markdown vers Typst : **13 tests fermés**, dont un qui compile un
document complet et relit le PDF produit.

## 1. La question posée

Comment donner un rapport PDF à vingt-quatre dépôts sans écrire vingt-quatre rapports ?

En mots simples : le texte existe déjà, bien écrit et vérifié, dans le README. Le dupliquer dans un
second fichier créerait deux versions qui divergeraient dès la première correction. Mieux vaut une
seule source et deux formes.

## 2. Ce que l'outil traduit, et ce qu'il écarte

Le traducteur ne couvre pas tout le Markdown, seulement ce que les README du portefeuille emploient.

| Élément Markdown | Ce qu'il devient |
|---|---|
| Titres de niveau 2 à 6 | titres Typst, celui de niveau 1 devenant le titre du document |
| Gras, italique, code en ligne | les marques équivalentes, le texte alentour échappé |
| Liens | `#link`, l'adresse conservée telle quelle |
| Citations | blocs cités, à filet vertical et en italique |
| Tableaux | `#table`, en-tête en gras et filet sous la première ligne |
| Images relatives | `#figure` numérotée, avec sa légende |
| Images distantes | retirées : ce sont les écussons d'état, sans objet sur du papier |
| Blocs de code | `#raw` avec coloration syntaxique |
| Listes à puces et numérotées | listes Typst, les lignes de continuation rattachées à leur élément |

Comment lire ce tableau, en trois constats. D'abord, la distinction entre image relative et image
distante est ce qui sépare une figure du dépôt d'un écusson d'état ; la première version confondait
les deux et perdait toutes les figures. Ensuite, chaque texte qui n'est pas une structure reconnue est
échappé caractère par caractère, faute de quoi un dièse ou une étoile du texte deviendrait une
instruction Typst. Enfin, rien n'est ajouté au README : le rapport ne peut pas dire autre chose que
lui.

## 3. La méthode, pas à pas

1. **Lire le README** du dépôt et en extraire le titre de niveau 1.
2. **Traduire le corps**, bloc par bloc, en gardant l'ordre du fichier.
3. **Composer le document** avec une page de titre, un pied de page numéroté et l'adresse du dépôt,
   lue dans la configuration de git.
4. **Compiler avec Typst**, la racine de compilation étant le dépôt lui-même pour que les figures de
   `results/figures/` soient atteignables depuis `rapport/`.
5. **Écrire le PDF et son source Typst** côte à côte, le second restant lisible et recompilable.

## 4. S'en servir

```bash
uv sync --locked --all-extras
uv run pytest                              # 13 tests fermés, sans réseau
uv run gvf rapport /chemin/vers/un/depot   # écrit rapport/rapport.pdf
```

Depuis un dépôt du portefeuille, `uv run gvf rapport .` suffit. La compilation d'un rapport de huit
pages avec trois figures prend moins d'une seconde.

## 5. Limites, avec leur statut

| Limite | Statut |
|---|---|
| Le Markdown couvert est celui des README du portefeuille, pas la norme complète | déclaré ; les listes imbriquées, les notes de bas de page et le HTML brut ne sont pas traduits |
| Les tableaux très larges débordent en petits caractères plutôt que de se replier | reconnu ; Typst répartit les colonnes, mais un tableau de neuf colonnes reste dense |
| La police est celle du système, avec Helvetica en premier choix | déclaré ; un poste sans Helvetica prendra Arial puis DejaVu Sans |
| Le résumé anglais reste dans le corps du rapport, sans page séparée | déclaré ; c'est la structure du README |

## 6. Crédits, licence, citation

Écrit en 2026 pour le portefeuille Finance de Guillaume Vaudescal. Code sous licence MIT.
