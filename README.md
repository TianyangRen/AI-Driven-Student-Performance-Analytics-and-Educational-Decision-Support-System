# AI-Driven Student Performance Analytics — Backend

Django + Django REST Framework backend. Models are trained **offline** and
**loaded once** at startup; web requests only run fast inference.

| Component | What | Where |
|-----------|------|-------|
| **Disengagement track** | Rule-based missing-work detector (the behavioural risk) | in `/api/cohort-profile/` |
| Grade regressor (dual-head) | **Huber**: course total + strictly-future exam avg | `/api/predict-grade/` |
| Analytics layer | Outcome tiers + multi-label weakness boards + dispersion | `/api/cohort-profile/` |
| Early-warning timeline | Week-N snapshot models + prediction trajectories | `/api/warning-timeline/` |
| Assessment quality | CTT item analysis of the course's own assessments | `/api/assessment-quality/` |
| Instructor dashboard | All of the above, drill-down + sorting | `/dashboard/` |
| OULAD benchmark (research) | RandomForest risk classifier + normalization studies | scripts + docs only |

**Why two risk tracks**: grades concentrate at 70–96; the single historical
failure (final 33) was a mid-course dropout (15/26 components missing/zero) —
a behavioural event no grade model can learn from one example, but one that
missing-work rules catch directly (and earlier). So behavioural risk is
detected by rules; the grade model honestly does what it can: separate
relative standing among engaged students.

## Architecture

```
Browser → /dashboard/  (Django-served page, fetches the API below)
   │
Django + DRF
   ├─► GradeService   → grade_model.pkl  (Huber dual-head, local)   /api/predict-grade/
   └─► CohortService  → profiling.py (+ optional clustering)        /api/cohort-profile/
   │
   ▼
SQLite / PostgreSQL

offline training:  real_data.py → train_real.py --save → grade_model.pkl
research/benchmark: oulad.py → train.py → risk_model.pkl  (NOT served — its
                    VLE-clickstream features don't exist in local gradebooks)
```

Headline numbers (all leave-one-semester-out, Huber `huber-grade-v4`):
course-total head **MAE 4.46, R² 0.375** (Huber beats Ridge 4.52 and RF 4.85;
early inputs overlap ~8.8% of the total — disclosed; sensitivity with/without
the dropout case shipped in the artifact); exam head **MAE 8.08, R² 0.336 on a
zero-overlap, strictly-future target**; OULAD benchmark ROC-AUC ≈ 0.82.
Note: this course has **no final exam** — the course total (labs + assignments
+ quizzes + midterms + project) is the prediction target, which is exactly
what determines pass/fail.

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
    ├── serializers.py      # DRF request validation
    ├── views.py            # health / predict-grade / cohort-profile / dashboard
    ├── urls.py
    ├── admin.py            # free data-management UI
    ├── templates/analytics/dashboard.html   # instructor dashboard (vanilla JS)
    └── ml/
        ├── features.py     # OULAD FEATURE_COLUMNS (single source of truth)
        ├── oulad.py        # download OULAD + build early-window features
        ├── service.py      # OULAD classifier inference (retired from serving; benchmark)
        ├── train.py        # OFFLINE training (on OULAD) -> risk_model.pkl
        ├── real_data.py    # parse & harmonize local gradebooks (dual-track)
        ├── train_real.py   # early-grade regression + cross-semester experiments
        ├── simulate_normalization.py  # controlled difficulty simulation
        ├── oulad_normalization.py     # normalization effect on real OULAD cohorts
        ├── evaluate_probabilistic.py  # interval coverage / CRPS / Brier evaluation
        ├── grade_service.py  # GradeService: local grade regressor (load + predict)
        ├── clustering.py     # archetype discovery: silhouette k, stability ARI
        ├── profiling.py      # profiling + weakness boards + tiers + dispersion
        ├── cohort_service.py # cached cohort_profile() for the API
        ├── engagement.py     # disengagement detector (behavioural risk track)
        ├── snapshots.py      # week-N snapshot models + trajectories + alerts
        └── assessment_quality.py  # CTT item analysis (difficulty/discrimination)
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

