# AI-Driven Student Performance Analytics — Backend

Django + Django REST Framework backend with a dedicated ML inference layer.
The model is trained **offline** (a script) and **loaded once** at server
startup; web requests only run fast predictions.

## Architecture

```
React (frontend)
   │  HTTP / JSON
   ▼
Django + DRF  ──────────────►  analytics/ml/service.py (MLService)
   │  ORM                          │ loads risk_model.pkl at startup
   ▼                               ▼
SQLite / PostgreSQL          RandomForest / XGBoost + SHAP
                                   ▲
                                   │ produced offline by
                             analytics/ml/train.py
```

## Project layout

```
backend/
├── manage.py
├── requirements.txt
├── config/                 # Django project (settings, urls, wsgi)
├── ml_models/              # trained .pkl artifacts (gitignored)
└── analytics/              # main app
    ├── models.py           # Student, Assessment, RiskPrediction
    ├── serializers.py      # DRF (incl. predict request validation)
    ├── views.py            # /api/health/, /api/predict/
    ├── urls.py
    ├── admin.py            # free data-management UI
    └── ml/
        ├── features.py     # FEATURE_COLUMNS (single source of truth)
        ├── service.py      # MLService: load + predict (+ rule-based fallback)
        └── train.py        # OFFLINE training -> risk_model.pkl
```

## Setup (Windows / PowerShell)

```powershell
# 1. Activate the virtual environment (already created at repo root)
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r backend\requirements.txt

# 3. Database
cd backend
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin

# 4. Train a model (writes ml_models\risk_model.pkl)
python -m analytics.ml.train                 # synthetic demo data
# python -m analytics.ml.train --csv data.csv  # your real data

# 5. Run the server
python manage.py runserver
```

> The backend works **before** step 4 too: with no model file, `MLService`
> falls back to a transparent rule-based predictor.

## API

| Method | Path           | Purpose                                  |
|--------|----------------|------------------------------------------|
| GET    | `/api/health/` | Liveness + whether a model is loaded     |
| POST   | `/api/predict/`| Risk score + level + explanation         |

Example:

```bash
curl -X POST http://localhost:8000/api/predict/ \
  -H "Content-Type: application/json" \
  -d '{"quiz_avg":45,"lab_avg":50,"assignment_avg":40,"midterm":48,"participation":25,"days_since_login":21}'
```

```json
{
  "risk_score": 0.86,
  "risk_level": "high",
  "model_version": "rf-v1",
  "explanation": {"quiz_avg": 0.21, "midterm": 0.19, "...": 0.0}
}
```

## Where to go next

- Swap `RandomForestClassifier` for `XGBClassifier` in `train.py` (uncomment
  xgboost in requirements) for the "advanced model" comparison.
- Enable SHAP (uncomment in requirements) — `service._explain` uses it
  automatically when installed.
- Add a CSV-import endpoint / management command to populate `Student` and
  `Assessment` from real course data.
- Build dashboard aggregation endpoints (class mean, pass rate, distribution).
```
