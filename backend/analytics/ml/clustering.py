"""Student archetype discovery (clustering) with honest validity checks.

Clusters students on their within-cohort per-dimension percentile profile
(Labs / Quiz / Assign / Midterm). To avoid "just ran KMeans", every run reports:

  * k chosen by silhouette score (not hand-picked)
  * cluster characterization (auto-named from the centroid profile)
  * bootstrap stability (Adjusted Rand Index across resamples)
  * cross-cohort presence (do archetypes appear in every semester, or are
    they an artifact of one cohort?)

Clustering on a small cohort is EXPLORATORY/descriptive — the report says so.
The per-dimension profiling and outcome tiers (profiling.py) are the robust
parts; clustering adds the archetype lens on top.
"""
from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score

DIM_LABELS = ["Labs", "Quiz", "Assign", "Mid"]


def choose_k(X: np.ndarray, k_min: int = 2, k_max: int = 6) -> dict:
    """Pick k by best silhouette score. Returns scores for every k too."""
    scores = {}
    for k in range(k_min, min(k_max, len(X) - 1) + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(X)
        scores[k] = float(silhouette_score(X, labels))
    best_k = max(scores, key=scores.get)
    return {"best_k": best_k, "silhouette_by_k": scores}


def fit(X: np.ndarray, k: int) -> dict:
    """Fit KMeans; return labels, centroids, and per-cluster sizes."""
    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = km.fit_predict(X)
    return {"labels": labels, "centroids": km.cluster_centers_, "model": km}


def characterize(centroid: np.ndarray) -> dict:
    """Turn a centroid (4 dim percentiles, 0-100) into a human label.

    Names by overall level + the shape of strengths/weaknesses, so the label
    is interpretable to an instructor (not 'cluster 2').
    """
    vals = {DIM_LABELS[i]: float(centroid[i]) for i in range(len(DIM_LABELS))}
    overall = float(np.mean(centroid))
    lo_dim = min(vals, key=vals.get)
    spread = float(max(centroid) - min(centroid))
    coursework = (vals["Labs"] + vals["Assign"]) / 2
    exams = (vals["Quiz"] + vals["Mid"]) / 2

    level = "Strong" if overall >= 60 else "At-risk" if overall <= 38 else "Mid"
    if spread < 12:
        name = f"{level}, balanced"
    elif coursework - exams >= 15:
        name = f"{level}, exam-weak"
    elif exams - coursework >= 15:
        name = f"{level}, coursework-weak"
    else:
        name = f"{level}, weak in {lo_dim.lower()}"
    return {"name": name, "overall": round(overall, 1), "profile": {k: round(v, 1) for k, v in vals.items()}}


def stability_ari(X: np.ndarray, k: int, n_boot: int = 60, seed: int = 42) -> float:
    """Bootstrap stability: refit on resamples, predict on full data, compare
    to the reference labels via Adjusted Rand Index. ~1.0 = very stable,
    ~0 = no better than chance. A standard honest cluster-validity measure.
    """
    rng = np.random.default_rng(seed)
    ref = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)
    aris = []
    n = len(X)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)  # resample with replacement
        km = KMeans(n_clusters=k, n_init=10, random_state=int(rng.integers(1e6)))
        km.fit(X[idx])
        aris.append(adjusted_rand_score(ref, km.predict(X)))
    return float(np.mean(aris))
