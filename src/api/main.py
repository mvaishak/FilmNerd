import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import corpus, films, taste, search, log, chat

app = FastAPI(title="filmnerd API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(corpus.router)
app.include_router(films.router)
app.include_router(taste.router)
app.include_router(search.router)
app.include_router(log.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    corpus_size = 0
    model_version = 0
    try:
        data = json.loads(Path("data/processed/annotations.json").read_text())
        corpus_size = len(data)
    except Exception:
        pass
    try:
        profile = json.loads(Path("data/processed/taste_profile.json").read_text())
        model_version = profile.get("model_version", 0)
    except Exception:
        pass
    return {"status": "ok", "corpus_size": corpus_size, "model_version": model_version}
