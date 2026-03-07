install:
	pip install -r requirements.txt

dev:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 --reload-exclude 'venv/*'

run:
	uvicorn src.main:app --host 0.0.0.0 --port 8000

seed:
	python -m src.data.seed

.PHONY: install dev run seed
