# Prérequis : uv (https://docs.astral.sh/uv/)
UV ?= uv

setup:
	$(UV) sync --locked --all-extras

test:             ## 13 tests fermés, sans réseau
	$(UV) run pytest

lint:
	$(UV) run ruff check .
