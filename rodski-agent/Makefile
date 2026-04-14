.PHONY: install test lint clean

install:
	pip3 install -e ".[dev]"

test:
	PYTHONPATH=src python3 -m pytest tests/ -v

lint:
	ruff check src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
