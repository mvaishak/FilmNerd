"""
Batch Prediction CLI.

Usage:
  python -m src.prediction.run_prediction                  # predict all unannotated unseen films
  python -m src.prediction.run_prediction --tmdb-id 12345  # predict one film by TMDB ID
  python -m src.prediction.run_prediction --limit 20       # cap number of new predictions
"""
import argparse
import sys

from ..observability.tracer import flush as lf_flush

from ..annotation.store import load_annotations
from ..enrichment.store import load_enriched
from ..taste.model import load_taste_profile
from .engine import predict_rating
from .store import get_prediction, save_prediction


def main():
    parser = argparse.ArgumentParser(description="Batch film rating predictor")
    parser.add_argument("--tmdb-id", type=int, metavar="ID",
                        help="Predict for a single TMDB ID")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Maximum number of new predictions to generate")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-predict even if a prediction already exists")
    args = parser.parse_args()

    annotations   = load_annotations()
    records       = load_enriched()
    taste_profile = load_taste_profile()

    seen_ids = {r.tmdb_id for r in records if r.tmdb_id and r.rating is not None}
    ann_map  = {a.tmdb_id: a for a in annotations}

    if args.tmdb_id:
        targets = [args.tmdb_id]
    else:
        # All annotated films not in the user's seen/rated set
        targets = [tid for tid in ann_map if tid not in seen_ids]

    new_count = 0
    for tmdb_id in targets:
        if args.limit is not None and new_count >= args.limit:
            break

        ann = ann_map.get(tmdb_id)
        if not ann:
            print(f"  [skip] tmdb_id={tmdb_id} — no annotation")
            continue

        if not args.overwrite and get_prediction(tmdb_id):
            print(f"  [skip] {ann.title} — prediction exists (use --overwrite to redo)")
            continue

        print(f"  Predicting: {ann.title} ({ann.year}) …", end=" ", flush=True)
        record = predict_rating(ann, taste_profile)
        save_prediction(record)
        print(f"{record.predicted_rating} ★")
        new_count += 1

    print(f"\nDone — {new_count} new predictions saved.")
    lf_flush()


if __name__ == "__main__":
    main()
