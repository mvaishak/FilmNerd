# src/annotation/store.py
import json
from pathlib import Path
from .schema import CraftAnnotation

ANNOTATIONS_PATH = Path("data/processed/annotations.json")

def save_annotations(annotations: list[CraftAnnotation]):
    ANNOTATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = [a.model_dump() for a in annotations]
    ANNOTATIONS_PATH.write_text(json.dumps(data, indent=2))
    print(f"Saved {len(annotations)} annotations to {ANNOTATIONS_PATH}")

def load_annotations() -> list[CraftAnnotation]:
    if not ANNOTATIONS_PATH.exists():
        raise FileNotFoundError("No annotations found. Run the annotation pipeline first.")
    data = json.loads(ANNOTATIONS_PATH.read_text())
    return [CraftAnnotation(**a) for a in data]