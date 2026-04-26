import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..poster import get_poster_path

router = APIRouter()

ENRICHED_PATH = Path("data/processed/enriched_films.json")
ANNOTATIONS_PATH = Path("data/processed/annotations.json")


class LogRequest(BaseModel):
    tmdb_id: int
    rating: float = Field(ge=0.5, le=5.0)
    notes: Optional[str] = None


def _get_annotation(tmdb_id: int) -> dict | None:
    if not ANNOTATIONS_PATH.exists():
        return None
    data = json.loads(ANNOTATIONS_PATH.read_text())
    for item in data:
        if item.get("tmdb_id") == tmdb_id:
            return item
    return None


def _get_enriched(tmdb_id: int) -> dict | None:
    if not ENRICHED_PATH.exists():
        return None
    data = json.loads(ENRICHED_PATH.read_text())
    for item in data:
        if item.get("tmdb_id") == tmdb_id:
            return item
    return None


def _update_enriched_rating(tmdb_id: int, rating: float, notes: Optional[str]):
    """Update rating in enriched_films.json for existing film, or add minimal entry."""
    data: list[dict] = []
    if ENRICHED_PATH.exists():
        data = json.loads(ENRICHED_PATH.read_text())

    found = False
    for item in data:
        if item.get("tmdb_id") == tmdb_id:
            item["rating"] = rating
            if notes:
                item["review"] = notes
            found = True
            break

    if not found:
        data.append({"tmdb_id": tmdb_id, "rating": rating, "review": notes})

    ENRICHED_PATH.write_text(json.dumps(data, indent=2, default=str))


def _update_annotation_rating(tmdb_id: int, rating: float):
    """Update user_rating in annotations.json."""
    if not ANNOTATIONS_PATH.exists():
        return
    data = json.loads(ANNOTATIONS_PATH.read_text())
    for item in data:
        if item.get("tmdb_id") == tmdb_id:
            item["user_rating"] = rating
            break
    ANNOTATIONS_PATH.write_text(json.dumps(data, indent=2, default=str))


@router.post("/log")
def log_watch(req: LogRequest):
    annotation = _get_annotation(req.tmdb_id)
    is_new_film = annotation is None

    # Get existing data before update (for prediction comparison)
    existing = _get_enriched(req.tmdb_id)
    predicted_rating = None

    # Try to get a predicted rating from predictions db
    try:
        import sqlite3
        db = Path("data/processed/predictions.db")
        if db.exists():
            conn = sqlite3.connect(str(db))
            row = conn.execute(
                "SELECT predicted_rating FROM predictions WHERE tmdb_id=? ORDER BY predicted_at DESC LIMIT 1",
                (req.tmdb_id,)
            ).fetchone()
            conn.close()
            if row:
                predicted_rating = row[0]
    except Exception:
        pass

    _update_enriched_rating(req.tmdb_id, req.rating, req.notes)
    _update_annotation_rating(req.tmdb_id, req.rating)

    title = annotation.get("title") if annotation else (existing.get("title") if existing else f"Film {req.tmdb_id}")

    prediction_error = None
    if predicted_rating is not None:
        prediction_error = round(req.rating - predicted_rating, 2)

    return {
        "tmdb_id": req.tmdb_id,
        "title": title,
        "rating": req.rating,
        "predicted_rating": predicted_rating,
        "prediction_error": prediction_error,
        "is_new_film": is_new_film,
        "poster_path": get_poster_path(req.tmdb_id),
    }
