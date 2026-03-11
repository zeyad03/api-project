PYTHON = venv/bin/python
PIP = venv/bin/pip

install:
	$(PIP) install -r requirements.txt

db-start:
	brew services start mongodb-community@7.0

db-stop:
	brew services stop mongodb-community@7.0

stop:
	@lsof -ti :8000 | xargs kill -9 2>/dev/null || echo "No server running on port 8000"

dev:
	$(PYTHON) -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 --reload-exclude 'venv/*'

run:
	$(PYTHON) -m uvicorn src.main:app --host 0.0.0.0 --port 8000

onboard:
	$(PYTHON) -m scripts.mongodb.onboard

seed:
	$(PYTHON) -m src.data.seed

test:
	$(PYTHON) -m pytest tests/ -v

test-cov:
	$(PYTHON) -m pytest tests/ -v --cov=src --cov-report=term-missing

test-fast:
	$(PYTHON) -m pytest tests/ -v -x

lint:
	$(PYTHON) -m py_compile src/main.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

reseed:
	$(PYTHON) -m scripts.mongodb.reset_db
	$(PYTHON) -m src.data.seed

DB_NAME ?= f1_facts_db

.PHONY: install db-start db-stop stop dev run onboard seed test test-cov test-fast lint clean reseed
