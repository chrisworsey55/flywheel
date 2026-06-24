from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Sequence

from .config import FlywheelConfig
from .experiments import Experiment
from .predict import Prediction


@dataclass(frozen=True)
class ExperimentScore:
    experiment: Experiment
    naive_score: float
    honest_score: float
    p_real: float
    segment_n: int
    passed: bool
    fail_reason: str | None


def rule_matches(exp: Experiment, pred: Prediction) -> bool:
    feat = pred.features
    rule = exp.feature_rule
    if "offer_type" in rule and feat.offer_type != rule["offer_type"]:
        return False
    if "framing" in rule and feat.framing != rule["framing"]:
        return False
    if "min_urgency" in rule and feat.urgency_score < float(rule["min_urgency"]):
        return False
    if "numeric_offer_present" in rule and feat.numeric_offer_present is not bool(rule["numeric_offer_present"]):
        return False
    if "has_emoji" in rule and feat.has_emoji is not bool(rule["has_emoji"]):
        return False
    return True


def evaluate_experiments(
    experiments: Sequence[Experiment],
    train_predictions: list[Prediction],
    holdout_predictions: list[Prediction],
    config: FlywheelConfig,
    *,
    trial_count: int | None = None,
) -> list[ExperimentScore]:
    scores: list[ExperimentScore] = []
    m = max(trial_count or len(experiments), 1)
    z_hurdle = NormalDist().inv_cdf(1 - 1 / max(m * 2.0, 2.0))
    for exp in experiments:
        train_seg = [p for p in train_predictions if rule_matches(exp, p)]
        holdout_seg = [p for p in holdout_predictions if rule_matches(exp, p)]
        naive = _accuracy(train_seg)
        honest_raw = _accuracy(holdout_seg)
        fail_reason = None
        if len(holdout_seg) < config.min_holdout_n:
            fail_reason = f"holdout segment n {len(holdout_seg)} below threshold {config.min_holdout_n}"
        if fail_reason:
            scores.append(ExperimentScore(exp, naive, 0.0, 0.0, len(holdout_seg), False, fail_reason))
            continue
        se = math.sqrt(max(honest_raw * (1 - honest_raw) / len(holdout_seg), 1e-6))
        hurdle = z_hurdle * se
        honest = max(0.0, honest_raw - 0.5 - hurdle)
        p_real = NormalDist().cdf((honest_raw - 0.5 - hurdle) / se)
        scores.append(ExperimentScore(exp, naive, honest, p_real, len(holdout_seg), bool(honest > 0 and p_real >= 0.80), None))
    return scores


def _accuracy(rows: list[Prediction]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.predicted_label == row.ad.label) / len(rows)
