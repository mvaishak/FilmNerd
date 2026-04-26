import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query

from ..poster import get_poster_path

router = APIRouter()

_ANNOTATIONS_PATH = Path("data/processed/annotations.json")
_ENRICHED_PATH = Path("data/processed/enriched_films.json")

# Filterable dimensions
FILTER_DIMS = [
    "pacing_signature", "tone_primary", "body_experience",
    "reality_register", "moral_complexity", "production_register",
    "director_lineage", "ending_valence",
]


def _load_corpus() -> list[dict]:
    annotations = json.loads(_ANNOTATIONS_PATH.read_text())
    enriched_map: dict[int, dict] = {}
    if _ENRICHED_PATH.exists():
        for r in json.loads(_ENRICHED_PATH.read_text()):
            if r.get("tmdb_id"):
                enriched_map[r["tmdb_id"]] = r

    result = []
    for ann in annotations:
        tid = ann.get("tmdb_id")
        enriched = enriched_map.get(tid, {})
        # Merge user_rating from enriched if missing in annotation
        rating = ann.get("user_rating") or enriched.get("rating")
        item = {**ann, "user_rating": rating, "poster_path": get_poster_path(tid) if tid else None}
        result.append(item)
    return result


@router.get("/corpus")
def get_corpus(
    pacing_signature: Optional[str] = None,
    tone_primary: Optional[str] = None,
    body_experience: Optional[str] = None,
    reality_register: Optional[str] = None,
    moral_complexity: Optional[str] = None,
    production_register: Optional[str] = None,
    director_lineage: Optional[str] = None,
    ending_valence: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    films = _load_corpus()

    # Apply filters
    filters = {
        "pacing_signature": pacing_signature,
        "tone_primary": tone_primary,
        "body_experience": body_experience,
        "reality_register": reality_register,
        "moral_complexity": moral_complexity,
        "production_register": production_register,
        "director_lineage": director_lineage,
        "ending_valence": ending_valence,
    }
    for dim, val in filters.items():
        if val:
            films = [f for f in films if f.get(dim) == val]

    if search:
        q = search.lower()
        films = [f for f in films if q in (f.get("title") or "").lower()]

    total = len(films)
    start = (page - 1) * per_page
    end = start + per_page

    return {
        "films": films[start:end],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
