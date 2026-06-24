from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from data.label import LabeledAd

from .agents import default_scoring_agents
from .features import CreativeFeatures, extract_features


@dataclass(frozen=True)
class Prediction:
    ad: LabeledAd
    features: CreativeFeatures
    p_winner: float
    predicted_label: int


@dataclass(frozen=True)
class PredictionMetrics:
    accuracy: float
    precision: float
    recall: float
    auc: float
    calibration: float
    n_train: int
    n_holdout: int


def temporal_split(rows: Sequence[LabeledAd], cycle: int, cycles: int) -> tuple[list[LabeledAd], list[LabeledAd]]:
    ordered = sorted(rows, key=lambda row: (row.ad.started, row.ad.id))
    n = len(ordered)
    if n < 8:
        cut = max(1, n // 2)
        return ordered[:cut], ordered[cut:]
    holdout_size = max(4, n // max(cycles + 1, 2))
    start = min(max(2, int(n * 0.45) + cycle * max(1, (n - holdout_size - 2) // max(cycles, 1))), n - holdout_size)
    return ordered[:start], ordered[start : start + holdout_size]


def train_and_predict(train: list[LabeledAd], holdout: list[LabeledAd]) -> list[Prediction]:
    agents = default_scoring_agents()
    train_rows = [(extract_features(row), row.label) for row in train]
    for agent in agents:
        agent.fit(train_rows)
    predictions: list[Prediction] = []
    for row in holdout:
        features = extract_features(row)
        p = sum(agent.predict(features) for agent in agents) / len(agents)
        predictions.append(Prediction(row, features, p, int(p >= 0.5)))
    return predictions


def metrics(predictions: list[Prediction], n_train: int) -> PredictionMetrics:
    if not predictions:
        return PredictionMetrics(0, 0, 0, 0.5, 0, n_train, 0)
    y = [p.ad.label for p in predictions]
    pvals = [p.p_winner for p in predictions]
    labels = [p.predicted_label for p in predictions]
    tp = sum(1 for yi, pi in zip(y, labels) if yi == 1 and pi == 1)
    fp = sum(1 for yi, pi in zip(y, labels) if yi == 0 and pi == 1)
    fn = sum(1 for yi, pi in zip(y, labels) if yi == 1 and pi == 0)
    acc = sum(1 for yi, pi in zip(y, labels) if yi == pi) / len(y)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    calibration = sum(abs(pi - yi) for yi, pi in zip(y, pvals)) / len(y)
    return PredictionMetrics(acc, precision, recall, _auc(y, pvals), calibration, n_train, len(predictions))


def _auc(y: list[int], scores: list[float]) -> float:
    pos = [s for yi, s in zip(y, scores) if yi == 1]
    neg = [s for yi, s in zip(y, scores) if yi == 0]
    if not pos or not neg:
        return 0.5
    wins = 0.0
    for ps in pos:
        for ns in neg:
            wins += 1.0 if ps > ns else 0.5 if math.isclose(ps, ns) else 0.0
    return wins / (len(pos) * len(neg))

