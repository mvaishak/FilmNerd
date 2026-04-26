import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

from ..poster import get_poster_path

router = APIRouter()

_ANNOTATIONS_PATH = Path("data/processed/annotations.json")
_ENRICHED_PATH = Path("data/processed/enriched_films.json")


def _build_index() -> dict[int, dict]:
    annotations = json.loads(_ANNOTATIONS_PATH.read_text())
    enriched_map: dict[int, dict] = {}
    if _ENRICHED_PATH.exists():
        for r in json.loads(_ENRICHED_PATH.read_text()):
            if r.get("tmdb_id"):
                enriched_map[r["tmdb_id"]] = r

    index = {}
    for ann in annotations:
        tid = ann.get("tmdb_id")
        if not tid:
            continue
        enriched = enriched_map.get(tid, {})
        rating = ann.get("user_rating") or enriched.get("rating")
        index[tid] = {**ann, "user_rating": rating, "poster_path": get_poster_path(tid)}
    return index


@router.get("/films/{tmdb_id}")
def get_film(tmdb_id: int):
    index = _build_index()
    film = index.get(tmdb_id)
    if not film:
        raise HTTPException(status_code=404, detail="Film not found")
    return film
