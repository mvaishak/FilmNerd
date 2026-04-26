import os
import json
import instructor
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv
from .schema import CraftAnnotation, AnnotationConfidence
from ..ingestion.models import FilmRecord

load_dotenv()

CACHE_DIR = Path(os.getenv("CACHE_DIR", "data/cache")) / "annotations"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

client = instructor.from_openai(
    OpenAI(
        base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
        api_key="lm-studio",
    ),
    mode=instructor.Mode.JSON_SCHEMA,
)

MODEL = os.getenv("LM_STUDIO_MODEL", "qwen3.5")


def _cache_path(tmdb_id: int) -> Path:
    # Cache key is ALWAYS the canonical tmdb_id from enriched_films.json
    return CACHE_DIR / f"{tmdb_id}.json"


def _load_cached(tmdb_id: int) -> CraftAnnotation | None:
    p = _cache_path(tmdb_id)
    if p.exists():
        return CraftAnnotation(**json.loads(p.read_text()))
    return None


def _save_cache(annotation: CraftAnnotation, canonical_tmdb_id: int):
    # Always write to the canonical ID path regardless of what the model returned
    # This is the fix for the wrong-mapping bug
    path = CACHE_DIR / f"{canonical_tmdb_id}.json"
    path.write_text(annotation.model_dump_json(indent=2))


def _build_prompt(record: FilmRecord) -> str:
    crew_parts = []
    if record.director:
        crew_parts.append(f"Director: {record.director.name}")
    if record.cinematographer:
        crew_parts.append(f"Cinematographer: {record.cinematographer.name}")
    if record.editor:
        crew_parts.append(f"Editor: {record.editor.name}")
    if record.writer:
        crew_parts.append(f"Writer: {record.writer.name}")
    if record.composer:
        crew_parts.append(f"Composer: {record.composer.name}")

    crew_str    = "\n".join(crew_parts) if crew_parts else "Crew data unavailable"
    genres_str  = ", ".join(record.genres) if record.genres else "Unknown"
    country_str = ", ".join(record.production_countries) if record.production_countries else "Unknown"
    overview    = (record.overview or "")[:200]  # truncate — saves tokens

    return f"""

Annotate this film across all craft dimensions. Be precise — do not default to middle-ground choices.

FILM:
Title:    {record.title} ({record.year})
Genres:   {genres_str}
Country:  {country_str}
Runtime:  {record.runtime} min
{crew_str}
Overview: {overview}

GUIDANCE:

reality_register:
  - hyperrealist       = Dardennes, early Cassavetes — more real than real
  - social_realist     = Moonlight, Parasite, Bicycle Thieves — grounded, observational
  - heightened_stylized= Lanthimos, Wes Anderson — real world, artificial register
  - mythic             = Mad Max Fury Road, Apocalypse Now — fable scale
  - DO NOT use heightened_stylized for social realist dramas shot on location

moral_complexity:
  - clear_moral_poles      = Die Hard, most superhero films — legible good/evil
  - sympathetic_antagonist = The Dark Knight, No Country for Old Men — villain has coherent ideology
  - morally_ambiguous      = Chinatown, Cache — film refuses to adjudicate
  - systemic_no_villain    = Parasite, Shoplifters — harm is structural, not personal
  - DO NOT use systemic_no_villain when a named antagonist drives the conflict

production_register:
  - prestige    = A24/Neon/Searchlight awards films (Moonlight, Nomadland)
  - blockbuster = $100M+ budget, franchise context (Dark Knight, Fury Road, Marvel)
  - DO NOT assign prestige to blockbusters regardless of critical reception

annotation_confidence:
  - HIGH   = Best Picture winners, Palme d'Or, wide critical corpus
  - MEDIUM = notable but limited critical coverage
  - LOW    = genuinely obscure, minimal criticism available

body_experience:    what watching FEELS like somatically, not what the film is about
editor_signature:   rhythm and structure of cuts — distinct from pacing
point_of_view:      who the camera privileges narratively, not who appears most
ending_valence:     annotate the ending as experienced, not as marketed
colour_palette:     intentional chromatic strategy of the film
aspect_ratio:       the intended exhibition ratio"""


def annotate_film(record: FilmRecord) -> CraftAnnotation | None:
    """
    Annotate a single film using the canonical tmdb_id from the enriched record.
    The cache is always keyed by record.tmdb_id — never by whatever the model returns.
    """
    if not record.tmdb_id:
        return None

    # Check cache using canonical ID
    cached = _load_cached(record.tmdb_id)
    if cached:
        return cached

    try:
        annotation = client.chat.completions.create(
            model=MODEL,
            response_model=CraftAnnotation,
            max_retries=1,  # was 3 — each retry is a full inference call
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise film craft analyst with encyclopedic knowledge of world cinema. "
                        "Set annotation_confidence to HIGH for any widely-discussed film — major festival films, "
                        "box office hits, and critically acclaimed films from any decade. "
                        "MEDIUM for notable films with moderate coverage. "
                        "LOW only for genuinely obscure films. "
                        "Do not be falsely modest."
                    )
                },
                {
                    "role": "user",
                    "content": _build_prompt(record)
                }
            ],
        )

        # ── Canonical ID enforcement ──────────────────────────────────
        # Overwrite whatever tmdb_id the model returned with the ground
        # truth ID from the enriched record. This prevents wrong-mapping.
        annotation.tmdb_id = record.tmdb_id
        annotation.title   = record.title
        annotation.year    = record.year

        # Save to canonical path — not annotation.tmdb_id (same thing now,
        # but explicit for clarity)
        _save_cache(annotation, canonical_tmdb_id=record.tmdb_id)
        return annotation

    except Exception as e:
        print(f"  ✗ {record.title} (tmdb_id={record.tmdb_id}): {e}")
        return None