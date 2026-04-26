import json
from pathlib import Path

CACHE_DIR = Path("data/cache/tmdb")


def get_poster_path(tmdb_id: int) -> str | None:
    """Read poster_path from local TMDB details cache."""
    path = CACHE_DIR / f"details_{tmdb_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data.get("poster_path")
    except Exception:
        return None
