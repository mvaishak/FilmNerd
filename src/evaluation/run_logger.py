"""
Ground Truth Logger CLI.

Usage:
  python -m src.evaluation.run_logger pending
  python -m src.evaluation.run_logger log --tmdb-id 12345 --rating 4.0
  python -m src.evaluation.run_logger report
"""
import argparse
import sys

from ..prediction.store import get_pending, log_actual_rating, get_prediction
from .logger import compute_report


def cmd_pending(_args):
    records = get_pending()
    if not records:
        print("No pending predictions (all have been evaluated, or none exist).")
        return
    print(f"{'TMDB ID':<10} {'Title':<40} {'Predicted':>10}  {'Predicted at'}")
    print("-" * 80)
    for r in records:
        predicted_at = r.predicted_at[:10] if r.predicted_at else "?"
        print(f"{r.tmdb_id:<10} {r.title[:40]:<40} {r.predicted_rating:>10.1f} ★  {predicted_at}")


def cmd_log(args):
    tmdb_id = args.tmdb_id
    rating  = args.rating

    if rating < 0.5 or rating > 5.0:
        print(f"Rating must be between 0.5 and 5.0 (got {rating})")
        sys.exit(1)

    # Round to nearest 0.5
    rating = round(rating * 2) / 2

    existing = get_prediction(tmdb_id)
    if not existing:
        print(f"No prediction on file for tmdb_id={tmdb_id}")
        sys.exit(1)

    if existing.actual_rating is not None:
        print(
            f"Already logged: {existing.title}  "
            f"predicted={existing.predicted_rating} ★  actual={existing.actual_rating} ★  "
            f"error={existing.prediction_error}"
        )
        overwrite = input("Overwrite? [y/N] ").strip().lower()
        if overwrite != "y":
            print("Aborted.")
            return

    log_actual_rating(tmdb_id, rating)
    updated = get_prediction(tmdb_id)
    print(
        f"Logged: {updated.title}\n"
        f"  Predicted : {updated.predicted_rating} ★\n"
        f"  Actual    : {updated.actual_rating} ★\n"
        f"  Error     : {updated.prediction_error} ★"
    )


def cmd_report(_args):
    report = compute_report()
    print(f"\n{'='*50}")
    print("PREDICTION ACCURACY REPORT")
    print(f"{'='*50}")
    print(report)
    print()


def main():
    parser = argparse.ArgumentParser(description="Ground Truth Logger for film predictions")
    sub    = parser.add_subparsers(dest="command")

    sub.add_parser("pending", help="List predictions awaiting an actual rating")

    log_p = sub.add_parser("log", help="Record an actual rating for a predicted film")
    log_p.add_argument("--tmdb-id", type=int, required=True, metavar="ID")
    log_p.add_argument("--rating",  type=float, required=True, metavar="STARS",
                       help="Actual star rating (0.5–5.0)")

    sub.add_parser("report", help="Show MAE stats and accuracy breakdown")

    args = parser.parse_args()

    if args.command == "pending":
        cmd_pending(args)
    elif args.command == "log":
        cmd_log(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
