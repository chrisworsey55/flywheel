from __future__ import annotations

from collections import Counter
from typing import Sequence

import numpy as np

from .experiments import FRAMINGS, OFFER_TYPES, Experiment


def embed_experiment(exp: Experiment) -> list[float]:
    rule = exp.feature_rule
    values: list[float] = []
    values.extend([1.0 if rule.get("offer_type") == item else 0.0 for item in OFFER_TYPES])
    values.extend([1.0 if rule.get("framing") == item else 0.0 for item in FRAMINGS])
    values.append(float(rule.get("min_urgency", 0.0)))
    values.append(1.0 if rule.get("numeric_offer_present") is True else 0.0)
    values.append(1.0 if rule.get("has_emoji") is True else 0.0)
    values.append(float(exp.confidence))
    return values


def embeddings(experiments: Sequence[Experiment]) -> np.ndarray:
    if not experiments:
        return np.empty((0, 0))
    return np.asarray([embed_experiment(exp) for exp in experiments], dtype=float)


def n_eff_ratio(experiments: Sequence[Experiment], seed: int = 7) -> tuple[float, float, dict[int, int]]:
    # Adapted from ATLAS Phase B: inverse-Simpson effective breadth over candidate
    # embeddings. The cluster id is deterministic and dependency-light for demos.
    n = len(experiments)
    if n == 0:
        return 0.0, 0.0, {}
    labels = []
    for exp in experiments:
        key = tuple(round(v, 2) for v in embed_experiment(exp))
        labels.append(hash((key, seed)) % max(2, min(n, 18)))
    counts = Counter(labels)
    probs = np.asarray([count / n for count in counts.values()], dtype=float)
    n_eff = 1.0 / float(np.sum(probs**2))
    return n_eff, n_eff / n, dict(counts)


def novelty_scores(experiments: Sequence[Experiment]) -> dict[str, float]:
    if not experiments:
        return {}
    x = embeddings(experiments)
    if len(experiments) == 1:
        return {experiments[0].id: 1.0}
    distances = np.sqrt(((x[:, None, :] - x[None, :, :]) ** 2).sum(axis=2))
    nearest = np.sort(distances + np.eye(len(experiments)) * 999.0, axis=1)[:, :5]
    raw = nearest.mean(axis=1)
    lo, hi = float(raw.min()), float(raw.max())
    scaled = (raw - lo) / (hi - lo + 1e-9)
    return {exp.id: float(score) for exp, score in zip(experiments, scaled)}

