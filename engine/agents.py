from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass

from .experiments import Experiment, make_experiment
from .features import CreativeFeatures


class GeneratorAgent:
    def __init__(self, name: str, prior: str) -> None:
        self.name = name
        self.prior = prior

    def propose(self, rng: random.Random, n: int) -> list[Experiment]:
        return [make_experiment(rng, agent=self.name, prior=self.prior) for _ in range(n)]


def default_swarm() -> list[GeneratorAgent]:
    # Adapted from ATLAS multi-agent generation: deliberately different priors
    # create breadth before the honesty gate starts culling.
    return [
        GeneratorAgent("offer_lab", "offer"),
        GeneratorAgent("framing_desk", "framing"),
        GeneratorAgent("urgency_desk", "urgency"),
        GeneratorAgent("clarity_desk", "mixed"),
        GeneratorAgent("contrarian", "contrarian"),
    ]


@dataclass
class ScoringAgent:
    name: str
    weights: dict[str, float]
    bias: float = 0.0

    def fit(self, rows: list[tuple[CreativeFeatures, int]]) -> None:
        counts: dict[str, Counter[int]] = defaultdict(Counter)
        for feat, label in rows:
            for key, value in _feature_items(feat):
                counts[f"{key}={value}"][label] += 1
        for key, counter in counts.items():
            total = counter[0] + counter[1]
            if total >= 2:
                self.weights[key] = self.weights.get(key, 0.0) + ((counter[1] + 1) / (total + 2) - 0.5)
        if rows:
            base = (sum(label for _, label in rows) + 1) / (len(rows) + 2)
            self.bias = math.log(base / (1 - base))

    def predict(self, feat: CreativeFeatures) -> float:
        score = self.bias
        for key, value in _feature_items(feat):
            score += self.weights.get(f"{key}={value}", 0.0)
        score += self.weights.get("urgency", 0.0) * feat.urgency_score
        score += self.weights.get("numeric", 0.0) * float(feat.numeric_offer_present)
        return 1 / (1 + math.exp(-max(-8, min(8, score))))


def default_scoring_agents() -> list[ScoringAgent]:
    return [
        ScoringAgent("offer_led", {"offer_type=free_bet": 0.30, "offer_type=odds_boost": 0.18, "numeric": 0.16}),
        ScoringAgent("framing_led", {"framing=national_team": 0.22, "framing=world_cup": 0.18}),
        ScoringAgent("urgency_led", {"urgency": 0.42, "cta_type=bet_now": 0.18}),
        ScoringAgent("clarity_led", {"offer_type=none": -0.18, "framing=generic": -0.10}),
        ScoringAgent("contrarian_novelty", {"has_emoji=True": 0.10, "offer_type=bet_insurance": 0.20, "offer_type=deposit_match": 0.08}),
    ]


def _feature_items(feat: CreativeFeatures) -> list[tuple[str, object]]:
    return [
        ("offer_type", feat.offer_type),
        ("framing", feat.framing),
        ("cta_type", feat.cta_type),
        ("has_emoji", feat.has_emoji),
        ("numeric_offer_present", feat.numeric_offer_present),
    ]

