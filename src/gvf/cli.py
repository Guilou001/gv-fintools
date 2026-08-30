"""Ligne de commande des outils partagés."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="Outils partagés du portefeuille.")


@app.callback()
def main() -> None:
    """Sous-commandes nommées."""


@app.command()
def rapport(
    depot: Annotated[Path, typer.Argument(help="La racine du dépôt à mettre en page")] = Path("."),
    out: Annotated[Path | None, typer.Option(help="Le fichier PDF à écrire")] = None,
) -> None:
    """Engendre le rapport PDF d'un dépôt depuis son README."""
    from gvf.rapport import engendrer

    chemin = engendrer(depot, out)
    typer.echo(f"écrit {chemin} ({chemin.stat().st_size / 1e3:.0f} Ko)")


if __name__ == "__main__":
    app()
