"""Evaluate the PROBABILISTIC grade forecast (Variant A).

The service reports a Gaussian predictive distribution N(mu, sigma^2) per
student (mu = Ridge prediction, sigma = LOSO residual std). This script checks
whether those distributions are HONEST, using nested leave-one-semester-out:

  outer loop : hold out one semester; fit Ridge on the remaining three.
  inner loop : estimate sigma from leave-one-semester-out residuals WITHIN the
               three training semesters only (the held-out semester never
               touches its own sigma -> no optimistic bias).

Metrics (pooled over all held-out students):
  * Interval coverage  — a nominal 50/80/90% interval should contain about
    50/80/90% of true grades. Over-coverage = intervals too wide; under = too
    narrow (overconfident).
  * CRPS (Continuous Ranked Probability Score, closed form for a Gaussian) —
    proper scoring rule for the whole distribution; lower is better. Reported
    against a climatological baseline N(train_mean, train_std).
  * Brier score for the event {final < t}, t in {60, 70} — proper scoring rule
    for the risk probabilities the API exposes; compared with the base-rate
    baseline. (Caveat: only 2 students sit below 60, so that threshold is
    reported for completeness, not for strong conclusions.)

    cd ml-service
    python -m analytics.ml.evaluate_probabilistic
"""
from __future__ import annotations

import math
import warnings

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

warnings.filterwarnings("ignore")

try:
    from analytics.ml.real_data import harmonize_all
    from analytics.ml.train_real import RAW_FEATURES, TARGET, make_estimator, make_pipeline
except ModuleNotFoundError:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from analytics.ml.real_data import harmonize_all
    from analytics.ml.train_real import RAW_FEATURES, TARGET, make_estimator, make_pipeline

Z = {0.50: 0.6745, 0.80: 1.2816, 0.90: 1.6449}


def _phi(z):  # standard normal pdf
    return np.exp(-0.5 * z**2) / math.sqrt(2 * math.pi)


def _Phi(z):  # standard normal cdf
    return 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2)))


def crps_gaussian(y, mu, sigma):
    """Closed-form CRPS for N(mu, sigma^2). Lower is better."""
    z = (y - mu) / sigma
    return sigma * (z * (2 * _Phi(z) - 1) + 2 * _phi(z) - 1 / math.sqrt(math.pi))


def nested_loso(df):
    """Outer LOSO predictions with inner-LOSO sigma per outer fold."""
    X = df[RAW_FEATURES].to_numpy()
    y = df[TARGET].to_numpy()
    groups = df["offering"].to_numpy()
    outer = GroupKFold(n_splits=df["offering"].nunique())

    mu_all, sigma_all, y_all, base_mu, base_sd = [], [], [], [], []
    for tr, te in outer.split(X, y, groups):
        # inner sigma: LOSO over the 3 training semesters only
        inner = GroupKFold(n_splits=len(np.unique(groups[tr])))
        res = []
        for itr, ite in inner.split(X[tr], y[tr], groups[tr]):
            p = make_pipeline(make_estimator())
            p.fit(X[tr][itr], y[tr][itr])
            res.extend(y[tr][ite] - p.predict(X[tr][ite]))
        sigma = float(np.std(res, ddof=1))

        pipe = make_pipeline(make_estimator())
        pipe.fit(X[tr], y[tr])
        mu = pipe.predict(X[te])

        mu_all.extend(mu)
        sigma_all.extend([sigma] * len(te))
        y_all.extend(y[te])
        base_mu.extend([float(np.mean(y[tr]))] * len(te))
        base_sd.extend([float(np.std(y[tr], ddof=1))] * len(te))

    return (np.array(mu_all), np.array(sigma_all), np.array(y_all),
            np.array(base_mu), np.array(base_sd))


def main():
    df = harmonize_all()
    mu, sigma, y, bmu, bsd = nested_loso(df)
    n = len(y)
    print(f"Nested leave-one-semester-out over {n} students, "
          f"{df['offering'].nunique()} semesters.")
    print(f"sigma per outer fold: {sorted(set(np.round(sigma, 2)))}")

    # --- interval coverage --------------------------------------------------
    print("\n=== Prediction-interval coverage (nominal vs empirical) ===")
    print(f"  {'nominal':>8s} {'empirical':>10s}")
    for level, z in Z.items():
        cover = float(np.mean(np.abs(y - mu) <= z * sigma))
        print(f"  {level:8.0%} {cover:10.1%}")

    # --- CRPS ----------------------------------------------------------------
    crps_model = float(np.mean(crps_gaussian(y, mu, sigma)))
    crps_base = float(np.mean(crps_gaussian(y, bmu, bsd)))
    print("\n=== CRPS (lower is better) ===")
    print(f"  model        {crps_model:6.3f}")
    print(f"  climatology  {crps_base:6.3f}   (predicting N(train mean, train std))")
    print(f"  skill        {1 - crps_model / crps_base:6.1%}  (improvement over baseline)")

    # --- Brier for the API's risk probabilities -----------------------------
    print("\n=== Brier score for P(final < t) (lower is better) ===")
    print(f"  {'t':>4s} {'positives':>9s} {'model':>8s} {'base-rate':>10s}")
    for t in (70.0, 60.0):
        p = _Phi((t - mu) / sigma)
        o = (y < t).astype(float)
        brier = float(np.mean((p - o) ** 2))
        rate = float(np.mean(o))
        brier_base = rate * (1 - rate)
        print(f"  {t:4.0f} {int(o.sum()):9d} {brier:8.4f} {brier_base:10.4f}")
    print("  (caveat: only ~2 students below 60 — that row is for completeness)")


if __name__ == "__main__":
    main()
