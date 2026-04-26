"""
Builds and maintains the Qdrant vector index over craft annotations.

Each document = one annotated film.
Vector = nomic-embed-text-v1.5 embedding of a craft-dimension text description.
Payload = full annotation metadata used for filtering and re-ranking.

Run:  python -m src.agent.qdrant_index
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from ..annotation.schema import CraftAnnotation
from ..annotation.store import load_annotations
from ..enrichment.store import load_enriched

load_dotenv()

COLLECTION   = "films"
VECTOR_DIM   = 768  # nomic-embed-text-v1.5 default

_embed_client = OpenAI(
    base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
    api_key="lm-studio",
)
_EMBED_MODEL = os.getenv("LM_STUDIO_EMBED_MODEL", "nomic-embed-text-v1.5")
_QDRANT_URL  = os.getenv("QDRANT_URL", "http://localhost:6333")


def annotation_text(ann: CraftAnnotation) -> str:
    def v(field: str) -> str:
        val = getattr(ann, field, None)
        if val is None:
            return "unknown"
        return val.value if hasattr(val, "value") else str(val)

    sec = ann.thematic_secondary or []
    sec_str = " ".join(t.value if hasattr(t, "value") else str(t) for t in sec)

    return (
        f"{ann.title} {ann.year} "
        f"{v('director_lineage')} cinema "
        f"pacing {v('pacing_signature')} "
        f"reality {v('reality_register')} "
        f"tone {v('tone_primary')} "
        f"cinematography {v('cinematographic_language')} "
        f"colour {v('colour_palette')} "
        f"editing {v('editor_signature')} "
        f"score {v('score_style')} "
        f"theme {v('thematic_primary')} {sec_str} "
        f"moral {v('moral_complexity')} "
        f"body {v('body_experience')} "
        f"production {v('production_register')} "
        f"ending {v('ending_valence')}"
    )


def _embed(texts: list[str]) -> list[list[float]]:
    resp = _embed_client.embeddings.create(model=_EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def _annotation_payload(ann: CraftAnnotation, user_rating: float | None) -> dict:
    def v(field: str) -> str | None:
        val = getattr(ann, field, None)
        if val is None:
            return None
        return val.value if hasattr(val, "value") else str(val)

    return {
        "tmdb_id":                ann.tmdb_id,
        "title":                  ann.title,
        "year":                   ann.year,
        "user_rating":            user_rating,
        "has_rating":             user_rating is not None,
        "director_lineage":       v("director_lineage"),
        "pacing_signature":       v("pacing_signature"),
        "reality_register":       v("reality_register"),
        "tone_primary":           v("tone_primary"),
        "cinematographic_language": v("cinematographic_language"),
        "colour_palette":         v("colour_palette"),
        "editor_signature":       v("editor_signature"),
        "score_style":            v("score_style"),
        "thematic_primary":       v("thematic_primary"),
        "moral_complexity":       v("moral_complexity"),
        "body_experience":        v("body_experience"),
        "production_register":    v("production_register"),
        "ending_valence":         v("ending_valence"),
        "dialogue_density":       v("dialogue_density"),
        "world_building_depth":   v("world_building_depth"),
        "genre_subversion":       v("genre_subversion"),
    }


def build_index(batch_size: int = 32):
    annotations = load_annotations()
    records      = load_enriched()
    rating_map   = {r.tmdb_id: r.rating for r in records if r.tmdb_id}

    qdrant = QdrantClient(url=_QDRANT_URL)

    existing = {c.name for c in qdrant.get_collections().collections}
    if COLLECTION not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
        print(f"Created Qdrant collection '{COLLECTION}'")
    else:
        print(f"Collection '{COLLECTION}' already exists — upserting")

    total = 0
    for i in range(0, len(annotations), batch_size):
        batch = annotations[i : i + batch_size]
        texts  = [annotation_text(ann) for ann in batch]
        vectors = _embed(texts)

        points = [
            PointStruct(
                id=ann.tmdb_id,
                vector=vec,
                payload=_annotation_payload(ann, rating_map.get(ann.tmdb_id)),
            )
            for ann, vec in zip(batch, vectors)
        ]
        qdrant.upsert(collection_name=COLLECTION, points=points)
        total += len(points)
        print(f"  Indexed {total}/{len(annotations)}")

    print(f"\nQdrant index built — {total} films in '{COLLECTION}'")


def search(
    query_text: str,
    limit: int = 15,
    filter_unseen: bool = False,
    min_rating: float | None = None,
) -> list[dict]:
    """Semantic search over indexed annotations."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

    qdrant  = QdrantClient(url=_QDRANT_URL)
    [vec]   = _embed([query_text])

    conditions = []
    if filter_unseen:
        conditions.append(FieldCondition(key="has_rating", match=MatchValue(value=False)))
    if min_rating is not None:
        conditions.append(FieldCondition(key="user_rating", range=Range(gte=min_rating)))

    query_filter = Filter(must=conditions) if conditions else None

    result = qdrant.query_points(
      collection_name=COLLECTION,                                      
      query=vec,                                         
      limit=limit,
      query_filter=query_filter,                                       
      with_payload=True,
    )                                                                    
    return [                                               
        {"score": h.score, **h.payload}
        for h in result.points
    ]


if __name__ == "__main__":
    build_index()
