#set document(title: "Les outils communs des projets Finance", author: "Guillaume Vaudescal")
#set page(
  paper: "a4",
  margin: (x: 2.2cm, y: 2.4cm),
  numbering: "1 / 1",
  footer: context [
    #set text(size: 8pt, fill: luma(90))
    #grid(columns: (1fr, auto), align: (left, right),
      [gv-fintools], [#counter(page).display("1 / 1", both: true)])
  ],
)
#set text(font: ("Helvetica", "Arial", "DejaVu Sans"), size: 10pt, lang: "fr")
#set par(justify: true, leading: 0.68em, spacing: 1.1em)
#set heading(numbering: none)
#show heading.where(level: 2): it => block(above: 1.6em, below: 0.8em, text(size: 13pt, it))
#show heading.where(level: 3): it => block(above: 1.2em, below: 0.6em, text(size: 11pt, it))
#show raw.where(block: true): it => block(
  fill: luma(246), inset: 8pt, radius: 3pt, width: 100%, text(size: 8.5pt, it))
#show raw.where(block: false): it => text(size: 9pt, fill: rgb("#1a3f66"), it)
#show quote.where(block: true): it => block(
  inset: (left: 10pt), stroke: (left: 1.5pt + luma(180)),
  text(style: "italic", fill: luma(45), it.body))
// la table NE DOIT PAS être enfermée dans un par() : Typst 0.15 la supprime alors
// entièrement, sans erreur. Le réglage se pose donc dans la portée du bloc.
#show table: it => block(above: 1.1em, below: 1.1em,
  [#set par(justify: false); #text(size: 8.8pt, it)])
#show figure: it => block(above: 1.4em, below: 1.4em, it)
#show figure.caption: it => text(size: 8.5pt, fill: luma(70), it)
#show link: it => text(fill: rgb("#0072B2"), it)

#align(center)[
  #block(width: 100%)[
    #text(size: 18pt, weight: "bold")[Les outils communs des projets Finance]
    #v(0.6em)
    #text(size: 10pt, fill: luma(70))[Guillaume Vaudescal · 2026-09-08 · #link("https://github.com/Guilou001/gv-fintools")[Guilou001/gv-fintools]]
  ]
]
#v(1.2em)
#line(length: 100%, stroke: 0.6pt + luma(190))
#v(0.8em)

Les projets Finance ont besoin des mêmes tâches pratiques. Dessiner une figure lisible, charger des relevés bancaires ou produire un rapport ne devrait pas demander de recopier du code dans chaque dépôt.

Cette bibliothèque regroupe ces outils. Les études financières gardent leurs propres hypothèses et calculs.

== Choisir l'outil selon le besoin

#table(
  columns: 2,
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
  align: left + top,
  inset: 5pt,
    [*Besoin*],
    [*Ce que la bibliothèque fournit*],
    [Expliquer un résultat avec un graphique],
    [Sept fonctions de dessin et un style commun],
    [Interroger les comptes publics des banques canadiennes],
    [Un chargeur des relevés du BSIF et une base DuckDB utilisable en SQL],
    [Réutiliser des prix et volumes par minute],
    [Un client de téléchargement avec cache local],
    [Lire un README sous forme de rapport],
    [Une traduction en Typst, puis une compilation en PDF],
)

Les modules optionnels s'installent séparément. Le générateur de PDF n'impose pas les bibliothèques de données de marché.

== Voir ce que les graphiques expliquent

#figure(image("../docs/figures/fabriques_1.png", width: 100%), caption: [Exemples de décomposition, classement, changement de notation et incertitude])

Les quatre panneaux répondent à des questions différentes. D'où vient un total ? Un score sépare-t-il deux groupes ? Comment les notations changent-elles ? Quelle dispersion ont les trajectoires simulées ?

Ce sont des données de démonstration. Aucun panneau ne présente un résultat d'investissement.

Chaque fonction renvoie aussi les nombres qu'elle a dessinés. On peut ainsi vérifier le calcul indépendamment de son apparence. La #link("docs/figures/fabriques_2.png")[galerie complète] ajoute les analyses de sensibilité, les distributions et les sinistres.

== Un premier exemple complet

Après l'installation ci-dessous, ce code dessine un revenu de 100 dollars canadiens, des dépenses de 65 dollars et le solde de 35 dollars.

#raw("import matplotlib.pyplot as plt\nfrom gvf.figures import cascade\nfrom gvf.style import appliquer\n\nappliquer()\nfig, ax = plt.subplots()\ncumuls = cascade(ax, [\"Revenus\", \"Dépenses\"], [100, -65], total=\"Solde\")\nax.set_ylabel(\"Dollars canadiens\")\nax.set_title(\"Un exemple de budget\")\nfig.savefig(\"budget.png\", facecolor=\"white\", bbox_inches=\"tight\")\nplt.close(fig)\nassert cumuls[-1] == 35", block: true, lang: "python")

== Connaître les limites

Le traducteur PDF couvre le Markdown utilisé par ces projets, pas toute la norme. Les tableaux très larges et le HTML complexe demandent une vérification visuelle.

Un chargeur de données ne décide pas du sens économique des colonnes. Les dates, les unités et le périmètre des comptes restent à contrôler dans chaque étude.

Les mesures de couverture des flux intrajournaliers dépendent aussi des heures retenues. Inclure la nuit donne une image très différente de la seule séance de bourse.

== Installer et utiliser

#raw("uv sync --locked --all-extras\nuv run pytest\nuv run gvf rapport /chemin/vers/un/depot", block: true, lang: "bash")

La dernière commande écrit rapport/rapport.pdf et sa source Typst dans le dépôt indiqué. Les clients de marché nécessitent les accès du fournisseur, conservés hors du code.

== Pour aller plus loin

#link("docs/ETUDE_DETAILLEE.md")[Méthodes, résultats complets et références] · #link("rapport/rapport.pdf")[Présentation en PDF] · #link("CITATION.cff")[Citer le projet] · #link("LICENSE")[Licence].

== English summary

Shared utilities for the Finance repositories provide chart factories, Canadian bank filing ingestion, cached intraday data and README-to-PDF reports. Chart functions return their numerical inputs or summaries so arithmetic can be checked separately from visual presentation.
