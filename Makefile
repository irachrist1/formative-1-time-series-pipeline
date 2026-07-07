.PHONY: install analysis notebook seed api test predict report all

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

analysis:
	.venv/bin/python scripts/run_analysis.py

notebook: analysis
	.venv/bin/python scripts/create_notebook.py
	.venv/bin/python -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=300 notebooks/01_time_series_analysis.ipynb

seed:
	.venv/bin/python scripts/seed_databases.py

api:
	.venv/bin/uvicorn src.api.main:app --reload

test:
	.venv/bin/pytest -q

predict:
	.venv/bin/python scripts/predict_from_api.py --database sql

report:
	.venv/bin/python scripts/create_erd.py
	.venv/bin/python scripts/build_report.py

all: install notebook test report

