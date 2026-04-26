# src/taste/model.py — full replacement

import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

from sklearn.linear_model import Ridge, ElasticNet
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, KFold
from sklearn.pipeline import Pipeline
from sklearn.inspection import permutation_importance

from ..annotation.schema import CraftAnnotation
from ..ingestion.models import FilmRecord
from .encoder import build_feature_matrix, ORDINAL_FIELDS, NOMINAL_FIELDS

TASTE_MODEL_PATH = Path("data/processed/taste_profile.json")
MODEL_VERSION    = 2


# ── Model zoo ────────────────────────────────────────────────────
# In src/taste/model.py, replace MODELS dict:


MODELS = {
    "ridge_weak_signal": Pipeline([
        ("scaler", StandardScaler()),
        ("model",  Ridge(alpha=0.1)),  # very low alpha — don't regularise weak signal away
    ]),
    "elasticnet": Pipeline([
        ("scaler", StandardScaler()),
        ("model",  ElasticNet(alpha=0.01, l1_ratio=0.3, max_iter=10000)),
    ]),
    "gradient_boosting": GradientBoostingRegressor(
        n_estimators=500,
        max_depth=2,        # shallow trees — avoids overfitting weak signal
        learning_rate=0.01, # slow learning on weak signal
        subsample=0.6,
        min_samples_leaf=10,  # large leaf — forces generalisation
        random_state=42,
    ),
    "random_forest": RandomForestRegressor(
        n_estimators=500,
        max_depth=4,
        min_samples_leaf=10,
        max_features=0.3,   # sample fewer features per split
        random_state=42,
    ),
}

def compare_models(X: pd.DataFrame, y: pd.Series) -> tuple[dict, str]:
    """5-fold CV comparison across all models. Returns results + best model name."""
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    results = {}

    print("\nModel comparison (5-fold CV):")
    print(f"{'Model':<22} {'R²':>8} {'±':>6} {'MAE':>8} {'±':>6}")
    print("-" * 54)

    for name, pipeline in MODELS.items():
        r2_scores  = cross_val_score(pipeline, X, y, cv=cv, scoring="r2")
        mae_scores = -cross_val_score(pipeline, X, y, cv=cv,
                                      scoring="neg_mean_absolute_error")
        results[name] = {
            "r2_mean":  round(float(r2_scores.mean()),  3),
            "r2_std":   round(float(r2_scores.std()),   3),
            "mae_mean": round(float(mae_scores.mean()), 3),
            "mae_std":  round(float(mae_scores.std()),  3),
        }
        print(f"{name:<22} {r2_scores.mean():>8.3f} {r2_scores.std():>6.3f} "
              f"{mae_scores.mean():>8.3f} {mae_scores.std():>6.3f}")

    # Pick best by MAE — that's what the spec evaluates
    best_name = min(results, key=lambda k: results[k]["mae_mean"])
    print(f"\n→ Best model by MAE: {best_name} "
          f"(MAE={results[best_name]['mae_mean']}, R²={results[best_name]['r2_mean']})")
    return results, best_name


def extract_importance(pipeline, X: pd.DataFrame, y: pd.Series,
                        model_name: str) -> list[tuple[str, float]]:
    """
    Extract feature importances regardless of model type.
    Uses permutation importance for tree models — more reliable than
    impurity-based importance for high-cardinality one-hot features.
    """
    model = pipeline if not hasattr(pipeline, "named_steps") else pipeline

    if hasattr(model, "named_steps"):
        inner = model.named_steps.get("model", list(model.named_steps.values())[-1])
    else:
        inner = model

    if model_name in ("random_forest", "gradient_boosting"):
        # Permutation importance — robust to one-hot cardinality bias
        result = permutation_importance(
            model, X, y,
            n_repeats=10,
            random_state=42,
            scoring="neg_mean_absolute_error",
        )
        importances = result.importances_mean
    elif hasattr(inner, "coef_"):
        importances = np.abs(inner.coef_)
    elif hasattr(inner, "feature_importances_"):
        importances = inner.feature_importances_
    else:
        return []

    return sorted(
        zip(X.columns.tolist(), importances.tolist()),
        key=lambda x: x[1],
        reverse=True,
    )


def group_by_dimension(feature_importance: list[tuple]) -> list[tuple[str, float]]:
    """Aggregate one-hot feature importances back to base dimension names."""
    dimension_importance: dict[str, float] = {}

    all_fields = NOMINAL_FIELDS + list(ORDINAL_FIELDS.keys())

    for feat, score in feature_importance:
        base = next(
            (field for field in all_fields if feat.startswith(field)),
            feat,
        )
        dimension_importance[base] = dimension_importance.get(base, 0.0) + score

    return sorted(dimension_importance.items(), key=lambda x: x[1], reverse=True)


