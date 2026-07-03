"""Week-N snapshot models + prediction trajectories (early-warning timeline).

Turns the system from a single fixed "early" prediction into a TIMELINE:

  W3  (~week 3)  : labs 1-2,            quiz 1
  W6  (~week 6)  : labs 1-4, assign 1,  quizzes 1-2      (= the deployed set)
  W9  (~week 9)  : labs 1-6, assign 1-2, quizzes 1-3, + Midterm I
  W12 (~week 12) : labs 1-8, assign 1-3, quizzes 1-4, + Midterm I

For each snapshot a Ridge model predicts the final course total, evaluated
with leave-one-semester-out (LOSO). Two products:

  1. The warning-time curve — "how early can we warn, and at what accuracy?"
     (MAE / R^2 per snapshot).
  2. Per-student trajectories — the sequence of LOSO out-of-fold predictions
     across snapshots. A drop of >= ALERT_DROP points between consecutive
     snapshots flags a DECLINING student even if their level is still "fine".

Timing assumptions (disclosed): quiz order comes from real due dates parsed
from column names; labs are assumed ~weekly and assignments ~evenly spaced,
so the week labels are approximate. Trajectories use OUT-OF-FOLD predictions
(the model never saw that student's semester), so deltas are honest.

    python -m analytics.ml.snapshots
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold

try:
    from analytics.ml.real_data import (
        REAL_DATA_DIR, _extract_date, _final_grade, _parse_grade_header, _to_num,
    )
    from analytics.ml.train_real import make_estimator, make_pipeline
except ModuleNotFoundError:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from analytics.ml.real_data import (
        REAL_DATA_DIR, _extract_date, _final_grade, _parse_grade_header, _to_num,
    )
    from analytics.ml.train_real import make_estimator, make_pipeline

# (key, approx_week, n_labs, n_assignments, n_quizzes, include_midterm1)
SNAPSHOTS = [
    ("W3", 3, 2, 0, 1, False),
    ("W6", 6, 4, 1, 2, False),
    ("W9", 9, 6, 2, 3, True),
    ("W12", 12, 8, 3, 4, True),
]

ALERT_DROP = 5.0   # projected-total drop (points) between snapshots -> alert


# --------------------------------------------------------------------------- #
# Feature building
# --------------------------------------------------------------------------- #
def _component_fracs(df: pd.DataFrame):
    """Return {kind: [(order_key, Series of fractions)]} for one offering."""
    labs, assigns, quizzes, mid1 = [], [], [], None
    for col in df.columns:
        meta = _parse_grade_header(col)
        if not meta:
            continue
        name = meta["name"]
        frac = (_to_num(df[col]) / meta["max_points"]).clip(0, 1.5)
        m = re.match(r"^Lab (\d+)$", name)
        if m:
            labs.append((int(m.group(1)), frac))
            continue
        m = re.match(r"^Assignment (\d+)$", name)
        if m:
            assigns.append((int(m.group(1)), frac))
            continue
        if meta["category"] in ("RLQs", "Quizzes", "Quiz") and "(Total)" not in name:
            quizzes.append((_extract_date(name) or pd.Timestamp.max, frac))
            continue
        if name == "Mid-Term Exam I (Total)":
            mid1 = frac
    labs.sort(key=lambda x: x[0])
    assigns.sort(key=lambda x: x[0])
    quizzes.sort(key=lambda x: x[0])
    return labs, assigns, quizzes, mid1


def _avg_first(items, n):
    if n <= 0 or not items:
        return None
    mat = pd.concat([s for _, s in items[:n]], axis=1)
    return mat.mean(axis=1)


def build_snapshot_table() -> pd.DataFrame:
    """One row per student; per-snapshot feature columns + final_grade."""
    frames = []
    for path in sorted(REAL_DATA_DIR.glob("Data-Part*.csv")):
        raw = pd.read_csv(path)
        raw = raw[raw.iloc[:, 0].notna()]
        labs, assigns, quizzes, mid1 = _component_fracs(raw)
        out = pd.DataFrame({
            "student_id": raw.iloc[:, 0].astype(str).str.lstrip("#").str.strip(),
            "offering": path.stem,
            "final_grade": _final_grade(raw).values,
        })
        for key, _wk, nl, na, nq, use_m1 in SNAPSHOTS:
            for feat, series in [("labs", _avg_first(labs, nl)),
                                 ("assign", _avg_first(assigns, na)),
                                 ("quiz", _avg_first(quizzes, nq))]:
                if series is not None:
                    out[f"{key}_{feat}"] = series.values
            if use_m1 and mid1 is not None:
                out[f"{key}_mid1"] = mid1.values
        frames.append(out[out["final_grade"].notna()])
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- #
# Timeline: per-snapshot LOSO models + trajectories
# --------------------------------------------------------------------------- #
def warning_timeline() -> dict:
    df = build_snapshot_table()
    y = df["final_grade"].to_numpy()
    groups = df["offering"].to_numpy()
    gkf = GroupKFold(n_splits=df["offering"].nunique())

    curve, oof = [], {}
    for key, wk, nl, na, nq, use_m1 in SNAPSHOTS:
        cols = [c for c in df.columns if c.startswith(key + "_")]
        X = df[cols].to_numpy()
        preds = np.empty(len(df))
        for tr, te in gkf.split(X, y, groups):
            pipe = make_pipeline(make_estimator())
            pipe.fit(X[tr], y[tr])
            preds[te] = pipe.predict(X[te])
        preds = np.clip(preds, 0, 100)
        oof[key] = preds
        curve.append({
            "snapshot": key, "approx_week": wk,
            "features": [c.split("_", 1)[1] for c in cols],
            "mae": round(float(mean_absolute_error(y, preds)), 2),
            "r2": round(float(r2_score(y, preds)), 3),
            "sigma": round(float(np.std(y - preds, ddof=1)), 2),
        })

    keys = [s[0] for s in SNAPSHOTS]
    trajectories, declining = [], []
    for i in range(len(df)):
        seq = {k: round(float(oof[k][i]), 1) for k in keys}
        deltas = [seq[keys[j + 1]] - seq[keys[j]] for j in range(len(keys) - 1)]
        max_drop = round(min(deltas), 1)
        t = {"id": df["student_id"].iat[i], "offering": df["offering"].iat[i],
             "preds": seq, "final": round(float(y[i]), 1),
             "max_drop": max_drop, "declining": bool(max_drop <= -ALERT_DROP)}
        trajectories.append(t)
        if t["declining"]:
            declining.append(t)
    declining.sort(key=lambda t: t["max_drop"])

    # Do declining students actually end lower? (given same W6 level)
    dec = [t for t in trajectories if t["declining"]]
    stable = [t for t in trajectories if not t["declining"]]
    check = {
        "n_declining": len(dec),
        "declining_mean_final": round(float(np.mean([t["final"] for t in dec])), 1) if dec else None,
        "stable_mean_final": round(float(np.mean([t["final"] for t in stable])), 1),
    }

    return {
        "meta": {
            "assumption": ("Quiz timing from real due dates; labs assumed "
                           "~weekly, assignments ~evenly spaced, so week labels "
                           "are approximate. Trajectory predictions are LOSO "
                           "out-of-fold (never trained on that semester)."),
            "alert_rule": f"drop >= {ALERT_DROP:.0f} points between consecutive snapshots",
        },
        "curve": curve,
        "trajectories": trajectories,
        "declining": declining,
        "sanity_check": check,
    }


class TimelineService:
    _cache: dict | None = None

    @classmethod
    def get(cls, refresh: bool = False) -> dict:
        if refresh or cls._cache is None:
            cls._cache = warning_timeline()
        return cls._cache


def main():
    t = warning_timeline()
    print(t["meta"]["assumption"], "\n")
    print("=== Warning-time curve (LOSO) — how early, how accurate? ===")
    print(f"{'snap':>4s} {'~wk':>4s} {'MAE':>6s} {'R2':>7s} {'sigma':>6s}  features")
    for c in t["curve"]:
        print(f"{c['snapshot']:>4s} {c['approx_week']:4d} {c['mae']:6.2f} "
              f"{c['r2']:7.3f} {c['sigma']:6.2f}  {'+'.join(c['features'])}")
    sc = t["sanity_check"]
    print(f"\n=== Trajectory alerts (drop >= {ALERT_DROP:.0f} pts) ===")
    print(f"  declining: {sc['n_declining']} students | mean final "
          f"{sc['declining_mean_final']} vs stable {sc['stable_mean_final']}")
    print("  worst 5 declines:")
    for d in t["declining"][:5]:
        seq = " → ".join(f"{d['preds'][k]:.0f}" for k in d["preds"])
        print(f"    {d['id']} ({d['offering'].replace('Data-','')}): {seq}  "
              f"(max drop {d['max_drop']}, final {d['final']})")


if __name__ == "__main__":
    main()
