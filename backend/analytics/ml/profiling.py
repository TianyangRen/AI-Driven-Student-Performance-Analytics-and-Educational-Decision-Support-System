"""Cohort profiling — assembles everything the dashboard needs, from real data.

Per student:
  * within-cohort percentile in each dimension (Labs/Quiz/Assign/Mid)
  * projected final grade + 80% interval (from the grade regression model)
  * risk band, weakest dimension, consistency (std across dimensions)

Per group (two grouping modes):
  * outcome tiers  — by projected grade (Excellent/On track/Borderline/At risk)
  * profile clusters — archetypes from clustering.py
  Each group carries homogeneity sigma (avg within-group dimension spread) so
  the instructor knows whether the group is a coherent unit or hides sub-types.

Dispersion is wired to ACTION:
  * class CV          -> uniform vs split teaching
  * group homogeneity -> one plan vs differentiate / look inside
  * student consistency -> fix one component vs broad support

Run:  python -m analytics.ml.profiling
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

try:
    from analytics.ml.real_data import harmonize_all
    from analytics.ml import clustering
except ModuleNotFoundError:  # pragma: no cover
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from analytics.ml.real_data import harmonize_all
    from analytics.ml import clustering

# Profiling dimensions = the four categories present in every offering.
DIMS = ["abs_labs", "abs_quizzes", "abs_assignments", "abs_midterm"]
DIM_LABELS = {"abs_labs": "Labs", "abs_quizzes": "Quiz",
              "abs_assignments": "Assign", "abs_midterm": "Mid"}
PCTL = [d + "_pctl" for d in DIMS]
GRADE_MODEL = Path(__file__).resolve().parents[2] / "ml_models" / "grade_model.pkl"

# Dispersion -> tag thresholds (percentile points), tuned to real output below.
HOMOG = {"tight": 16, "mixed": 24}        # group avg within-dim std
CONSISTENCY_UNEVEN = 20                    # student std across dims

# Multi-label weakness boards: a student is "weak in <dim>" when their
# within-cohort percentile in that dimension is in the bottom quartile.
# Deterministic, explainable, and a student can be weak in several dims —
# this matches the instructor question "who is weak in quizzes / midterms?"
# better than a forced exclusive partition (clustering).
WEAK_PCTL = 25.0

# Archetype count: k=4 chosen for actionability (separates assignment-skippers,
# exam-strugglers, at-risk, strong). k=2 is more stable; see clustering_meta.
DEFAULT_K = 4

# Cluster membership is NOT solid (bootstrap ARI ~0.64 at k=4). Students whose
# per-sample silhouette falls below this are tagged "borderline" so the UI can
# de-emphasize their group assignment instead of presenting it as fact.
SIL_BORDERLINE = 0.10

TIER_BINS = [-1, 60, 70, 80, 101]
TIER_ORDER = ["excellent", "ontrack", "borderline", "atrisk"]
TIER_LABELS_CUT = ["atrisk", "borderline", "ontrack", "excellent"]
TIER_NAMES = {"excellent": "Excellent", "ontrack": "On track",
              "borderline": "Borderline", "atrisk": "At risk"}


def _std(a):
    a = np.asarray(a, float)
    return float(np.sqrt(np.mean((a - a.mean()) ** 2))) if len(a) else 0.0


def build_profiles() -> pd.DataFrame:
    df = harmonize_all()

    # Within-cohort percentile per dimension (cohort-referenced, comparable).
    g = df.groupby("offering")
    for d in DIMS:
        df[d] = df[d].fillna(g[d].transform("median"))
        df[d + "_pctl"] = (g[d].rank(pct=True) * 100).round(1)

    # Projected final grade + 80% interval from the regression model.
    import joblib
    art = joblib.load(GRADE_MODEL)
    feats, sigma = art["features"], art.get("residual_std", 6.0)
    pred = art["model"].predict(df[feats].to_numpy())
    df["projected"] = np.clip(pred, 0, 100).round(1)
    z80 = 1.2816
    df["proj_lo"] = np.clip(df["projected"] - z80 * sigma, 0, 100).round(0)
    df["proj_hi"] = np.clip(df["projected"] + z80 * sigma, 0, 100).round(0)

    # Risk band, weakest dimension, consistency (spread across dims).
    df["risk"] = pd.cut(df["projected"], [-1, 60, 70, 101],
                        labels=["high", "medium", "low"])
    df["weakest"] = df[PCTL].idxmin(axis=1).map(
        {p: DIM_LABELS[d] for p, d in zip(PCTL, DIMS)})
    df["consistency"] = df[PCTL].apply(lambda r: _std(r.values), axis=1).round(1)
    df["consistency_tag"] = np.where(df["consistency"] >= CONSISTENCY_UNEVEN,
                                     "uneven", "balanced")

    # Multi-label weakness flags (bottom quartile of cohort, per dimension).
    for d in DIMS:
        df[f"weak_{DIM_LABELS[d]}"] = df[d + "_pctl"] <= WEAK_PCTL
    df["weak_in"] = df.apply(
        lambda r: [DIM_LABELS[d] for d in DIMS if r[f"weak_{DIM_LABELS[d]}"]],
        axis=1)

    # Behavioural track: disengagement flags (missing/zero submissions).
    from analytics.ml.engagement import engagement_table

    eng = engagement_table()[["student_id", "offering", "missed_total",
                              "missed_late", "engagement"]]
    df = df.merge(eng, on=["student_id", "offering"], how="left")
    df["engagement"] = df["engagement"].fillna("ok")
    return df


def _jsonable(o):
    """Recursively convert numpy scalars to native types so DRF can render."""
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(x) for x in o]
    if isinstance(o, np.floating):
        return round(float(o), 3)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, float):
        return round(o, 3)
    return o


def _homog_tag(sigma: float) -> str:
    if sigma < HOMOG["tight"]:
        return "tight"
    if sigma < HOMOG["mixed"]:
        return "mixed"
    return "wide"


def _make_groups(df, assign_col, order, names):
    has_membership = "membership" in df.columns
    groups = []
    for key in order:
        rows = df[df[assign_col] == key]
        if not len(rows):
            continue
        dim_avgs = {DIM_LABELS[d]: round(rows[d + "_pctl"].mean(), 1) for d in DIMS}
        # group homogeneity = avg within-group spread across dimensions
        homog = float(np.mean([_std(rows[d + "_pctl"].values) for d in DIMS]))
        members = []
        for r in rows.to_dict("records"):
            m = {"id": r["student_id"], "offering": r["offering"],
                 "dims": {DIM_LABELS[d]: r[d + "_pctl"] for d in DIMS},
                 "projected": r["projected"], "lo": r["proj_lo"], "hi": r["proj_hi"],
                 "risk": str(r["risk"]), "weakest": r["weakest"],
                 "weak_in": r["weak_in"], "engagement": r["engagement"],
                 "consistency": r["consistency"], "consistency_tag": r["consistency_tag"]}
            if has_membership:
                m["membership"] = r["membership"]
            members.append(m)
        group = {
            "key": key, "name": names.get(key, key), "n": int(len(rows)),
            "dim_avgs": dim_avgs,
            "projected_avg": round(rows["projected"].mean(), 1),
            "homogeneity": round(homog, 1), "homog_tag": _homog_tag(homog),
            "n_high": int((rows["risk"] == "high").sum()),
            "n_medium": int((rows["risk"] == "medium").sum()),
            "members": members,
        }
        if has_membership:
            group["n_borderline"] = int((rows["membership"] == "borderline").sum())
        groups.append(group)
    return groups


def _weakness_boards(df) -> list[dict]:
    """One board per dimension: the students in the cohort's bottom quartile.

    Multi-label by design — a student weak in both Quiz and Mid appears on
    both boards, with the other memberships listed in also_weak_in.
    """
    boards = []
    for d in DIMS:
        label = DIM_LABELS[d]
        rows = df[df[f"weak_{label}"]].sort_values(d + "_pctl")
        boards.append({
            "dim": label, "n": int(len(rows)),
            "share_pct": round(len(rows) / len(df) * 100, 1),
            "definition": f"within-cohort percentile <= {WEAK_PCTL:.0f} in {label}",
            "members": [
                {"id": r["student_id"], "offering": r["offering"],
                 "pctl": r[d + "_pctl"], "projected": r["projected"],
                 "risk": str(r["risk"]),
                 "also_weak_in": [w for w in r["weak_in"] if w != label]}
                for r in rows.to_dict("records")
            ],
        })
    return boards


def _cluster_analysis(df, k: int) -> dict:
    """Exploratory archetype clustering (research lens, NOT the primary
    grouping). Kept out of the default API payload: silhouette favours k=2,
    bootstrap ARI at k=4 is ~0.64, and exclusive partitions fit the
    instructor's per-dimension questions worse than the weakness boards.
    """
    from sklearn.metrics import silhouette_samples

    X = df[PCTL].to_numpy()
    sel = clustering.choose_k(X)
    fitres = clustering.fit(X, k)
    df["cluster"] = fitres["labels"]
    df["membership"] = np.where(
        silhouette_samples(X, fitres["labels"]) < SIL_BORDERLINE,
        "borderline", "core")
    cluster_names = {c: clustering.characterize(fitres["centroids"][c])["name"]
                     for c in range(k)}
    order = sorted(range(k), key=lambda c: -np.mean(fitres["centroids"][c]))
    groups = _make_groups(df, "cluster", order, cluster_names)
    stability = clustering.stability_ari(X, k)
    presence = {cluster_names[c]: int(df[df.cluster == c]["offering"].nunique())
                for c in range(k)}
    return {
        "groups": groups,
        "meta": {
            "k": k, "best_k_by_silhouette": sel["best_k"],
            "silhouette_by_k": {str(kk): round(v, 3)
                                for kk, v in sel["silhouette_by_k"].items()},
            "silhouette_at_k": round(sel["silhouette_by_k"][k], 3),
            "stability_ari": round(stability, 3),
            "cohort_presence": presence,
            "n_borderline_total": int((df["membership"] == "borderline").sum()),
            "note": (
                f"Exploratory only (bootstrap ARI {round(stability, 2)}; "
                f"silhouette favours k={sel['best_k']}). Weakness boards are "
                f"the primary grouping; treat cluster rosters as tentative."
            ),
        },
    }


def _disengagement_block(df) -> dict:
    """Behavioural risk track for the API: who stopped submitting.

    Rides ABOVE the grade model: the one historical failure was a mid-course
    dropout, which grades can't learn from one example but missing work shows
    directly. Ceiling components (labs/assignments) double as attendance
    sensors: a zero there almost certainly means 'did not submit'.
    """
    from analytics.ml.engagement import RULE

    flagged = df[df["engagement"] != "ok"].sort_values(
        ["engagement", "missed_late"], ascending=[True, False])
    return {
        "rule": RULE,
        "n_disengaged": int((df["engagement"] == "disengaged").sum()),
        "n_gaps": int((df["engagement"] == "gaps").sum()),
        "members": [
            {"id": r["student_id"], "offering": r["offering"],
             "tag": r["engagement"], "missed_total": int(r["missed_total"]),
             "missed_late": int(r["missed_late"]),
             "projected": r["projected"], "final": r["final_grade"],
             "risk": str(r["risk"])}
            for r in flagged.to_dict("records")
        ],
    }


def cohort_profile(k: int = DEFAULT_K, include_clusters: bool = False) -> dict:
    df = build_profiles()

    # --- outcome tiers: two bases (final grade & projected grade) --------- #
    df["tier_final"] = pd.cut(df["final_grade"], TIER_BINS, labels=TIER_LABELS_CUT)
    df["tier_proj"] = pd.cut(df["projected"], TIER_BINS, labels=TIER_LABELS_CUT)
    outcome_final = _make_groups(df, "tier_final", TIER_ORDER, TIER_NAMES)
    outcome_projected = _make_groups(df, "tier_proj", TIER_ORDER, TIER_NAMES)

    boards = _weakness_boards(df)

    proj = df["projected"].to_numpy()
    result = {
        "meta": {
            "view": "retrospective",
            "data_basis": (
                "Dimension percentiles and weakness boards use FULL-TERM "
                "official category subtotals — an end-of-course review view. "
                "For mid-semester early warning use /api/warning-timeline/ "
                "(week-N snapshot models + trajectories). The 'projected' "
                "column is the early-features regression and keeps its "
                "early-warning meaning. Note: this course has no final exam; "
                "the course total = labs + assignments + quizzes + midterms "
                "+ project."
            ),
        },
        "class_stats": {
            "n": int(len(df)),
            "projected_mean": round(float(proj.mean()), 1),
            "cv_pct": round(float(proj.std() / proj.mean() * 100), 1),
            "pct_at_risk": round(float((df["risk"] == "high").mean() * 100), 1),
            "n_uneven": int((df["consistency_tag"] == "uneven").sum()),
            "n_multi_weak": int((df["weak_in"].apply(len) >= 2).sum()),
            "n_disengaged": int((df["engagement"] == "disengaged").sum()),
        },
        "groups": {"outcome_final": outcome_final,
                   "outcome_projected": outcome_projected},
        "weakness_boards": boards,
        "disengagement": _disengagement_block(df),
    }
    if include_clusters:
        result["cluster_analysis"] = _cluster_analysis(df, k)
    return _jsonable(result)


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Cohort profiling summary.")
    ap.add_argument("--clusters", action="store_true",
                    help="Also run the exploratory archetype clustering.")
    args = ap.parse_args()

    p = cohort_profile(include_clusters=args.clusters)
    print(f"[view: {p['meta']['view']}] {p['meta']['data_basis']}\n")
    cs = p["class_stats"]
    print(f"=== Class ({cs['n']} students) ===")
    print(f"  projected mean {cs['projected_mean']} | score spread CV {cs['cv_pct']}% "
          f"| at risk {cs['pct_at_risk']}% | uneven {cs['n_uneven']} "
          f"| weak in >=2 dims {cs['n_multi_weak']}")

    dz = p["disengagement"]
    print(f"\n=== Behavioural track: disengagement ===")
    print(f"  disengaged {dz['n_disengaged']} | gaps {dz['n_gaps']}  ({dz['rule']})")
    for m in dz["members"][:5]:
        print(f"    {m['id']} ({m['offering'].replace('Data-','')}): {m['tag']}, "
              f"{m['missed_total']} misses ({m['missed_late']} late), final {m['final']:.0f}")

    print("\n=== Weakness boards (bottom quartile per dimension, multi-label) ===")
    for b in p["weakness_boards"]:
        multi = sum(1 for m in b["members"] if m["also_weak_in"])
        print(f"  {b['dim']:7s} n={b['n']:3d} ({b['share_pct']}%)  "
              f"{multi} also weak elsewhere")

    for mode in ["outcome_final", "outcome_projected"]:
        print(f"\n=== Groups — {mode} ===")
        for grp in p["groups"][mode]:
            da = grp["dim_avgs"]
            print(f"  {grp['name']:12s} n={grp['n']:3d}  "
                  f"L{da['Labs']:.0f} Q{da['Quiz']:.0f} A{da['Assign']:.0f} M{da['Mid']:.0f}  "
                  f"proj {grp['projected_avg']:.0f}  homog σ{grp['homogeneity']:.0f}({grp['homog_tag']})  "
                  f"{grp['n_high']} high")

    if args.clusters:
        ca = p["cluster_analysis"]
        cm = ca["meta"]
        print(f"\n=== Exploratory clusters (research lens) ===")
        print(f"  {cm['note']}")
        for grp in ca["groups"]:
            da = grp["dim_avgs"]
            print(f"  {grp['name']:26s} n={grp['n']:3d}  "
                  f"L{da['Labs']:.0f} Q{da['Quiz']:.0f} A{da['Assign']:.0f} M{da['Mid']:.0f}  "
                  f"{grp.get('n_borderline', 0)} borderline")


if __name__ == "__main__":
    main()
