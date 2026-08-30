"""Le Markdown des README du portefeuille, traduit en Typst.

Ce module ne traduit pas tout le Markdown, seulement ce que les README du portefeuille emploient :
titres, paragraphes, gras, italique, code en ligne, liens, citations, listes, tableaux, images et
blocs de code. Ce qu'il ne reconnaît pas, il le laisse passer en texte échappé plutôt que de le perdre.

Deux choix méritent d'être dits. Les écussons d'état, ces images cliquables en tête de fichier, sont
retirés : ils renvoient à un service en ligne et n'ont aucun sens sur une page imprimée. Les liens,
eux, sont conservés avec leur adresse, parce qu'un rapport se lit aussi à l'écran.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Les caractères que Typst interprète et qu'un texte ordinaire doit neutraliser.
A_ECHAPPER = "\\#$*_`<>@[]"
ECUSSON = re.compile(r"^\s*\[?!\[[^\]]*\]\([^)]*\)\]?(\([^)]*\))?\s*$")
IMAGE = re.compile(r"^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$")
TITRE = re.compile(r"^(#{1,6})\s+(.*)$")
PUCE = re.compile(r"^(\s*)[-*]\s+(.*)$")
NUMERO = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
SEPARATEUR = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


@dataclass
class Document:
    """Le corps traduit, et le titre lu dans le premier titre de niveau un."""

    titre: str
    corps: str


def chaine(texte: str) -> str:
    """Une chaîne littérale au format de Typst, qui n'accepte que les guillemets droits."""
    corps = texte.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{corps}"'


def echapper(texte: str) -> str:
    """Neutralise les caractères que Typst interprète."""
    return "".join("\\" + c if c in A_ECHAPPER else c for c in texte)


def _liens(texte: str) -> str:
    """Traduit les liens Markdown, en échappant le libellé mais pas l'adresse."""
    morceaux, position = [], 0
    for trouve in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", texte):
        morceaux.append(_marques(texte[position:trouve.start()]))
        libelle, adresse = trouve.group(1), trouve.group(2)
        morceaux.append(f'#link("{adresse}")[{_marques(libelle)}]')
        position = trouve.end()
    morceaux.append(_marques(texte[position:]))
    return "".join(morceaux)


def _marques(texte: str) -> str:
    """Gras, italique et code en ligne, le reste étant échappé."""
    sortie, position = [], 0
    motif = re.compile(r"\*\*(.+?)\*\*|(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)|`([^`]+)`")
    for trouve in motif.finditer(texte):
        sortie.append(echapper(texte[position:trouve.start()]))
        gras, italique, code = trouve.groups()
        if gras is not None:
            sortie.append(f"*{echapper(gras)}*")
        elif italique is not None:
            sortie.append(f"_{echapper(italique)}_")
        else:
            sortie.append(f"#raw({chaine(code)})")
        position = trouve.end()
    sortie.append(echapper(texte[position:]))
    return "".join(sortie)


def ligne(texte: str) -> str:
    """Une ligne de texte courant, traduite."""
    return _liens(texte)


def _cellules(ligne_brute: str) -> list[str]:
    depouillee = ligne_brute.strip().strip("|")
    return [c.strip() for c in depouillee.split("|")]


def _tableau(lignes: list[str]) -> str:
    """Un tableau Markdown, traduit en table Typst avec en-tête en gras."""
    entete = _cellules(lignes[0])
    corps = [_cellules(x) for x in lignes[2:]]
    largeur = len(entete)
    cellules = [f"[*{ligne(c)}*]" for c in entete]
    for rangee in corps:
        rangee = (rangee + [""] * largeur)[:largeur]
        cellules += [f"[{ligne(c)}]" for c in rangee]
    contenu = ",\n    ".join(cellules)
    return ("#table(\n"
            f"  columns: {largeur},\n"
            "  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },\n"
            "  align: left + top,\n"
            "  inset: 5pt,\n"
            f"    {contenu},\n"
            ")")


