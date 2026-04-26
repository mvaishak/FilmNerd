"""
LangGraph Recommendation Agent.

State flow:
    rag_retrieve → graph_traverse → rerank_by_taste → synthesize → END

Each node is a pure function: state in → state out.
The agent is callable as a function; it does not require a running server.
"""
import os
from typing import TypedDict

import instructor
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from openai import OpenAI
from pydantic import BaseModel, Field

from ..enrichment.store import load_enriched
from ..taste.model import load_taste_profile
from ..observability.tracer import get_langfuse
from .graph_retriever import get_graph_candidates
from .qdrant_index import search as qdrant_search
from .query_interpreter import build_craft_query

try:
    from langfuse.decorators import observe, langfuse_context
    _LANGFUSE_DECORATORS = True
except ImportError:
    _LANGFUSE_DECORATORS = False
    def observe(**_kw):
        def _wrap(fn): return fn
        return _wrap
    class langfuse_context:  # noqa: N801
        @staticmethod
        def update_current_observation(**_kw): pass

load_dotenv()

_client = instructor.from_openai(
    OpenAI(
        base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
        api_key="lm-studio",
    ),
    mode=instructor.Mode.JSON_SCHEMA,
)
_MODEL = os.getenv("LM_STUDIO_MODEL", "qwen3.5")


# ── State ─────────────────────────────────────────────────────────

class AgentState(TypedDict):
    query:                    str
    seen_ids:                 list[int]
    taste_profile:            dict
    rag_hits:                 list[dict]
    graph_hits:               list[dict]
    candidates:               list[dict]
    recommendations:          list[dict]
    confidence:               str
    craft_query_resolution:   str


# ── Pydantic output schema for synthesis ──────────────────────────

class FilmRecommendation(BaseModel):
    title:          str
    year:           int | None
    tmdb_id:        int | None
    explanation:    str = Field(
        description=(
            "2-3 sentences grounded in the user's specific craft dimension preferences. "
            "Must reference at least 2 named dimensions from the taste profile."
        )
    )
    key_dimensions: list[str] = Field(
        description="The 2-4 craft dimension names most relevant to this recommendation"
    )
    via_path:       str = Field(
        description="How this film was surfaced: 'rag_similarity', 'graph_influence', "
                    "'graph_collaborator', or 'graph_direct'"
    )


class SynthesisOutput(BaseModel):
    recommendations: list[FilmRecommendation] = Field(
        min_length=1, max_length=5,
        description="Ranked film recommendations, best match first"
    )
    confidence_note: str = Field(
        description=(
            "Brief note on recommendation confidence. If taste model is based on < 50 films, "
            "explicitly state that signal is limited."
        )
    )


# ── Node functions ────────────────────────────────────────────────

@observe(name="rag_retrieve")
def rag_retrieve(state: AgentState) -> AgentState:
    seen = set(state["seen_ids"])

    craft_query, resolution_note = build_craft_query(state["query"])

    hits = qdrant_search(
        query_text=craft_query,
        limit=20,
        filter_unseen=False,
    )
    unseen = [h for h in hits if h.get("tmdb_id") not in seen]
    seen_high = [
        h for h in hits
        if h.get("tmdb_id") in seen and (h.get("user_rating") or 0) >= 4.0
    ]
    result = unseen[:10] + seen_high[:5]
    langfuse_context.update_current_observation(
        output={
            "n_rag_hits": len(result),
            "n_unseen": len(unseen),
            "n_seen_high": len(seen_high),
            "craft_query_resolution": resolution_note,
        },
    )
    return {**state, "rag_hits": result, "craft_query_resolution": resolution_note}


@observe(name="graph_traverse")
def graph_traverse(state: AgentState) -> AgentState:
    records = load_enriched()
    hits    = get_graph_candidates(
        records=records,
        seen_ids=set(state["seen_ids"]),
        top_n_directors=10,
        max_candidates=20,
    )
    langfuse_context.update_current_observation(
        output={"n_graph_hits": len(hits)},
    )
    return {**state, "graph_hits": hits}


@observe(name="rerank_by_taste")
def rerank_by_taste(state: AgentState) -> AgentState:
    profile = state["taste_profile"]
    div     = profile.get("divergence_profile", {})

    def taste_score(film: dict) -> float:
        """Score based on how well the film's dimensions align with the divergence profile."""
        score = 0.0
        for dimension, group_divs in div.items():
            val = film.get(dimension)
            if val and val in group_divs:
                score += group_divs[val]  # positive = user historically likes this
        return score

    # Merge RAG and graph hits; deduplicate by tmdb_id
    seen_in_merge: set[int] = set()
    merged: list[dict] = []
    for film in state["rag_hits"] + state["graph_hits"]:
        tid = film.get("tmdb_id")
        if tid and tid not in seen_in_merge:
            seen_in_merge.add(tid)
            film["taste_score"] = taste_score(film)
            merged.append(film)

    merged.sort(key=lambda x: (
        x.get("taste_score", 0) * 0.5 + x.get("score", 0) * 0.3 +
        x.get("graph_score", 0) * 0.2
    ), reverse=True)

    n_films   = profile.get("trained_on_n_films", 0)
    confidence = (
        "low"       if n_films < 50  else
        "medium"    if n_films < 150 else
        "high"
    )
    langfuse_context.update_current_observation(
        output={"n_candidates": len(merged[:12]), "confidence": confidence},
        metadata={"top_taste_score": merged[0].get("taste_score", 0) if merged else 0},
    )
    return {**state, "candidates": merged[:12], "confidence": confidence}