# 4. Train the grade model (dual-head, from the local gradebooks in real_data/;
#    writes ml_models\grade_model.pkl)
python -m analytics.ml.train_real --save

# 5. Run the server, then open http://127.0.0.1:8000/  (-> /dashboard/)
python manage.py runserver

# Optional (research benchmark): train the OULAD classifier
# python -m analytics.ml.train        # downloads ~85 MB the first time
```

> Without step 4, `/api/predict-grade/` returns 503 and the dashboard's
> projected column is unavailable — run `train_real --save` first.

## Data: OULAD (research benchmark — not served)

The OULAD risk classifier is a **methodological benchmark**, retired from the
API: its features are VLE clickstream, which local gradebooks don't have. It
remains the validation testbed (ROC-AUC ≈ 0.82; normalization reproduction on
22 real divergent cohorts). Trained on the **Open University Learning
Analytics Dataset** (~32k students, CC BY 4.0). `analytics/ml/oulad.py`
downloads the 7 CSVs into `backend/data/oulad/` and engineers EARLY-WINDOW
features (first 28 days only, to avoid leakage):

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

> **Frontend collaborators**: full request/response reference with real
> payload samples, enums, color-scale rules, and error contracts is in
> [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md).

| Method | Path                  | Purpose                                          |
|--------|-----------------------|--------------------------------------------------|
| GET    | `/api/health/`        | Liveness + grade-model status                    |
| POST   | `/api/predict-grade/` | Per-student projection: course total + exam avg  |
| GET    | `/api/cohort-profile/`| Whole-class analysis: tiers, weakness boards     |
| GET    | `/api/warning-timeline/` | Week-N curve + trajectories + declining alerts |
| GET    | `/api/assessment-quality/` | CTT item analysis (difficulty/discrimination/ceiling) |
| GET    | `/dashboard/`         | Instructor dashboard (root `/` redirects here)   |

```bash
# Grade regressor (early-grade fractions in [0,1])
curl -X POST http://localhost:8000/api/predict-grade/ \
  -H "Content-Type: application/json" \
  -d '{"early_lab_avg":0.5,"early_assignment_pct":0.4,"early_quiz_avg":0.2}'
