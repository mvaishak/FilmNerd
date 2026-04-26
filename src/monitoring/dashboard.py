# src/monitoring/dashboard.py
import streamlit as st
import json
import time
from pathlib import Path
from collections import Counter
import pandas as pd

ANNOTATIONS_CACHE = Path("data/cache/annotations")
ENRICHED_PATH = Path("data/processed/enriched_films.json")
LOG_PATH = Path("logs/annotation.log")

st.set_page_config(page_title="Annotation Monitor", page_icon="🎬", layout="wide")
st.title("🎬 Annotation Pipeline Monitor")

# Auto-refresh every 30 seconds
refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 10, 120, 30)
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)


def load_progress():
    completed = list(ANNOTATIONS_CACHE.glob("*.json"))
    total_eligible = 804  # update if your count differs

    annotations = []
    for p in completed:
        try:
            annotations.append(json.loads(p.read_text()))
        except Exception:
            pass
    return annotations, total_eligible


def load_enriched_index():
    if not ENRICHED_PATH.exists():
        return {}
    records = json.loads(ENRICHED_PATH.read_text())
    return {r["tmdb_id"]: r for r in records if r.get("tmdb_id")}

def load_log_failures():
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text().splitlines()
    return [l for l in lines if "failed" in l.lower() or "✗" in l]

# --- Load data ---
annotations, total = load_progress()
enriched_index = load_enriched_index()
failures = load_log_failures()

completed_count = len(annotations)
pct = completed_count / total * 100 if total else 0

# --- Top metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Completed", f"{completed_count} / {total}")
col2.metric("Progress", f"{pct:.1f}%")
col3.metric("Remaining", total - completed_count)
col4.metric("Failures", len(failures))

st.progress(pct / 100)

# --- Estimate time remaining ---
if annotations:
    # Use file modification times to estimate rate
    mtimes = sorted([
        Path(ANNOTATIONS_CACHE / f"{a['tmdb_id']}.json").stat().st_mtime
        for a in annotations
        if (ANNOTATIONS_CACHE / f"{a['tmdb_id']}.json").exists()
    ])
    if len(mtimes) > 10:
        # Rate over last 50 annotations
        window = min(50, len(mtimes))
        elapsed = mtimes[-1] - mtimes[-window]
        rate = window / elapsed if elapsed > 0 else 0
        remaining = total - completed_count
        eta_seconds = remaining / rate if rate > 0 else 0
        eta_min = int(eta_seconds // 60)
        eta_hr = eta_min // 60
        eta_min_remainder = eta_min % 60
        st.info(f"⏱ Estimated time remaining: **{eta_hr}h {eta_min_remainder}m** at {rate:.2f} films/sec")

st.divider()

if annotations:
    df = pd.DataFrame(annotations)

    # In src/monitoring/dashboard.py, replace the two chart columns block:

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Pacing Distribution")
    pacing_counts = Counter(df["pacing_signature"])
    st.bar_chart(pd.Series(pacing_counts))

    st.subheader("Tone Distribution")
    if "tone_primary" in df.columns:
        tone_counts = Counter(df["tone_primary"])
        st.bar_chart(pd.Series(tone_counts))

    st.subheader("Body Experience")
    if "body_experience" in df.columns:
        body_counts = Counter(df["body_experience"])
        st.bar_chart(pd.Series(body_counts))

    with col_right:
        st.subheader("Thematic Clusters")
        if "thematic_primary" in df.columns:
            theme_counts = Counter(df["thematic_primary"])
        else:
            theme_counts = Counter(df["thematic_cluster"])
        st.bar_chart(pd.Series(theme_counts).sort_values(ascending=False))

        st.subheader("Reality Register")
        if "reality_register" in df.columns:
            register_counts = Counter(df["reality_register"])
            st.bar_chart(pd.Series(register_counts))

        st.subheader("Production Register")
        if "production_register" in df.columns:
            prod_counts = Counter(df["production_register"])
            st.bar_chart(pd.Series(prod_counts))

    st.subheader("Moral Complexity")
    if "moral_complexity" in df.columns:
        moral_counts = Counter(df["moral_complexity"])
        st.bar_chart(pd.Series(moral_counts))

    st.subheader("Confidence Levels")
    if "annotation_confidence" in df.columns:
        conf_counts = Counter(df["annotation_confidence"].astype(str))
        st.bar_chart(pd.Series(conf_counts))

    st.subheader("Most Recent Annotations")
    recent_tmdb_ids = [
        int(p.stem) for p in sorted(
            ANNOTATIONS_CACHE.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:10]
    ]
    recent_rows = []
    for tid in recent_tmdb_ids:
        record = enriched_index.get(tid, {})
        ann_path = ANNOTATIONS_CACHE / f"{tid}.json"
        try:
            ann = json.loads(ann_path.read_text())
            # Replace the recent_rows.append(...) block:
            recent_rows.append({
                "Title":             record.get("title", "Unknown"),
                "Year":              record.get("year", ""),
                "Pacing":            ann.get("pacing_signature", ""),
                "Tone":              ann.get("tone_primary", ""),
                "Body Experience":   ann.get("body_experience", ""),
                "Reality Register":  ann.get("reality_register", ""),
                "Thematic":          ann.get("thematic_primary", ""),
                "Confidence":        ann.get("annotation_confidence", ""),
            })
        except Exception:
            pass
    if recent_rows:
        st.dataframe(pd.DataFrame(recent_rows), use_container_width=True)

if failures:
    with st.expander(f"⚠️ Failures ({len(failures)})"):
        for f in failures[-20:]:
            st.text(f)

# Auto-refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()