@observe(name="synthesize")
def synthesize(state: AgentState) -> AgentState:
    profile   = state["taste_profile"]
    candidates = state["candidates"]

    if not candidates:
        return {**state, "recommendations": [], "confidence": "low"}

    dims    = profile.get("interpretable_dimensions", [])[:8]
    weights = profile.get("ridge_dimension_weights", {})
    div     = profile.get("divergence_profile", {})

    # Build divergence summary for the prompt
    likes, dislikes = [], []
    for dimension, groups in div.items():
        for val, delta in sorted(groups.items(), key=lambda x: x[1], reverse=True):
            if delta > 0.15:
                likes.append(f"{dimension}={val} ({delta:+.2f})")
            elif delta < -0.15:
                dislikes.append(f"{dimension}={val} ({delta:+.2f})")

    taste_summary = (
        f"Top craft dimensions: {', '.join(dims[:6])}\n"
        f"Rates ABOVE consensus: {', '.join(likes[:6]) or 'none notable'}\n"
        f"Rates BELOW consensus: {', '.join(dislikes[:6]) or 'none notable'}\n"
        f"Mean rating: {profile.get('mean_user_rating', 3.5)} ★  "
        f"({profile.get('trained_on_n_films', '?')} films)"
    )

    candidate_summaries = []
    for i, film in enumerate(candidates[:10], 1):
        via = film.get("via_path") or film.get("hop_type") or film.get("source", "unknown")
        dims_list = [k for k in [
            "director_lineage", "pacing_signature", "reality_register",
            "tone_primary", "body_experience", "production_register",
        ] if film.get(k)]
        dim_str = ", ".join(f"{k}={film[k]}" for k in dims_list[:4])
        candidate_summaries.append(
            f"{i}. {film.get('title')} ({film.get('year')})  "
            f"[tmdb_id={film.get('tmdb_id')}]  via={via}\n"
            f"   Craft: {dim_str}\n"
            f"   Taste score: {film.get('taste_score', 0):.3f}  "
            f"Similarity: {film.get('score', film.get('graph_score', 0)):.3f}"
        )

    prompt = f"""You are recommending films to a specific viewer based on their measurable craft preferences.

USER QUERY: "{state['query']}"

USER TASTE PROFILE:
{taste_summary}

CANDIDATE FILMS (pre-ranked by taste alignment):
{chr(10).join(candidate_summaries)}

Select the 3 best recommendations from the candidates.
For each, write an explanation that:
  - References at least 2 specific craft dimensions from the taste profile
  - Explains WHY those dimensions make this film a good match
  - Uses concrete, specific language (not generic praise)
  - Notes the path: 'rag_similarity' if similar to liked films, 'graph_influence' if via director lineage

If the taste model has limited signal (< 50 films), note this in confidence_note."""

    result = _client.chat.completions.create(
        model=_MODEL,
        response_model=SynthesisOutput,
        max_retries=2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a film taste analyst. Write recommendations grounded in "
                    "specific craft dimensions — not plot summaries or genre labels. "
                    "Every recommendation must cite named dimensions from the taste profile."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    recs = [r.model_dump() for r in result.recommendations]
    langfuse_context.update_current_observation(
        output={"n_recommendations": len(recs), "confidence_note": result.confidence_note},
        metadata={"model": _MODEL, "titles": [r["title"] for r in recs]},
    )
    return {**state, "recommendations": recs, "confidence": state["confidence"]}


# ── Graph assembly ────────────────────────────────────────────────

def build_agent():
    g = StateGraph(AgentState)
    g.add_node("rag_retrieve",    rag_retrieve)
    g.add_node("graph_traverse",  graph_traverse)
    g.add_node("rerank_by_taste", rerank_by_taste)
    g.add_node("synthesize",      synthesize)

    g.set_entry_point("rag_retrieve")
    g.add_edge("rag_retrieve",    "graph_traverse")
    g.add_edge("graph_traverse",  "rerank_by_taste")
    g.add_edge("rerank_by_taste", "synthesize")
    g.add_edge("synthesize",      END)

    return g.compile()


# ── Public entry point ────────────────────────────────────────────

@observe(name="recommend")
def recommend(query: str) -> dict:
    """Run the recommendation agent. Returns final state."""
    records       = load_enriched()
    taste_profile = load_taste_profile()
    seen_ids      = [r.tmdb_id for r in records if r.tmdb_id and r.rating is not None]

    langfuse_context.update_current_observation(
        input={"query": query},
        metadata={
            "n_seen_films": len(seen_ids),
            "taste_model_version": taste_profile.get("model_version"),
            "trained_on_n_films": taste_profile.get("trained_on_n_films"),
        },
    )

    agent = build_agent()
    initial_state: AgentState = {
        "query":                   query,
        "seen_ids":                seen_ids,
        "taste_profile":           taste_profile,
        "rag_hits":                [],
        "graph_hits":              [],
        "candidates":              [],
        "recommendations":         [],
        "confidence":              "medium",
        "craft_query_resolution":  "",
    }
    result = agent.invoke(initial_state)

    langfuse_context.update_current_observation(
        output={"n_recommendations": len(result.get("recommendations", []))},
    )
    return result
