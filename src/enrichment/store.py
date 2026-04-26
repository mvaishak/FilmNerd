# src/enrichment/store.py
import json
from pathlib import Path
from ..ingestion.models import FilmRecord

ENRICHED_PATH = Path("data/processed/enriched_films.json")

def save_enriched(records: list[FilmRecord]):
    ENRICHED_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = [r.model_dump() for r in records]
    ENRICHED_PATH.write_text(json.dumps(data, indent=2, default=str))
    print(f"Saved {len(records)} records to {ENRICHED_PATH}")

def load_enriched() -> list[FilmRecord]:
    if not ENRICHED_PATH.exists():
        raise FileNotFoundError("No enriched records found. Run the enrichment pipeline first.")
    data = json.loads(ENRICHED_PATH.read_text())
    return [FilmRecord(**r) for r in data]