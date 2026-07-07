# Metro Interstate Traffic Volume Forecasting Pipeline

This project forecasts hourly traffic volume on westbound Interstate 94 between Minneapolis and St. Paul, Minnesota. It contains the complete pipeline requested in Formative 1: preprocessing and EDA, feature engineering, model tuning, MySQL and MongoDB implementations, CRUD APIs, time-series queries, and an API-to-model prediction script.

## Problem and dataset

The prediction target is `traffic_volume`, the number of westbound vehicles recorded during an hour. Forecasting this measure can support traffic management and road planning. The dataset is useful because it contains several years of traffic, weather, and holiday observations.

- Kaggle: [Metro Interstate Traffic Volume](https://www.kaggle.com/datasets/anshtanwar/metro-interstate-traffic-volume)
- Original publisher: Minnesota Department of Transportation
- Raw observations: 48,204
- Time range: 2 October 2012 09:00 to 30 September 2018 23:00
- Intended granularity: hourly
- Target: `traffic_volume`

## Main results

The selected random forest (`RF-2`) used calendar, weather, lag, and moving-average features. The final chronological test results were:

| Metric | Result |
|---|---:|
| MAE | 147.79 vehicles/hour |
| RMSE | 233.21 vehicles/hour |
| R-squared | 0.9861 |
| Test observations | 6,281 |

Traffic from the same hour one week earlier had a correlation of 0.944 with current traffic. This was the strongest lag relationship found.

## Repository structure

```text
├── data/
│   ├── raw/                         # Original Kaggle/UCI CSV
│   └── processed/                   # Generated hourly feature data
├── models/                          # Generated trained model
├── notebooks/
│   └── 01_time_series_analysis.ipynb
├── output/pdf/                      # Final PDF submission
├── outputs/
│   ├── figures/                     # Generated EDA and model figures
│   └── tables/                      # Metrics and executed query results
├── reports/
│   ├── final_report.html            # Self-contained report preview
│   └── team_details.json            # Names, IDs, roles, and GitHub URL
├── scripts/                         # Analysis, seeding, report, and prediction scripts
├── src/
│   ├── api/                         # FastAPI application
│   ├── database/sql/                # MySQL schema, ERD source, and queries
│   ├── database/mongodb/            # Collection design, samples, and queries
│   └── features.py                  # Shared preprocessing and feature logic
└── tests/                           # API integration tests
```

## 1. Python setup

Python 3.9 or newer is supported.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Run Task 1 analysis and model experiments

```bash
python scripts/run_analysis.py
python scripts/create_notebook.py
python -m jupyter nbconvert --execute --to notebook --inplace \
  --ExecutePreprocessor.timeout=300 notebooks/01_time_series_analysis.ipynb
```

This creates the cleaned data, analytical figures, experiment table, test predictions, and `models/traffic_forecaster.joblib`.

### Preprocessing decisions

- The holiday text `None` means a normal day and is renamed `No Holiday`.
- Seventeen complete duplicates are removed.
- Repeated timestamps are aggregated into one hourly record.
- The data is reindexed to an hourly timeline.
- Only internal gaps of three hours or less are interpolated.
- Lags and moving averages use shifted traffic values so the current target cannot leak into its own predictors.

## 3. Configure MySQL and MongoDB

### macOS installation

```bash
brew install mysql
brew tap mongodb/brew
brew trust mongodb/brew
brew install mongodb-community@8.0
brew services start mysql
brew services start mongodb-community@8.0
```

### MySQL schema and local user

```bash
mysql -uroot < src/database/sql/schema.sql
mysql -uroot -e "CREATE USER IF NOT EXISTS 'traffic_user'@'localhost' IDENTIFIED BY 'traffic_password'; GRANT ALL PRIVILEGES ON traffic_pipeline.* TO 'traffic_user'@'localhost'; FLUSH PRIVILEGES;"
```

Copy the environment example and review its values:

```bash
cp .env.example .env
```

Seed both databases and execute the required queries:

```bash
python scripts/seed_databases.py
python scripts/run_database_queries.py
```

For quick development without database services, omit `.env`. The API then uses SQLite for the SQL-compatible route and `mongomock` for the MongoDB-compatible route. The submitted query evidence was also verified against running MySQL and MongoDB services with 1,000 records in each.

## 4. Run the API

```bash
uvicorn src.api.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

| Method | SQL route | MongoDB route |
|---|---|---|
| POST | `/sql/records` | `/mongo/records` |
| GET one | `/sql/records/{id}` | `/mongo/records/{id}` |
| PUT | `/sql/records/{id}` | `/mongo/records/{id}` |
| DELETE | `/sql/records/{id}` | `/mongo/records/{id}` |
| Latest | `/sql/records/latest` | `/mongo/records/latest` |
| Date range | `/sql/records?start=&end=` | `/mongo/records?start=&end=` |

## 5. Run the integrated prediction

Keep the API running, then use either database route:

```bash
python scripts/predict_from_api.py --database sql
python scripts/predict_from_api.py --database mongo
```

The verified example fetched 337 API records and predicted 1,110.93 vehicles/hour for the final record. The actual value was 954.

## 6. Tests

```bash
pytest -q
```

The automated test covers create, read, update, delete, latest, and date-range operations for both database implementations. `scripts/smoke_test_api.py` performs the same checks against a running API and deletes its temporary records afterward.

## 7. Build the report

Update `reports/team_details.json` with the group members, student IDs, group name, and GitHub URL. Then run:

```bash
python scripts/create_erd.py
python scripts/build_report.py
```

Final PDF: `output/pdf/metro_traffic_pipeline_report.pdf`

The HTML version in `reports/final_report.html` is self-contained and can be opened directly in a browser.

## Make shortcuts

```bash
make analysis
make notebook
make seed
make api
make test
make report
```

## Team contribution requirement

Each member should update `reports/team_details.json` and make at least four meaningful commits under their own GitHub account. Do not submit the PDF while placeholder names or the placeholder GitHub URL remain.