def train_taste_model(
    annotations: list[CraftAnnotation],
    records: list[FilmRecord],
) -> dict:

    X, y, df = build_feature_matrix(annotations, records)

    print(f"Training on {len(X)} films, {X.shape[1]} features")
    print(f"Rating distribution: mean={y.mean():.2f}, std={y.std():.2f}, "
          f"range=[{y.min()}, {y.max()}]")

    if len(X) < 50:
        print(" !!!!  Fewer than 50 annotated rated films — model will have low confidence")

    # ── Model comparison ─────────────────────────────────────
    model_results, best_name = compare_models(X, y)

    # ── Fit best model on full data ───────────────────────────
    best_model = MODELS[best_name]
    best_model.fit(X, y)

    # ── Always fit Ridge too for interpretability ─────────────
    # Even if Ridge isn't the best predictor, its coefficients
    # give us the named taste factors for the portfolio story
    ridge_pipeline = MODELS["ridge_weak_signal"]
    ridge_pipeline.fit(X, y)

    # ── Feature importance from best model ───────────────────
    feature_imp  = extract_importance(best_model, X, y, best_name)
    dimension_imp = group_by_dimension(feature_imp)

    # ── Ridge coefficients for interpretable taste factors ───
    ridge_inner  = ridge_pipeline.named_steps["model"]
    ridge_imp    = sorted(
        zip(X.columns, np.abs(ridge_inner.coef_)),
        key=lambda x: x[1], reverse=True
    )
    ridge_dim_imp = group_by_dimension(ridge_imp)

    # ── Divergence profile ────────────────────────────────────
    divergence_by_dimension: dict = {}
    df_div = df[df["critical_divergence"].notna()].copy()
    if len(df_div) > 10:
        for field in ["production_register", "reality_register",
                      "pacing_signature", "body_experience",
                      "moral_complexity", "ending_valence"]:
            if field in df_div.columns:
                grp = df_div.groupby(field)["critical_divergence"].mean()
                divergence_by_dimension[field] = {
                    k: round(float(v), 3) for k, v in grp.items()
                }

    # ── Low signal dimensions ─────────────────────────────────
    low_signal = [
        field for field in ORDINAL_FIELDS
        if field in X.columns and X[field].nunique() < 2
    ]

    taste_profile = {
        "model_version":                  MODEL_VERSION,
        "best_model":                     best_name,
        "model_comparison":               model_results,
        "trained_on_n_films":             len(X),
        "variance_explained":             model_results[best_name]["r2_mean"],
        "prediction_mae":                 model_results[best_name]["mae_mean"],

        # From best model — used for prediction
        "top_predictive_dimensions":      [d for d, _ in dimension_imp[:10]],
        "dimension_weights":              {d: round(float(w), 4)
                                          for d, w in dimension_imp[:20]},

        # From Ridge — used for interpretable taste report
        "interpretable_dimensions":       [d for d, _ in ridge_dim_imp[:10]],
        "ridge_dimension_weights":        {d: round(float(w), 4)
                                          for d, w in ridge_dim_imp[:20]},

        "divergence_profile":             divergence_by_dimension,
        "low_signal_dimensions":          low_signal,
        "trained_at":                     datetime.now(timezone.utc).isoformat(),
        "mean_user_rating":               round(float(y.mean()), 3),
        "rating_std":                     round(float(y.std()), 3),
    }

    TASTE_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    TASTE_MODEL_PATH.write_text(json.dumps(taste_profile, indent=2))
    print(f"\nTaste profile saved → {TASTE_MODEL_PATH}")

    return taste_profile


def load_taste_profile() -> dict:
    if not TASTE_MODEL_PATH.exists():
        raise FileNotFoundError("No taste profile found. Run train_taste_model first.")
    return json.loads(TASTE_MODEL_PATH.read_text())


def print_taste_report(profile: dict):
    print("\n" + "=" * 55)
    print("YOUR TASTE PROFILE")
    print("=" * 55)
    print(f"Trained on:       {profile['trained_on_n_films']} films")
    print(f"Best model:       {profile['best_model']}")
    print(f"Variance expl.:   {profile['variance_explained']*100:.1f}%")
    print(f"Prediction MAE:   {profile['prediction_mae']:.3f} stars")
    print(f"Mean rating:      {profile['mean_user_rating']} ★")
    print(f"Rating std dev:   {profile['rating_std']}")

    print("\n── Predictive dimensions (from best model) ──")
    weights = profile.get("dimension_weights", {})
    for i, dim in enumerate(profile["top_predictive_dimensions"], 1):
        w = weights.get(dim, 0)
        bar = "█" * min(int(w * 15), 30)
        print(f"  {i:2}. {dim:<32} {bar} ({w:.4f})")

    print("\n── Interpretable taste factors (Ridge) ──")
    r_weights = profile.get("ridge_dimension_weights", {})
    for i, dim in enumerate(profile["interpretable_dimensions"], 1):
        w = r_weights.get(dim, 0)
        bar = "█" * min(int(w * 15), 30)
        print(f"  {i:2}. {dim:<32} {bar} ({w:.4f})")

    if profile.get("divergence_profile"):
        print("\n── Where you diverge from consensus ──")
        for dimension, groups in profile["divergence_profile"].items():
            top = sorted(groups.items(), key=lambda x: abs(x[1]), reverse=True)[:2]
            for val, div in top:
                if abs(div) > 0.1:
                    arrow = "↑" if div > 0 else "↓"
                    print(f"  {arrow} {dimension}={val}: {div:+.2f} stars vs TMDB avg")

    mc = profile.get("model_comparison", {})
    if mc:
        print("\n── Model comparison ──")
        print(f"  {'Model':<22} {'R²':>8} {'MAE':>8}")
        for name, res in mc.items():
            marker = " ←" if name == profile["best_model"] else ""
            print(f"  {name:<22} {res['r2_mean']:>8.3f} {res['mae_mean']:>8.3f}{marker}")

    if profile.get("low_signal_dimensions"):
        print(f"\n !!!!  Low signal: {profile['low_signal_dimensions']}")

