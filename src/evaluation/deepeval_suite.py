"""
DeepEval evaluation suite for recommendation quality.

Metrics measured per recommendation session:
  1. Faithfulness       — explanations only claim what the taste profile supports
  2. Answer Relevancy   — recommendations match the user's query intent
  3. Contextual Recall  — taste profile dimensions appear in explanations

Run:  python -m src.evaluation.run_eval
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class RecommendationEvalInput:
    query:         str
    recommendations: list[dict]   # from agent state["recommendations"]
    taste_profile: dict


@dataclass
class EvalResult:
    session_id:         str
    faithfulness_score: float | None
    relevancy_score:    float | None
    recall_score:       float | None
    passed:             bool
    details:            dict


def _build_context_from_profile(profile: dict) -> list[str]:
    """Build the 'context' DeepEval uses to judge faithfulness."""
    dims    = profile.get("interpretable_dimensions", [])[:8]
    div     = profile.get("divergence_profile", {})

    lines = [f"Top craft dimensions: {', '.join(dims)}"]
    for dimension, groups in div.items():
        for val, delta in sorted(groups.items(), key=lambda x: x[1], reverse=True):
            if abs(delta) > 0.1:
                direction = "above" if delta > 0 else "below"
                lines.append(
                    f"User rates {dimension}={val} {direction} consensus by {abs(delta):.2f} stars"
                )
    return lines


def evaluate_session(
    session_input: RecommendationEvalInput,
    session_id: str = "session",
    openai_api_key: str | None = None,
) -> EvalResult:
    """
    Run DeepEval metrics against one recommendation session.
    Requires an OpenAI API key for the evaluation LLM (separate from LM Studio).
    """
    try:
        from deepeval import evaluate
        from deepeval.metrics import (
            FaithfulnessMetric,
            AnswerRelevancyMetric,
            ContextualRecallMetric,
        )
        from deepeval.test_case import LLMTestCase
    except ImportError:
        raise ImportError("deepeval not installed — run: uv add deepeval")

    key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise ValueError(
            "DeepEval requires an OpenAI API key. "
            "Set OPENAI_API_KEY in .env or pass openai_api_key="
        )

    context = _build_context_from_profile(session_input.taste_profile)

    # Combine all recommendation explanations into one output string
    output_text = "\n\n".join(
        f"{r['title']} ({r.get('year', '?')}): {r['explanation']}"
        for r in session_input.recommendations
    )

    # Expected output: query intent should be addressed
    expected = f"Film recommendations that match: {session_input.query}"

    test_case = LLMTestCase(
        input=session_input.query,
        actual_output=output_text,
        expected_output=expected,
        retrieval_context=context,
    )

    faithfulness = FaithfulnessMetric(threshold=0.7, verbose_mode=False)
    relevancy    = AnswerRelevancyMetric(threshold=0.7, verbose_mode=False)
    recall       = ContextualRecallMetric(threshold=0.6, verbose_mode=False)

    results = evaluate([test_case], [faithfulness, relevancy, recall], run_async=False)

    f_score = faithfulness.score if hasattr(faithfulness, "score") else None
    r_score = relevancy.score    if hasattr(relevancy,    "score") else None
    c_score = recall.score       if hasattr(recall,       "score") else None

    passed = all([
        (f_score or 0) >= 0.7,
        (r_score or 0) >= 0.7,
        (c_score or 0) >= 0.6,
    ])

    return EvalResult(
        session_id=session_id,
        faithfulness_score=f_score,
        relevancy_score=r_score,
        recall_score=c_score,
        passed=passed,
        details={
            "n_recommendations": len(session_input.recommendations),
            "context_chunks":    len(context),
        },
    )
