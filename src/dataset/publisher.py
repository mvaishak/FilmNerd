"""
Dataset Publisher — packages craft annotations for Hugging Face.

Produces a JSONL dataset where each row is one film with:
  - TMDB metadata (title, year, runtime, language, genres, crew)
  - All 20 craft dimension annotations
  - Annotation metadata (model, version, confidence)

Personal ratings and review text are stripped before publishing.

Usage:
  python -m src.dataset.publisher                          # export to data/export/
  python -m src.dataset.publisher --push --repo username/film-craft-annotations
"""
import json
from pathlib import Path
from typing import Any

from ..annotation.store import load_annotations
from ..enrichment.store import load_enriched

EXPORT_DIR = Path("data/export")

# Fields stripped before public export
_PRIVATE_FIELDS = {
    "user_rating", "user_review_text", "watch_date",
    "critical_divergence",  # derived from private rating
}


def _serialise(v: Any) -> Any:
    """Recursively convert enums, dataclasses, and Pydantic models to JSON-safe values."""
    if v is None:
        return None
    if hasattr(v, "value"):          # str Enum
        return v.value
    if hasattr(v, "model_dump"):     # Pydantic model
        return {k: _serialise(val) for k, val in v.model_dump().items()}
    if hasattr(v, "__dataclass_fields__"):  # dataclass (e.g. CrewMember)
        import dataclasses
        return {f.name: _serialise(getattr(v, f.name)) for f in dataclasses.fields(v)}
    if isinstance(v, list):
        return [_serialise(i) for i in v]
    if isinstance(v, dict):
        return {k: _serialise(val) for k, val in v.items()}
    return v


# Keep old name as alias used in annotation loop
_enum_val = _serialise


def build_rows(
    strip_private: bool = True,
) -> list[dict]:
    annotations = load_annotations()
    records     = load_enriched()
    rec_map     = {r.tmdb_id: r for r in records if r.tmdb_id}

    rows = []
    for ann in annotations:
        rec = rec_map.get(ann.tmdb_id, None)

        # TMDB metadata from enriched record
        tmdb = {}
        if rec:
            tmdb = {
                "tmdb_rating":          rec.tmdb_rating,
                "tmdb_vote_count":      rec.tmdb_vote_count,
                "runtime_minutes":      rec.runtime,
                "original_language":    rec.original_language,
                "production_countries": rec.production_countries or [],
                "genres":               rec.genres or [],
                "director":             _serialise(rec.director),
                "cinematographer":      _serialise(rec.cinematographer),
                "editor":               _serialise(rec.editor),
                "writer":               _serialise(rec.writer),
                "composer":             _serialise(rec.composer),
            }

        # Craft annotation fields
        ann_dict = ann.model_dump()
        if strip_private:
            for f in _PRIVATE_FIELDS:
                ann_dict.pop(f, None)

        # Normalise enums to their string values
        for k, v in ann_dict.items():
            ann_dict[k] = _enum_val(v)

        row = {**ann_dict, **tmdb}
        rows.append(row)

    return rows


def export_jsonl(
    output_path: Path | None = None,
    strip_private: bool = True,
) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = output_path or EXPORT_DIR / "film_craft_annotations.jsonl"

    rows = build_rows(strip_private=strip_private)
    with output_path.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Exported {len(rows)} records → {output_path}")
    return output_path


def export_dataset_card(output_path: Path | None = None) -> Path:
    output_path = output_path or EXPORT_DIR / "README.md"
    rows = build_rows()

    # Compute some stats for the card
    from collections import Counter
    pacing_counts = Counter(r.get("pacing_signature") for r in rows)
    lang_counts   = Counter(r.get("original_language") for r in rows if r.get("original_language"))
    top_langs     = ", ".join(f"{k} ({v})" for k, v in lang_counts.most_common(5))
    top_pacing    = ", ".join(f"{k} ({v})" for k, v in pacing_counts.most_common())

    card = f"""---
license: cc-by-4.0
language:
- en
tags:
- film
- cinema
- craft-dimensions
- recommendation
- taste-modelling
size_categories:
- 100<n<1K
---

# Film Craft Annotations

A structured dataset of **{len(rows)} films** annotated across **20 craft dimensions** by an LLM (GPT-4o via Instructor structured outputs). Each record captures a film's aesthetic and formal properties — not plot tags or genres, but the craft choices that define how a film looks, feels, and moves.

## Dimensions

| Dimension | Description |
|---|---|
| `narrative_time` | Temporal structure: linear, non-linear, fragmented, cyclical, parallel |
| `pacing_signature` | Felt tempo: slow_burn, measured, propulsive, frenetic, variable |
| `point_of_view` | Whose perspective organises the narration |
| `ending_valence` | Emotional register of the resolution |
| `tone_primary` | Dominant emotional register |
| `reality_register` | Relationship to physical/social reality |
| `moral_complexity` | How the film treats moral questions |
| `character_legibility` | Psychological transparency of characters |
| `dialogue_density` | Amount and function of dialogue |
| `cinematographic_language` | Visual language and camera style |
| `colour_palette` | Dominant colour approach |
| `editor_signature` | Editing rhythm and style |
| `score_style` | Music approach |
| `world_building_depth` | How much the film constructs its world |
| `genre_subversion` | Degree of genre deconstruction |
| `thematic_primary` | Dominant thematic concern |
| `thematic_secondary` | Secondary thematic concerns (list) |
| `director_lineage` | Cinematic tradition the director belongs to |
| `body_experience` | Physical sensation the film produces |
| `production_register` | Budget and production scale |

## Statistics

- **{len(rows)} films** annotated
- **Top languages**: {top_langs}
- **Pacing distribution**: {top_pacing}

## Annotation Method

Each film was annotated using GPT-4o with Instructor structured outputs against a locked Pydantic schema. Annotations are cached by TMDB ID. Personal ratings and review text have been stripped before publication.

## Usage

```python
from datasets import load_dataset

ds = load_dataset("YOUR_USERNAME/film-craft-annotations")
df = ds["train"].to_pandas()

# Films with slow-burn pacing and expressionistic cinematography
filtered = df[
    (df["pacing_signature"] == "slow_burn") &
    (df["cinematographic_language"] == "expressionistic")
]
```

## Citation

If you use this dataset, please cite the [Film Taste Intelligence Engine](https://github.com/YOUR_USERNAME/yesiamafilmnerd) project.
"""
    output_path.write_text(card)
    print(f"Dataset card written → {output_path}")
    return output_path


def push_to_hub(repo_id: str, token: str | None = None):
    """Push the exported dataset to Hugging Face Hub."""
    try:
        from datasets import Dataset
    except ImportError:
        raise ImportError("pip install datasets")

    rows = build_rows(strip_private=True)
    ds   = Dataset.from_list(rows)

    ds.push_to_hub(
        repo_id,
        token=token,
        commit_message=f"Update: {len(rows)} films annotated",
    )
    print(f"Dataset pushed to hub: {repo_id}")
