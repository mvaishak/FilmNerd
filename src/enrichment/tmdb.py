# src/enrichment/tmdb.py
import asyncio
import aiohttp
import json
import os
from pathlib import Path
from typing import Optional
from tqdm.asyncio import tqdm_asyncio
from dotenv import load_dotenv
from ..ingestion.models import FilmRecord, CrewMember

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
CACHE_DIR = Path(os.getenv("CACHE_DIR", "data/cache")) / "tmdb"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://api.themoviedb.org/3"
CONCURRENCY = 10  # simultaneous requests — safe for TMDB free tier


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"

def _load_cache(key: str) -> Optional[dict]:
    p = _cache_path(key)
    if p.exists():
        return json.loads(p.read_text())
    return None

def _save_cache(key: str, data: dict):
    _cache_path(key).write_text(json.dumps(data))


async def _get(session: aiohttp.ClientSession, url: str, params: dict) -> Optional[dict]:
    params["api_key"] = TMDB_API_KEY
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return await resp.json()
            return None
    except Exception:
        return None


async def _search_tmdb_id(session: aiohttp.ClientSession, title: str, year: Optional[int]) -> Optional[int]:
    cache_key = f"search_{title}_{year}".replace(" ", "_").lower()
    cached = _load_cache(cache_key)
    if cached:
        return cached.get("tmdb_id")

    params = {"query": title, "include_adult": "false"}
    if year:
        params["year"] = year

    data = await _get(session, f"{BASE_URL}/search/movie", params)
    if not data or not data.get("results"):
        # Retry without year constraint if no results
        if year:
            data = await _get(session, f"{BASE_URL}/search/movie", {"query": title, "include_adult": "false"})

    tmdb_id = None
    if data and data.get("results"):
        tmdb_id = data["results"][0]["id"]

    _save_cache(cache_key, {"tmdb_id": tmdb_id})
    return tmdb_id


async def _fetch_movie_details(session: aiohttp.ClientSession, tmdb_id: int) -> Optional[dict]:
    cache_key = f"details_{tmdb_id}"
    cached = _load_cache(cache_key)
    if cached:
        return cached

    data = await _get(session, f"{BASE_URL}/movie/{tmdb_id}", {"append_to_response": "external_ids"})
    if data:
        _save_cache(cache_key, data)
    return data


async def _fetch_credits(session: aiohttp.ClientSession, tmdb_id: int) -> Optional[dict]:
    cache_key = f"credits_{tmdb_id}"
    cached = _load_cache(cache_key)
    if cached:
        return cached

    data = await _get(session, f"{BASE_URL}/movie/{tmdb_id}/credits", {})
    if data:
        _save_cache(cache_key, data)
    return data


def _extract_crew(credits: dict) -> dict:
    """Extract the five key crew roles from TMDB credits."""
    crew = credits.get("crew", [])
    
    def find_first(job_titles: list[str]) -> Optional[CrewMember]:
        for member in crew:
            if member.get("job") in job_titles:
                return CrewMember(name=member["name"], tmdb_id=member["id"])
        return None

    return {
        "director":        find_first(["Director"]),
        "cinematographer": find_first(["Director of Photography", "Cinematographer"]),
        "editor":          find_first(["Editor", "Film Editor"]),
        "writer":          find_first(["Screenplay", "Writer", "Story"]),
        "composer":        find_first(["Original Music Composer", "Music", "Composer"]),
    }


async def _enrich_one(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    record: FilmRecord,
) -> FilmRecord:
    async with semaphore:
        try:
            tmdb_id = await _search_tmdb_id(session, record.title, record.year)
            if not tmdb_id:
                record.enrichment_error = "TMDB search returned no results"
                return record

            details, credits = await asyncio.gather(
                _fetch_movie_details(session, tmdb_id),
                _fetch_credits(session, tmdb_id),
            )

            if not details:
                record.enrichment_error = "TMDB details fetch failed"
                return record

            crew = _extract_crew(credits) if credits else {}

            record.tmdb_id = tmdb_id
            record.imdb_id = details.get("external_ids", {}).get("imdb_id")
            record.runtime = details.get("runtime")
            record.original_language = details.get("original_language")
            record.production_countries = [c["iso_3166_1"] for c in details.get("production_countries", [])]
            record.genres = [g["name"] for g in details.get("genres", [])]
            record.overview = details.get("overview")
            record.tmdb_rating = details.get("vote_average")
            record.tmdb_vote_count = details.get("vote_count")
            record.director = crew.get("director")
            record.cinematographer = crew.get("cinematographer")
            record.editor = crew.get("editor")
            record.writer = crew.get("writer")
            record.composer = crew.get("composer")
            record.enriched = True

        except Exception as e:
            record.enrichment_error = str(e)

        return record


async def enrich_all(records: list[FilmRecord]) -> list[FilmRecord]:
    semaphore = asyncio.Semaphore(CONCURRENCY)
    async with aiohttp.ClientSession() as session:
        tasks = [_enrich_one(session, semaphore, r) for r in records]
        results = await tqdm_asyncio.gather(*tasks, desc="Enriching via TMDB")
    return results


async def retry_failed(records: list[FilmRecord]) -> list[FilmRecord]:
    """Single retry pass for transient failures."""
    failed = [r for r in records if not r.enriched and r.enrichment_error == "TMDB details fetch failed"]
    if not failed:
        return records
    
    print(f"\nRetrying {len(failed)} transient failures...")
    retried = await enrich_all(failed)
    
    # Merge back
    retried_map = {r.title: r for r in retried}
    return [retried_map.get(r.title, r) for r in records]