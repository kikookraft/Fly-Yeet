.PHONY: install run debug clean lint lint-strict

# Usage: make run MAP=maps/easy/01_linear_path.txt
MAP ?=

run:
	uv run python main.py $(MAP)

install:
	uv venv
	uv pip install -e .

debug:
	uv run python -m pdb main.py

clean:
	rm -rf __pycache__
	rm -rf .mypy_cache

lint:
	uv run flake8 . --exclude .venv
	uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 . --exclude .venv
	uv run mypy . --strict
