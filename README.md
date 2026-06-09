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
                                   ▲
                                   │ features from
                          OULAD dataset (analytics/ml/oulad.py)
```

Current model: RandomForest on OULAD, **ROC-AUC ≈ 0.82, accuracy ≈ 0.74**
(early-window prediction using only the first 28 days).

## Project layout

```
backend/
├── manage.py
├── requirements.txt
├── config/                 # Django project (settings, urls, wsgi)
├── ml_models/              # trained .pkl artifacts (gitignored)
├── data/oulad/             # OULAD CSVs, downloaded on demand (gitignored)
└── analytics/              # main app
    ├── models.py           # Student, Assessment, RiskPrediction
    ├── serializers.py      # DRF (incl. predict request validation)
    ├── views.py            # /api/health/, /api/predict/
    ├── urls.py
    ├── admin.py            # free data-management UI
    └── ml/
        ├── features.py     # OULAD FEATURE_COLUMNS (single source of truth)
        ├── oulad.py        # download OULAD + build early-window features
        ├── service.py      # MLService: OULAD risk classifier (load + predict)
        ├── train.py        # OFFLINE training (on OULAD) -> risk_model.pkl
        ├── real_data.py    # parse & harmonize local gradebooks (dual-track)
        ├── train_real.py   # early-grade regression + cross-semester experiments
        ├── simulate_normalization.py  # controlled difficulty simulation
        └── grade_service.py  # GradeService: local grade regressor (load + predict)
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

# 4. Train a model on the OULAD dataset (downloads ~85 MB the first time,
#    writes ml_models\risk_model.pkl)
python -m analytics.ml.train
# python -m analytics.ml.train --csv data.csv   # or train on your own CSV

# 5. Run the server
python manage.py runserver
```

> The backend works **before** step 4 too: with no model file, `MLService`
> falls back to a transparent rule-based predictor.

## Data: OULAD

The model is trained on the **Open University Learning Analytics Dataset**
(OULAD, ~32k students, CC BY 4.0). `analytics/ml/oulad.py` downloads the 7
CSVs into `backend/data/oulad/` and engineers EARLY-WINDOW features (first 28
days only, to avoid leakage):

| Feature | Meaning |
|---------|---------|
| `total_clicks` | total VLE clicks in the first 28 days |
| `active_days` | distinct active days in the window |
| `mean_clicks_per_day` | engagement intensity |
| `early_avg_score` | mean score of early assessments |
| `num_prev_attempts` | prior attempts at the module |
| `studied_credits` | credits being studied |

Label `at_risk` = 1 if final result is Fail/Withdrawn, else 0.

```bash
python -m analytics.ml.oulad            # download + print a feature summary
python -m analytics.ml.oulad --no-download   # rebuild features from local CSVs
```

## API

| Method | Path                  | Purpose                                          |
|--------|-----------------------|--------------------------------------------------|
| GET    | `/api/health/`        | Liveness + status of both models                 |
| POST   | `/api/predict/`       | OULAD risk classifier: risk score + level        |
| POST   | `/api/predict-grade/` | Local regression: projected final grade + band   |

There are **two models**:
- **Risk classifier** (`rf-oulad-v1`, trained on OULAD) — `/api/predict/`
- **Grade regressor** (`ridge-grade-v1`, trained on the local gradebooks) —
  `/api/predict-grade/`: projects the final grade from leakage-free early
  features and maps it to a risk band (`<60` high, `60–70` medium, `≥70` low).

```bash
# Risk classifier (OULAD features)
curl -X POST http://localhost:8000/api/predict/ \
  -H "Content-Type: application/json" \
  -d '{"total_clicks":40,"active_days":3,"mean_clicks_per_day":13,"early_avg_score":35,"num_prev_attempts":1,"studied_credits":60}'

# Grade regressor (early-grade fractions in [0,1])
curl -X POST http://localhost:8000/api/predict-grade/ \
  -H "Content-Type: application/json" \
  -d '{"early_lab_avg":0.5,"early_assignment_pct":0.4,"early_quiz_avg":0.2}'
```

```json
// /api/predict-grade/ response
{
  "predicted_final_grade": 50.6,
  "risk_level": "high",
  "model_version": "ridge-grade-v1",
  "explanation": {"early_assignment_pct": -18.15, "early_quiz_avg": -6.71, "early_lab_avg": -3.27},
  "thresholds": {"high": "<60", "medium": "60-70", "low": ">=70"}
}
```

> The `explanation` for the regressor is the **exact** per-feature contribution
> in grade points (linear model: prediction = mean + Σ contributions). No SHAP
> needed.

Train the grade regressor (writes `ml_models/grade_model.pkl`):

```bash
python -m analytics.ml.train_real --save
```

## Where to go next

- Swap `RandomForestClassifier` for `XGBClassifier` in `train.py` (uncomment
  xgboost in requirements) for the "advanced model" comparison.
- Enable SHAP (uncomment in requirements) — `service._explain` uses it
  automatically when installed.
- Add a CSV-import endpoint / management command to populate `Student` and
  `Assessment` from real course data.
- Build dashboard aggregation endpoints (class mean, pass rate, distribution).
