from __future__ import annotations

import random
from dataclasses import dataclass

from data.label import LabeledAd

from .config import FlywheelConfig
from .evaluator import evaluate_experiments
from .experiments import Experiment
from .predict import Prediction


@dataclass(frozen=True)
class MetaEvalResult:
    null_count: int
    evaluated_null_count: int
    fail_closed_count: int
    false_positives: int
    false_positive_rate: float
    passed: bool
    max_null_honest_score: float
    mean_null_honest_score: float
    signal_count: int
    signal_pass_count: int


def run_metaeval(train_predictions: list[Prediction], holdout_predictions: list[Prediction], config: FlywheelConfig) -> MetaEvalResult:
    rng = random.Random(config.seed + 404)
    pool = train_predictions + holdout_predictions
    rules = _candidate_rules(pool)
    false_positives = 0
    fail_closed = 0
    honest_scores: list[float] = []

    for i in range(config.metaeval_nulls):
        null = Experiment(
            hypothesis=f"Known-null shuffled-label feature subset {i}",
            predicts="winner",
            feature_rule=dict(rng.choice(rules)),
            segment="metaeval shuffled-label null",
            confidence=0.5,
            agent="metaeval_null",
        )
        shuffled = _shuffle_labels(pool, rng)
        score = evaluate_experiments([null], shuffled, shuffled, config, trial_count=config.experiments_per_cycle * 2)[0]
        if score.fail_reason:
            fail_closed += 1
        else:
            honest_scores.append(score.honest_score)
            # Clearing the bar means positive multiple-testing-deflated evidence.
            # This should happen around the nominal 5% rate under a real null.
            if score.honest_score > 0:
                false_positives += 1

    signal_scores = evaluate_experiments(_signal_experiments(), pool, pool, config, trial_count=config.experiments_per_cycle * 2)
    signal_pass_count = sum(1 for row in signal_scores if row.honest_score > 0)
    evaluated = config.metaeval_nulls - fail_closed
    fpr = false_positives / max(evaluated, 1)
    return MetaEvalResult(
        null_count=config.metaeval_nulls,
        evaluated_null_count=evaluated,
        fail_closed_count=fail_closed,
        false_positives=false_positives,
        false_positive_rate=fpr,
        passed=fpr <= config.max_false_positive_rate and evaluated >= int(config.metaeval_nulls * 0.85) and signal_pass_count > 0,
        max_null_honest_score=max(honest_scores or [0.0]),
        mean_null_honest_score=sum(honest_scores) / max(len(honest_scores), 1),
        signal_count=len(signal_scores),
        signal_pass_count=signal_pass_count,
    )


def _candidate_rules(predictions: list[Prediction]) -> list[dict[str, object]]:
    rules: list[dict[str, object]] = [{}]
    for attr in ("offer_type", "framing", "numeric_offer_present"):
        values = sorted({getattr(row.features, attr) for row in predictions}, key=str)
        for value in values:
            rule = {attr: value}
            if sum(1 for row in predictions if _matches_rule(row, rule)) >= 12:
                rules.append(rule)
    return rules


def _signal_experiments() -> list[Experiment]:
    return [
        Experiment("Free-bet ads should survive above baseline.", "winner", {"offer_type": "free_bet"}, "metaeval true-signal control", 0.7, "metaeval_signal"),
        Experiment("Deposit-match ads should survive above baseline.", "winner", {"offer_type": "deposit_match"}, "metaeval true-signal control", 0.7, "metaeval_signal"),
    ]


def _shuffle_labels(predictions: list[Prediction], rng: random.Random) -> list[Prediction]:
    labels = [row.ad.label for row in predictions]
    rng.shuffle(labels)
    out: list[Prediction] = []
    for row, label in zip(predictions, labels):
        ad = LabeledAd(row.ad.ad, label, "WINNER" if label else "LOSER", row.ad.days_running)
        out.append(Prediction(ad, row.features, row.p_winner, row.predicted_label))
    return out


def _matches_rule(row: Prediction, rule: dict[str, object]) -> bool:
    for key, value in rule.items():
        if getattr(row.features, key) != value:
            return False
    return True
