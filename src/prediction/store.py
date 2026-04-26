import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..annotation.schema import PredictionRecord

DB_PATH = Path("data/processed/predictions.db")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                tmdb_id               INTEGER PRIMARY KEY,
                title                 TEXT    NOT NULL,
                predicted_rating      REAL    NOT NULL,
                actual_rating         REAL,
                prediction_error      REAL,
                taste_model_version   INTEGER NOT NULL,
                predicted_at          TEXT    NOT NULL,
                watched_at            TEXT,
                top_dimensions_used   TEXT    NOT NULL
            )
        """)


def save_prediction(record: PredictionRecord):
    init_db()
    with _connect() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO predictions
            (tmdb_id, title, predicted_rating, actual_rating, prediction_error,
             taste_model_version, predicted_at, watched_at, top_dimensions_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.tmdb_id,
            record.title,
            record.predicted_rating,
            record.actual_rating,
            record.prediction_error,
            record.taste_model_version,
            record.predicted_at,
            record.watched_at,
            json.dumps(record.top_dimensions_used),
        ))


def get_prediction(tmdb_id: int) -> PredictionRecord | None:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE tmdb_id = ?", (tmdb_id,)
        ).fetchone()
    if not row:
        return None
    return _row_to_record(row)


def get_pending() -> list[PredictionRecord]:
    """Predictions not yet fulfilled with an actual rating."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions WHERE actual_rating IS NULL ORDER BY predicted_at"
        ).fetchall()
    return [_row_to_record(r) for r in rows]


def get_all() -> list[PredictionRecord]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions ORDER BY predicted_at"
        ).fetchall()
    return [_row_to_record(r) for r in rows]


def log_actual_rating(tmdb_id: int, actual_rating: float):
    """Called by Ground Truth Logger after watching a predicted film."""
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT predicted_rating FROM predictions WHERE tmdb_id = ?", (tmdb_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"No prediction on file for tmdb_id={tmdb_id}")
        error = round(abs(row["predicted_rating"] - actual_rating), 3)
        conn.execute("""
            UPDATE predictions
            SET actual_rating = ?, prediction_error = ?, watched_at = ?
            WHERE tmdb_id = ?
        """, (actual_rating, error, datetime.now(timezone.utc).isoformat(), tmdb_id))


def _row_to_record(row: sqlite3.Row) -> PredictionRecord:
    return PredictionRecord(
        tmdb_id=row["tmdb_id"],
        title=row["title"],
        predicted_rating=row["predicted_rating"],
        actual_rating=row["actual_rating"],
        prediction_error=row["prediction_error"],
        taste_model_version=row["taste_model_version"],
        predicted_at=row["predicted_at"],
        watched_at=row["watched_at"],
        top_dimensions_used=json.loads(row["top_dimensions_used"]),
    )
