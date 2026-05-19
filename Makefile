.PHONY: install run debug clean lint lint-strict

install:
	uv venv
	uv pip install pygame flake8 mypy

run:
	uv run python gui.py

debug:
	uv run python -m pdb gui.py

clean:
	if exist __pycache__ rmdir /s /q __pycache__
	if exist .mypy_cache rmdir /s /q .mypy_cache
	if exist .venv rmdir /s /q .venv

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict
