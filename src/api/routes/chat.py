import json
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..poster import get_poster_path

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


def _run_agent(query: str) -> dict:
    from ...agent.recommender import build_agent
    from ...taste.model import load_taste_profile
    from ...enrichment.store import load_enriched

    profile = load_taste_profile()
    records = load_enriched()
    seen_ids = [r.tmdb_id for r in records if r.tmdb_id and r.rating is not None]

    agent = build_agent()
    state = {
        "query": query,
        "seen_ids": seen_ids,
        "taste_profile": profile,
        "rag_hits": [],
        "graph_hits": [],
        "candidates": [],
        "recommendations": [],
        "confidence": "medium",
        "craft_query_resolution": "",
    }
    return agent.invoke(state)


async def _stream_recommendations(req: ChatRequest) -> AsyncGenerator[str, None]:
    def sse(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _run_agent, req.message)

        recs = result.get("recommendations", [])
        confidence_note = result.get("confidence_note", "")

        if confidence_note:
            for token in confidence_note.split(" "):
                yield sse({"type": "token", "content": token + " "})
                await asyncio.sleep(0.02)

        if recs:
            yield sse({"type": "token", "content": "\n\n"})

        for rec in recs:
            tmdb_id = rec.get("tmdb_id")
            key_dims = rec.get("key_dimensions", [])
            rec_data = {
                "tmdb_id": tmdb_id,
                "title": rec.get("title"),
                "year": rec.get("year"),
                "poster_path": get_poster_path(tmdb_id) if tmdb_id else None,
                "explanation": rec.get("explanation", ""),
                "predicted_rating": rec.get("predicted_rating"),
                "craft_dimensions": {k: rec[k] for k in key_dims if k in rec},
                "knowledge_graph_path": [rec.get("via_path")] if rec.get("via_path") else [],
            }
            yield sse({"type": "recommendation", "data": rec_data})

        yield sse({"type": "done"})

    except Exception as e:
        yield sse({"type": "token", "content": f"Error: {e}"})
        yield sse({"type": "done"})


@router.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        _stream_recommendations(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
