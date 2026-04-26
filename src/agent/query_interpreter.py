"""
Translates natural language queries into craft-dimension text for Qdrant search.

Two strategies:
  Film reference  – query names a specific film → use that film's annotation text
                    (same format as indexed docs, guaranteed embedding alignment)
  Natural language – map descriptive text to craft dimensions via LLM
"""
import os
from typing import Literal

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

from ..annotation.store import load_annotations
from .qdrant_index import annotation_text

_client = instructor.from_openai(
    OpenAI(
        base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
        api_key="lm-studio",
    ),
    mode=instructor.Mode.JSON_SCHEMA,
)
_MODEL = os.getenv("LM_STUDIO_MODEL", "qwen3.5")


class _CraftProfile(BaseModel):
    director_lineage: Literal[
        "european_art_cinema", "american_new_wave", "east_asian_modernism",
        "latin_american_realism", "mumblecore_naturalism", "genre_formalism",
        "documentary_hybrid", "postmodern_pastiche", "mainstream_classical",
        "south_asian_parallel", "african_diaspora", "independent_auteur",
        "transnational_global",
    ]
    pacing_signature: Literal["slow_burn", "measured", "propulsive", "frenetic", "variable"]
    reality_register: Literal[
        "hyperrealist", "social_realist", "heightened_stylized",
        "magical_realist", "surrealist", "genre_artificial", "mythic",
    ]
    tone_primary: Literal[
        "bleak", "melancholic", "deadpan", "absurdist", "earnest",
        "lyrical", "tense", "playful", "elegiac", "satirical",
    ]
    body_experience: Literal[
        "dread_creeping", "tension_sustained", "catharsis_emotional", "wonder_awe",
        "discomfort_confrontational", "meditative_dissociative", "propulsive_momentum",
        "funny_uncomfortable", "grief_immersive",
    ]
    production_register: Literal[
        "microbudget_raw", "indie_crafted", "mid_budget_studio", "prestige",
        "blockbuster", "foreign_language_arthouse", "documentary_observational",
    ]
    thematic_primary: str = Field(description="Short thematic descriptor, e.g. 'memory desire loss'")
    cinematographic_language: Literal[
        "handheld_intimate", "static_composed", "long_take",
        "montage_driven", "expressionistic", "observational", "formalist",
    ]


def _find_by_title(query: str) -> str | None:
    """
    Scan annotation titles for a substring match against the user's query.
    Returns annotation text of the matched film, or None.

    Sorts by title length descending so "In the Mood for Love" wins over "Love"
    when both are substrings of the query.
    """
    annotations = load_annotations()
    query_lower = query.lower()

    # Collect all annotations whose title appears as a substring of the query
    candidates = [
        ann for ann in annotations
        if ann.title.lower() in query_lower
    ]

    if not candidates:
        return None

    # Prefer longest title match (most specific)
    best = max(candidates, key=lambda a: len(a.title))
    return annotation_text(best)


def _craft_text_from_nl(query: str) -> str:
    """Use LLM to translate a natural language description to craft-dimension text."""
    profile = _client.chat.completions.create(
        model=_MODEL,
        response_model=_CraftProfile,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a film craft analyst. Map the user's description to the exact "
                    "craft dimension values from the provided enum lists. You must use only "
                    "the listed values — do not invent new ones."
                ),
            },
            {"role": "user", "content": f"Map to craft dimensions: {query}"},
        ],
    )
    return (
        f"{profile.director_lineage} cinema "
        f"pacing {profile.pacing_signature} "
        f"reality {profile.reality_register} "
        f"tone {profile.tone_primary} "
        f"body {profile.body_experience} "
        f"production {profile.production_register} "
        f"theme {profile.thematic_primary} "
        f"cinematography {profile.cinematographic_language}"
    )


def build_craft_query(user_query: str) -> tuple[str, str]:
    """
    Return (craft_text, resolution_note) for a user query.

    craft_text      – embedding-ready craft-dimension text for Qdrant
    resolution_note – how the query was resolved (for logging/prompt context)
    """
    # Step 1: direct annotation title scan (no LLM needed, highest fidelity)
    craft = _find_by_title(user_query)
    if craft:
        # Extract the matched title for the note
        annotations = load_annotations()
        matched = max(
            (a for a in annotations if a.title.lower() in user_query.lower()),
            key=lambda a: len(a.title),
        )
        return craft, f"resolved via craft profile of '{matched.title}'"

    # Step 2: natural language → craft dimensions via LLM
    craft = _craft_text_from_nl(user_query)
    return craft, "resolved via craft dimension mapping"
