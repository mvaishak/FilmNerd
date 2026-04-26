"""
Prediction Engine — estimates star rating for a film given the user's taste profile.

Uses Qwen3.5 via LM Studio with the taste profile as structured context.
The prediction is LLM-based rather than sklearn-based because:
  - Unseen films don't have the same feature encoding as training data
  - The LLM can reason about craft alignment explicitly
  - Explanation is a first-class output, not an afterthought
"""
import os
from datetime import datetime, timezone

import instructor
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from ..annotation.schema import CraftAnnotation, PredictionRecord
from ..observability.tracer import get_langfuse  # noqa: F401 — ensures client initialised

try:
    from langfuse.decorators import observe, langfuse_context
except ImportError:
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


class _PredictionOutput(BaseModel):
    predicted_rating: float = Field(
        ge=0.5, le=5.0,
        description="Predicted star rating in 0.5 increments (0.5, 1.0, 1.5 … 5.0)"
    )
    reasoning: str = Field(
        description=(
            "2-3 sentences explaining the prediction referencing specific "
            "craft dimensions from the taste profile"
        )
    )
    confidence: str = Field(
        description="low / medium / high based on how well this film's craft aligns with the taste model"
    )


def _build_taste_summary(profile: dict) -> str:
    dims = profile.get("interpretable_dimensions", profile.get("top_predictive_dimensions", []))
    weights = profile.get("ridge_dimension_weights", profile.get("dimension_weights", {}))

    lines = [
        f"Mean rating:        {profile.get('mean_user_rating', 3.5)} ★  "
        f"(std {profile.get('rating_std', 0.7)})",
        f"Trained on:         {profile.get('trained_on_n_films', '?')} films",
        "",
        "Top predictive craft dimensions (ordered by weight):",
    ]
    for d in dims[:8]:
        w = weights.get(d, 0)
        lines.append(f"  • {d:<32} weight={w:.4f}")

    div = profile.get("divergence_profile", {})
    if div:
        lines.append("")
        lines.append("Where user rates ABOVE consensus (positive = user higher than TMDB avg):")
        for dimension, groups in div.items():
            for val, delta in sorted(groups.items(), key=lambda x: x[1], reverse=True)[:2]:
                if delta > 0.1:
                    lines.append(f"  ↑ {dimension}={val}: {delta:+.2f} stars")
        lines.append("Where user rates BELOW consensus:")
        for dimension, groups in div.items():
            for val, delta in sorted(groups.items(), key=lambda x: x[1])[:2]:
                if delta < -0.1:
                    lines.append(f"  ↓ {dimension}={val}: {delta:+.2f} stars")

    return "\n".join(lines)


def _build_film_summary(ann: CraftAnnotation) -> str:
    def v(field: str) -> str:
        val = getattr(ann, field, None)
        if val is None:
            return "unknown"
        return val.value if hasattr(val, "value") else str(val)

    sec_themes = ann.thematic_secondary or []
    sec_str = ", ".join(
        t.value if hasattr(t, "value") else str(t) for t in sec_themes
    ) or "none"

    return f"""Title:               {ann.title} ({ann.year})
Director lineage:    {v("director_lineage")}
Reality register:    {v("reality_register")}
Pacing signature:    {v("pacing_signature")}
Tone (primary):      {v("tone_primary")}
Cinematography:      {v("cinematographic_language")}
Colour palette:      {v("colour_palette")}
Editing:             {v("editor_signature")}
Score style:         {v("score_style")}
Thematic (primary):  {v("thematic_primary")}
Thematic (secondary):{sec_str}
Moral complexity:    {v("moral_complexity")}
Body experience:     {v("body_experience")}
Production register: {v("production_register")}
Ending valence:      {v("ending_valence")}
Dialogue density:    {v("dialogue_density")}
World-building:      {v("world_building_depth")}
Genre subversion:    {v("genre_subversion")}"""


@observe(name="predict_rating")
def predict_rating(
    annotation: CraftAnnotation,
    taste_profile: dict,
) -> PredictionRecord:
    """
    Predict a star rating for an unseen film.
    Returns a PredictionRecord (actual_rating / prediction_error left as None until logged).
    """
    taste_summary = _build_taste_summary(taste_profile)
    film_summary  = _build_film_summary(annotation)

    prompt = f"""You are predicting a personal film rating for a specific viewer.

USER TASTE PROFILE:
{taste_summary}

FILM TO PREDICT:
{film_summary}

Predict the viewer's star rating (0.5–5.0 in 0.5 increments).
Ground your prediction in the craft dimensions with the highest weights.
Be precise — do not default to the mean unless the film is genuinely neutral on all axes."""

    result = _client.chat.completions.create(
        model=_MODEL,
        response_model=_PredictionOutput,
        max_retries=2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a film taste analyst. You predict personal star ratings "
                    "based on measurable craft dimension preferences, not genre familiarity. "
                    "The user's mean rating is their baseline — predict above it when the film "
                    "aligns with their highest-weight positive dimensions, below it when it conflicts."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    langfuse_context.update_current_observation(
        input={"tmdb_id": annotation.tmdb_id, "title": annotation.title},
        output={"raw_rating": result.predicted_rating, "confidence": result.confidence},
        metadata={"model": _MODEL, "reasoning": result.reasoning},
    )

    # Round to nearest 0.5
    raw = result.predicted_rating
    rounded = round(raw * 2) / 2
    rounded = max(0.5, min(5.0, rounded))

    top_dims = taste_profile.get("interpretable_dimensions", [])[:5]

    return PredictionRecord(
        tmdb_id=annotation.tmdb_id,
        title=annotation.title,
        predicted_rating=rounded,
        actual_rating=None,
        prediction_error=None,
        taste_model_version=taste_profile.get("model_version", 0),
        predicted_at=datetime.now(timezone.utc).isoformat(),
        watched_at=None,
        top_dimensions_used=top_dims,
    )
