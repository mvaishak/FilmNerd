"""
Evaluation CLI — runs DeepEval metrics against a live recommendation session.

Usage:
  python -m src.evaluation.run_eval "I want something slow and visually dense"
  python -m src.evaluation.run_eval "something formally experimental" --session my_test
"""
import argparse
import sys

from ..agent.recommender import recommend
from ..taste.model import load_taste_profile
from .deepeval_suite import RecommendationEvalInput, evaluate_session


def main():
    parser = argparse.ArgumentParser(description="Evaluate recommendation quality with DeepEval")
    parser.add_argument("query", help="Natural language recommendation query to evaluate")
    parser.add_argument("--session", default="eval", metavar="ID",
                        help="Session label for logging (default: eval)")
    args = parser.parse_args()

    print(f'Running recommendation agent for: "{args.query}"')
    state = recommend(args.query)

    recs = state.get("recommendations", [])
    if not recs:
        print("No recommendations returned — cannot evaluate.")
        sys.exit(1)

    print(f"Got {len(recs)} recommendations. Running DeepEval metrics...")

    taste_profile = load_taste_profile()
    session_input = RecommendationEvalInput(
        query=args.query,
        recommendations=recs,
        taste_profile=taste_profile,
    )

    result = evaluate_session(session_input, session_id=args.session)

    print(f"\n{'='*50}")
    print("EVALUATION RESULTS")
    print(f"{'='*50}")
    print(f"Session:      {result.session_id}")
    print(f"Faithfulness: {result.faithfulness_score:.3f}" if result.faithfulness_score is not None else "Faithfulness: n/a")
    print(f"Relevancy:    {result.relevancy_score:.3f}"    if result.relevancy_score    is not None else "Relevancy:    n/a")
    print(f"Recall:       {result.recall_score:.3f}"       if result.recall_score       is not None else "Recall:       n/a")
    print(f"Passed:       {'YES' if result.passed else 'NO'}")
    print()


if __name__ == "__main__":
    main()
