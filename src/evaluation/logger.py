"""
Ground truth evaluation — MAE, accuracy buckets, per-model-version breakdown.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

from ..annotation.schema import PredictionRecord
from ..prediction.store import get_all


@dataclass
class EvalReport:
    n_total:          int
    n_evaluated:      int
    mae:              float | None        # mean absolute error
    within_half_star: float | None        # fraction with |error| <= 0.5
    within_one_star:  float | None        # fraction with |error| <= 1.0
    mean_predicted:   float | None
    mean_actual:      float | None
    by_version:       dict[int, "VersionStats"]

    def __str__(self) -> str:
        lines = [
            f"Predictions total : {self.n_total}",
            f"With actual rating: {self.n_evaluated}",
        ]
        if self.mae is None:
            lines.append("No evaluated predictions yet.")
            return "\n".join(lines)

        lines += [
            f"MAE               : {self.mae:.3f} ★",
            f"Within ½ ★        : {self.within_half_star:.1%}",
            f"Within 1 ★        : {self.within_one_star:.1%}",
            f"Mean predicted    : {self.mean_predicted:.2f} ★",
            f"Mean actual       : {self.mean_actual:.2f} ★",
        ]
        if self.by_version:
            lines.append("\nBy model version:")
            for ver, stats in sorted(self.by_version.items()):
                lines.append(
                    f"  v{ver}: n={stats.n}  MAE={stats.mae:.3f} ★  "
                    f"within½={stats.within_half_star:.1%}"
                )
        return "\n".join(lines)


@dataclass
class VersionStats:
    n:               int
    mae:             float
    within_half_star: float


def compute_report(records: list[PredictionRecord] | None = None) -> EvalReport:
    if records is None:
        records = get_all()

    evaluated = [r for r in records if r.actual_rating is not None]

    if not evaluated:
        return EvalReport(
            n_total=len(records), n_evaluated=0,
            mae=None, within_half_star=None, within_one_star=None,
            mean_predicted=None, mean_actual=None,
            by_version={},
        )

    errors = [r.prediction_error for r in evaluated]
    mae    = statistics.mean(errors)

    within_half = sum(1 for e in errors if e <= 0.5) / len(errors)
    within_one  = sum(1 for e in errors if e <= 1.0) / len(errors)

    mean_pred   = statistics.mean(r.predicted_rating for r in evaluated)
    mean_actual = statistics.mean(r.actual_rating    for r in evaluated)

    by_version: dict[int, VersionStats] = {}
    version_groups: dict[int, list[PredictionRecord]] = {}
    for r in evaluated:
        version_groups.setdefault(r.taste_model_version, []).append(r)
    for ver, group in version_groups.items():
        errs = [g.prediction_error for g in group]
        by_version[ver] = VersionStats(
            n=len(group),
            mae=statistics.mean(errs),
            within_half_star=sum(1 for e in errs if e <= 0.5) / len(errs),
        )

    return EvalReport(
        n_total=len(records),
        n_evaluated=len(evaluated),
        mae=mae,
        within_half_star=within_half,
        within_one_star=within_one,
        mean_predicted=mean_pred,
        mean_actual=mean_actual,
        by_version=by_version,
    )
