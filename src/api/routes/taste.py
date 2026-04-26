import json
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks

router = APIRouter()

TASTE_PROFILE_PATH = Path("data/processed/taste_profile.json")


@router.get("/taste/profile")
def get_taste_profile():
    if not TASTE_PROFILE_PATH.exists():
        return {"error": "No taste profile found. Run taste model training first."}
    return json.loads(TASTE_PROFILE_PATH.read_text())


def _run_retrain():
    from ...annotation.store import load_annotations
    from ...enrichment.store import load_enriched
    from ...taste.model import train_taste_model
    annotations = load_annotations()
    records = load_enriched()
    train_taste_model(annotations, records)


@router.post("/taste/retrain")
def retrain_taste_model(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_retrain)
    return {"status": "retraining started"}