```

```json
// /api/predict-grade/ response (probabilistic, dual-head, huber-grade-v4)
{
  "predicted_course_total": 47.7,
  "prediction_interval_80": [40.2, 55.2],
  "prob_below_60": 0.98,
  "prob_below_70": 0.999,
  "uncertainty_sigma": 5.86,
  "data_coverage": "full",
  "risk_level": "high",
  "exam_head": {"predicted_exam_avg": 30.1, "exam_interval_80": [16.7, 43.5]},
  "target_note": "Primary target = official course total ... no final exam ...",
  "model_version": "huber-grade-v4",
  "explanation": {"early_assignment_pct": -18.15, "early_quiz_avg": -6.71, "early_lab_avg": -3.27},
  "thresholds": {"high": "<60", "medium": "60-70", "low": ">=70"}
}
```

> Two heads: `predicted_course_total` is the official course total (what
> pass/fail is decided on; early inputs are ~8.8% of it — disclosed).
> `exam_head` predicts the strictly-future Midterm I+II average with **zero**
> input overlap (LOSO MAE 8.08, R² 0.34) — proof of genuine forward prediction. Both heads use Huber (robust) loss.

> The `explanation` for the regressor is the **exact** per-feature contribution
> in grade points (linear model: prediction = mean + Σ contributions). No SHAP
> needed.
>
> The forecast is **probabilistic**: σ comes from leave-one-semester-out
> residuals, giving an 80% prediction interval and P(final < threshold) —
> a failure probability that requires no failing samples to train on.
> Evaluate it with `python -m analytics.ml.evaluate_probabilistic`
> (interval coverage, CRPS, Brier).
>
> **Missing-data honesty**: absent features are imputed with training means but
> never silently — the response carries `data_coverage`
> (full / partial / insufficient), `missing_features`, and a warning. A student
> with no early submissions is not an "average" student; missing work is itself
> a risk signal.

Train the grade regressor (writes `ml_models/grade_model.pkl`):

```bash
python -m analytics.ml.train_real --save
```

### Cohort analysis — `/api/cohort-profile/`

Whole-class analysis powering the dashboard. **Retrospective view**: dimension
percentiles use full-term official subtotals (`meta.view = "retrospective"`) —
an end-of-course review; for mid-semester early warning use
`/api/warning-timeline/`. Returns:
- `class_stats` — n, projected mean, score spread (CV), % at risk, uneven
  count, students weak in ≥2 dimensions
- `groups` — outcome tiers on two bases: `outcome_final` (official grade) and
  `outcome_projected` (early-features projection). Each group carries
  per-dimension averages, homogeneity σ, risk counts, full member list, and
  each member's multi-label `weak_in` flags.
- `weakness_boards` — **the primary "who is weak in X" grouping**: one board
  per dimension (bottom cohort quartile), multi-label by design (a student
  weak in Quiz *and* Mid appears on both, with `also_weak_in` cross-links).
  Deterministic and explainable — chosen over clustering because exclusive
  partitions fit the instructor's per-dimension questions poorly.
- `disengagement` — **the behavioural risk track**: rule-based missing-work
  flags (7 disengaged + 8 gaps on this data; the historical dropout tops the
  list with 14 misses). Ceiling components double as attendance sensors.
- `cluster_analysis` — only with `?clusters=1`: the exploratory KMeans
  archetypes with honest validity metadata (silhouette favours k=2, bootstrap
  ARI ≈ 0.64, borderline tags). A research lens, not the product grouping.

```bash
curl http://localhost:8000/api/cohort-profile/              # tiers + boards (cached)
curl "http://localhost:8000/api/cohort-profile/?clusters=1" # + exploratory clusters
curl "http://localhost:8000/api/cohort-profile/?refresh=1"  # recompute
```

Dispersion is wired to action: class CV (uniform vs split teaching), group
homogeneity (one plan vs differentiate), student consistency (fix one component
vs broad support).

### Early-warning timeline — `/api/warning-timeline/`

Week-N snapshot models (W3/W6/W9/W12: what data exists by then → Ridge → LOSO):

| Snapshot | Data | LOSO MAE | R² |
|---|---|---|---|
| W3 (~week 3) | labs 1-2, quiz 1 | 4.48 | 0.31 |
| W6 (~week 6) | + assignment 1, quiz 2 | 4.35 | 0.38 |
| W9 (~week 9) | + **Midterm I** | **2.99** | **0.66** |
| W12 (~week 12) | + more coursework | 2.87 | 0.69 |

Reliable warning from ~week 3; precision doubles once Midterm I lands.
Per-student **trajectories** use out-of-fold predictions; a drop ≥5 points
between snapshots flags a *declining* student (25 flagged; their mean final
71.5 vs 79.9 for stable — the alert carries real signal). Timing assumption
disclosed: quiz dates are real, lab/assignment pacing approximated.

### Assessment quality — `/api/assessment-quality/`

Classical Test Theory item analysis of the course's own instruments:
difficulty, item-total discrimination, ceiling rate, per component pooled over
4 semesters. Real findings: **all 10 labs + all 4 assignments + workshops are
at ceiling** (they measure compliance, not ability); **Quiz 1 is the best
early signal (r = 0.60)**; midterm parts discriminate most (r 0.60–0.81,
part-whole caveat disclosed). Decision support for the *course design*, not
just the students.

## Roadmap

- **Gradebook upload** — CSV import endpoint to populate `Student` /
  `Assessment` so new semesters flow in without touching `real_data/`.
- **Longitudinal features on OULAD** — prior-term GPA / trend slope, where
  students can actually be tracked across offerings.
- **Deployment hygiene** — auth, `DEBUG=False`, secret management, and
  configurable risk thresholds before any real classroom use.
