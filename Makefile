install:
	pip install -r requirements.txt

db-start:
	brew services start mongodb-community@7.0

db-stop:
	brew services stop mongodb-community@7.0

dev:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 --reload-exclude 'venv/*'

run:
	uvicorn src.main:app --host 0.0.0.0 --port 8000

seed:
	python -m src.data.seed

test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ -v --cov=src --cov-report=term-missing

test-fast:
	python -m pytest tests/ -v -x

lint:
	python -m py_compile src/main.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

reseed:
	mongosh $(DB_NAME) --eval "db.drivers.drop(); db.teams.drop(); db.facts.drop(); db.users.drop()"
	python -m src.data.seed

DB_NAME ?= f1_facts_db

.PHONY: install db-start db-stop dev run seed test test-cov test-fast lint clean reseed
