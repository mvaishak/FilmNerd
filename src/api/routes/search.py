import json
import os
from pathlib import Path
from fastapi import APIRouter, Query
import httpx

router = APIRouter()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
ANNOTATIONS_PATH = Path("data/processed/annotations.json")


def _get_corpus_ids() -> set[int]:
    if not ANNOTATIONS_PATH.exists():
        return set()
    data = json.loads(ANNOTATIONS_PATH.read_text())
    return {item["tmdb_id"] for item in data if item.get("tmdb_id")}


def _get_annotation(tmdb_id: int) -> dict | None:
    if not ANNOTATIONS_PATH.exists():
        return None
    data = json.loads(ANNOTATIONS_PATH.read_text())
    for item in data:
        if item.get("tmdb_id") == tmdb_id:
            return item
    return None


@router.get("/search")
def search_films(q: str = Query(..., min_length=1)):
    corpus_ids = _get_corpus_ids()

    resp = httpx.get(
        "https://api.themoviedb.org/3/search/movie",
        params={"api_key": TMDB_API_KEY, "query": q, "language": "en-US", "page": 1},
        timeout=10.0,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])[:10]

    output = []
    for r in results:
        tid = r.get("id")
        year = None
        rd = r.get("release_date", "")
        if rd:
            year = int(rd[:4])
        in_corpus = tid in corpus_ids
        item = {
            "tmdb_id": tid,
            "title": r.get("title"),
            "year": year,
            "poster_path": r.get("poster_path"),
            "in_corpus": in_corpus,
        }
        if in_corpus:
            item["annotation"] = _get_annotation(tid)
        output.append(item)

    return output
