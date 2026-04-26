"""
Taste Profile Dashboard — Streamlit.

Run: streamlit run src/monitoring/taste_dashboard.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

TASTE_PATH       = Path("data/processed/taste_profile.json")
PREDICTIONS_PATH = Path("data/processed/predictions.db")

st.set_page_config(page_title="Film Taste Profile", page_icon="🎬", layout="wide")
st.title("🎬 Film Taste Intelligence — Taste Profile")


# ── Load data ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_profile() -> dict:
    if not TASTE_PATH.exists():
        return {}
    return json.loads(TASTE_PATH.read_text())


@st.cache_data(ttl=30)
def load_predictions() -> pd.DataFrame:
    if not PREDICTIONS_PATH.exists():
        return pd.DataFrame()
    import sqlite3
    conn = sqlite3.connect(PREDICTIONS_PATH)
    df   = pd.read_sql("SELECT * FROM predictions ORDER BY predicted_at", conn)
    conn.close()
    return df


profile = load_profile()
preds   = load_predictions()

if not profile:
    st.warning("No taste profile found. Run `python -m src.taste.run_taste` first.")
    st.stop()


# ── Top-line metrics ──────────────────────────────────────────────────────────

c1, c2, c3, c4 = st.columns(4)
c1.metric("Films in model",    profile.get("trained_on_n_films", "?"))
c2.metric("Best model",        profile.get("best_model", "?"))
c3.metric("Mean rating",       f"{profile.get('mean_user_rating', 0):.2f} ★")
c4.metric("Prediction MAE",    f"{profile.get('prediction_mae', 0):.3f} ★")

st.divider()


# ── Model comparison ──────────────────────────────────────────────────────────

model_cmp = profile.get("model_comparison", {})
if model_cmp:
    st.subheader("Model Comparison")
    rows = []
    for name, stats in model_cmp.items():
        rows.append({
            "Model":    name,
            "CV R²":    round(stats.get("cv_r2_mean", 0), 4),
            "CV R² std": round(stats.get("cv_r2_std", 0), 4),
            "Train MAE": round(stats.get("train_mae", 0), 3),
            "Test MAE":  round(stats.get("test_mae", 0), 3),
        })
    df_cmp = pd.DataFrame(rows).set_index("Model")
    st.dataframe(df_cmp, use_container_width=True)
    st.caption(f"Best: **{profile.get('best_model')}**  |  Variance explained: {profile.get('variance_explained', 0):.1%}")

st.divider()


# ── Top predictive dimensions ─────────────────────────────────────────────────

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Top Predictive Dimensions")
    dims   = profile.get("interpretable_dimensions", [])
    weights = profile.get("ridge_dimension_weights", {})
    if dims:
        df_dims = pd.DataFrame({
            "Dimension": dims,
            "Ridge weight": [round(weights.get(d, 0), 4) for d in dims],
        })
        st.dataframe(df_dims, use_container_width=True, hide_index=True)

with col_right:
    st.subheader("Divergence from Consensus")
    st.caption("Where your ratings differ most from TMDB/Letterboxd aggregate ratings")
    div = profile.get("divergence_profile", {})
    rows = []
    for dimension, groups in div.items():
        for val, delta in groups.items():
            if abs(delta) > 0.1:
                rows.append({
                    "Dimension": dimension,
                    "Value":     val,
                    "Delta (★)": round(delta, 2),
                })
    if rows:
        df_div = pd.DataFrame(rows).sort_values("Delta (★)", ascending=False)
        st.dataframe(df_div, use_container_width=True, hide_index=True)

st.divider()


# ── Prediction accuracy ───────────────────────────────────────────────────────

st.subheader("Prediction Accuracy")

if preds.empty:
    st.info("No predictions logged yet. Run `python -m src.prediction.run_prediction` to generate some.")
else:
    evaluated = preds.dropna(subset=["actual_rating"])
    pending   = preds[preds["actual_rating"].isna()]

    a1, a2, a3 = st.columns(3)
    a1.metric("Total predictions",  len(preds))
    a2.metric("Evaluated",          len(evaluated))
    a3.metric("Pending",            len(pending))

    if not evaluated.empty:
        mae         = evaluated["prediction_error"].mean()
        within_half = (evaluated["prediction_error"] <= 0.5).mean()
        within_one  = (evaluated["prediction_error"] <= 1.0).mean()

        b1, b2, b3 = st.columns(3)
        b1.metric("MAE",            f"{mae:.3f} ★")
        b2.metric("Within ½ ★",    f"{within_half:.1%}")
        b3.metric("Within 1 ★",    f"{within_one:.1%}")

        # Scatter: predicted vs actual
        st.subheader("Predicted vs Actual Ratings")
        chart_data = evaluated[["title", "predicted_rating", "actual_rating"]].copy()
        chart_data = chart_data.rename(columns={
            "predicted_rating": "Predicted",
            "actual_rating":    "Actual",
        })
        st.scatter_chart(chart_data.set_index("title")[["Predicted", "Actual"]])

        # MAE over time
        st.subheader("Cumulative MAE Over Time")
        evaluated_sorted = evaluated.sort_values("watched_at")
        evaluated_sorted["cumulative_mae"] = (
            evaluated_sorted["prediction_error"].expanding().mean()
        )
        st.line_chart(evaluated_sorted.set_index("watched_at")["cumulative_mae"])

    if not pending.empty:
        st.subheader("Pending Predictions (not yet watched)")
        st.dataframe(
            pending[["tmdb_id", "title", "predicted_rating", "predicted_at"]],
            use_container_width=True, hide_index=True,
        )

st.divider()
st.caption(
    f"Taste model v{profile.get('model_version', '?')} · "
    f"trained {profile.get('trained_at', '')[:10]} · "
    f"rating std {profile.get('rating_std', 0):.2f}"
)