def _bloc_code(lignes: list[str], langue: str) -> str:
    contenu = "\n".join(lignes)
    langue_typst = f', lang: "{langue}"' if langue else ""
    return f"#raw({chaine(contenu)}, block: true{langue_typst})"


def convertir(source: str, racine: str = ".") -> Document:
    """Traduit un README complet, et rend son titre avec son corps."""
    lignes = source.splitlines()
    sortie: list[str] = []
    titre = ""
    i = 0
    while i < len(lignes):
        courante = lignes[i]

        # un écusson cliquable est une image distante enveloppée dans un lien
        if ECUSSON.match(courante) and not IMAGE.match(courante):
            i += 1
            continue

        if courante.startswith("```"):
            langue = courante[3:].strip()
            bloc, i = [], i + 1
            while i < len(lignes) and not lignes[i].startswith("```"):
                bloc.append(lignes[i])
                i += 1
            sortie.append(_bloc_code(bloc, langue))
            i += 1
            continue

        trouve = IMAGE.match(courante)
        if trouve:
            legende, chemin = trouve.group(1), trouve.group(2)
            # une image distante est un écusson d'état : elle n'a pas de sens sur du papier
            if chemin.startswith(("http://", "https://")):
                i += 1
                continue
            sortie.append(f'#figure(image("{racine}/{chemin}", width: 100%), '
                          f"caption: [{ligne(legende)}])")
            i += 1
            continue

        trouve = TITRE.match(courante)
        if trouve:
            niveau, texte = len(trouve.group(1)), trouve.group(2)
            if niveau == 1 and not titre:
                titre = texte
            else:
                sortie.append("=" * niveau + " " + ligne(texte))
            i += 1
            continue

        if courante.startswith(">"):
            bloc = []
            while i < len(lignes) and lignes[i].startswith(">"):
                bloc.append(lignes[i][1:].strip())
                i += 1
            paragraphes = "\n\n".join(p.strip() for p in "\n".join(bloc).split("\n\n") if p.strip())
            corps_cite = "\n\n".join(ligne(" ".join(p.split())) for p in paragraphes.split("\n\n"))
            sortie.append(f"#quote(block: true)[{corps_cite}]")
            continue

        if "|" in courante and i + 1 < len(lignes) and SEPARATEUR.match(lignes[i + 1]):
            bloc = []
            while i < len(lignes) and "|" in lignes[i]:
                bloc.append(lignes[i])
                i += 1
            sortie.append(_tableau(bloc))
            continue

        trouve = PUCE.match(courante) or NUMERO.match(courante)
        if trouve:
            bloc = []
            while i < len(lignes) and (PUCE.match(lignes[i]) or NUMERO.match(lignes[i])
                                       or (lignes[i].startswith("   ") and lignes[i].strip())):
                bloc.append(lignes[i])
                i += 1
            sortie.append(_liste(bloc))
            continue

        if not courante.strip():
            i += 1
            continue

        paragraphe = []
        while i < len(lignes) and lignes[i].strip() and not lignes[i].startswith((">", "#", "```")):
            if (PUCE.match(lignes[i]) or NUMERO.match(lignes[i])) and paragraphe:
                break
            paragraphe.append(lignes[i].strip())
            i += 1
        sortie.append(ligne(" ".join(paragraphe)))

    return Document(titre, "\n\n".join(sortie))


def _liste(bloc: list[str]) -> str:
    """Une liste à puces ou numérotée, les continuations rattachées à leur élément."""
    elements: list[tuple[str, str]] = []
    for ligne_brute in bloc:
        puce = PUCE.match(ligne_brute)
        numero = NUMERO.match(ligne_brute)
        if puce:
            elements.append(("-", puce.group(2)))
        elif numero:
            elements.append(("+", numero.group(3)))
        elif elements:
            marque, texte = elements[-1]
            elements[-1] = (marque, texte + " " + ligne_brute.strip())
    return "\n".join(f"{marque} {ligne(texte)}" for marque, texte in elements)
