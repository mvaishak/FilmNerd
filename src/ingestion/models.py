from pydantic import BaseModel
from typing import Optional
from datetime import date

class CrewMember(BaseModel):
    name: str
    tmdb_id: int
    
class FilmRecord(BaseModel):
    # From Letterboxd
    title: str
    year: Optional[int]
    rating: Optional[float]          # 0.5–5.0, None if unrated
    watch_date: Optional[str]
    letterboxd_uri: Optional[str]
    review: Optional[str]

    # From TMDB (populated by enrichment agent)
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    runtime: Optional[int] = None
    original_language: Optional[str] = None
    production_countries: list[str] = []
    genres: list[str] = []
    overview: Optional[str] = None
    tmdb_rating: Optional[float] = None
    tmdb_vote_count: Optional[int] = None

    # Crew
    director: Optional[CrewMember] = None
    cinematographer: Optional[CrewMember] = None
    editor: Optional[CrewMember] = None
    writer: Optional[CrewMember] = None
    composer: Optional[CrewMember] = None

    # Status flags
    enriched: bool = False
    enrichment_error: Optional[str] = None