"""Le rapport PDF d'un dépôt, engendré depuis son README.

Le README d'un dépôt du portefeuille porte déjà tout : la question, la méthode, les tableaux de
résultats avec leur lecture guidée, les figures avec leur mode d'emploi, les limites et les crédits.
Le rapport n'ajoute donc rien ; il met en page, numérote et rend citable ce qui existe déjà. Un seul
texte, deux formes, aucune divergence possible entre les deux.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import typst

from gvf.markdown import chaine, convertir, ligne

GABARIT = """#set document(title: {titre}, author: "Guillaume Vaudescal")
#set page(
  paper: "a4",
  margin: (x: 2.2cm, y: 2.4cm),
  numbering: "1 / 1",
  footer: context [
    #set text(size: 8pt, fill: luma(90))
    #grid(columns: (1fr, auto), align: (left, right),
      [{pied}], [#counter(page).display("1 / 1", both: true)])
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
    #text(size: 18pt, weight: "bold")[{titre_affiche}]
    #v(0.6em)
    #text(size: 10pt, fill: luma(70))[Guillaume Vaudescal · {date} · #link("{depot}")[{depot_court}]]
  ]
]
#v(1.2em)
#line(length: 100%, stroke: 0.6pt + luma(190))
#v(0.8em)

{corps}
"""


def _depot_de(racine: Path) -> str:
    """L'adresse du dépôt, lue dans le fichier de configuration de git."""
    config = racine / ".git" / "config"
    if config.exists():
        for ligne in config.read_text().splitlines():
            if "url = " in ligne and "github.com" in ligne:
                return ligne.split("url = ", 1)[1].strip().removesuffix(".git")
    return "https://github.com/Guilou001"


def engendrer(racine: Path, destination: Path | None = None, date: str | None = None) -> Path:
    """Compile le README du dépôt en un rapport PDF, et rend le chemin écrit."""
    racine = racine.resolve()
    readme = racine / "README.md"
    if not readme.exists():
        raise FileNotFoundError(f"aucun README.md dans {racine}")

    destination = destination or racine / "rapport" / "rapport.pdf"
    # les chemins d'images sont relatifs au fichier Typst, qui vit dans son sous-dossier :
    # le document reste ainsi lisible depuis n'importe quelle machine
    vers_racine = "/".join([".."] * len(destination.parent.relative_to(racine).parts)) or "."
    document = convertir(readme.read_text(), racine=vers_racine)
    depot = _depot_de(racine)
    source = GABARIT.format(
        titre=chaine(document.titre),
        titre_affiche=ligne(document.titre),
        pied=ligne(racine.name),
        date=date or dt.date.today().isoformat(),
        depot=depot,
        depot_court=depot.replace("https://github.com/", ""),
        corps=document.corps,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    (destination.parent / f"{destination.stem}.typ").write_text(source)
    # la racine de compilation est le dépôt : sans elle, Typst refuse les chemins qui
    # remontent du dossier rapport/ vers results/figures/
    destination.write_bytes(typst.compile(destination.parent / f"{destination.stem}.typ", root=racine))
    return destination
