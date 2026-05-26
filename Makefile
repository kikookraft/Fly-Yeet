.PHONY: install run debug clean lint lint-strict

run: install
	uv run python main.py

install:
	uv venv --clear
	uv pip install pygame flake8 mypy

debug:
	uv run python -m pdb gui.py

clean:
	rm -rf __pycache__
	rm -rf .mypy_cache
	rm -rf .venv

lint:
	uv run flake8 . --exclude .venv
	uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict
