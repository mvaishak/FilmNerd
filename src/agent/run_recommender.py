"""
CLI for the LangGraph Recommendation Agent.

Usage:
  python -m src.agent.run_recommender "I want something slow and visually dense"
  python -m src.agent.run_recommender "something melancholic and formally experimental"
  python -m src.agent.run_recommender --predict 12345   # also predict rating for tmdb_id
"""
import argparse
import sys

from .recommender import recommend
from ..prediction.engine import predict_rating
from ..prediction.store import get_prediction, save_prediction
from ..annotation.store import load_annotations
from ..taste.model import load_taste_profile
from ..observability.tracer import flush as lf_flush


def _print_recommendations(state: dict):
    recs = state.get("recommendations", [])
    conf = state.get("confidence", "?")

    if not recs:
        print("No recommendations generated.")
        print("Ensure Qdrant is running and the index has been built:")
        print("  python -m src.agent.qdrant_index")
        return

    print(f"\n{'='*60}")
    print("FILM RECOMMENDATIONS")
    print(f"{'='*60}")
    print(f"Query:      {state['query']}")
    print(f"Confidence: {conf}  ({state['taste_profile'].get('trained_on_n_films', '?')} films in taste model)")
    print()

    for i, rec in enumerate(recs, 1):
        print(f"{i}. {rec['title']} ({rec.get('year', '?')})")
        if rec.get("tmdb_id"):
            print(f"   TMDB: {rec['tmdb_id']}  |  via: {rec.get('via_path', '?')}")
        print(f"   Key dimensions: {', '.join(rec.get('key_dimensions', []))}")
        print(f"   {rec['explanation']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Film Taste Recommendation Agent")
    parser.add_argument("query", nargs="?", help="Natural language recommendation query")
    parser.add_argument(
        "--predict", type=int, metavar="TMDB_ID",
        help="Also predict star rating for a given TMDB ID"
    )
    args = parser.parse_args()

    if not args.query and not args.predict:
        parser.print_help()
        sys.exit(1)

    if args.query:
        print(f"Running recommendation agent for: \"{args.query}\"")
        print("(RAG retrieve → graph traverse → taste rerank → synthesize)")
        state = recommend(args.query)
        _print_recommendations(state)

    if args.predict:
        annotations  = load_annotations()
        ann_map      = {a.tmdb_id: a for a in annotations}
        taste_profile = load_taste_profile()

        ann = ann_map.get(args.predict)
        if not ann:
            print(f"No annotation found for tmdb_id={args.predict}")
            sys.exit(1)

        existing = get_prediction(args.predict)
        if existing:
            print(f"\nExisting prediction for {ann.title}:")
            print(f"  Predicted: {existing.predicted_rating} ★")
            if existing.actual_rating:
                print(f"  Actual:    {existing.actual_rating} ★  (error={existing.prediction_error})")
        else:
            print(f"\nPredicting rating for {ann.title}...")
            record = predict_rating(ann, taste_profile)
            save_prediction(record)
            print(f"  Predicted: {record.predicted_rating} ★")
            print(f"  Dimensions used: {', '.join(record.top_dimensions_used)}")
            print(f"  Saved to predictions store.")


    lf_flush()


if __name__ == "__main__":
    main()
