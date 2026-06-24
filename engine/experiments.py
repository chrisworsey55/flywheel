from __future__ import annotations

import hashlib
import random
from dataclasses import asdict, dataclass, field
from typing import Any


OFFER_TYPES = ("free_bet", "odds_boost", "bet_insurance", "deposit_match", "none")
FRAMINGS = ("national_team", "world_cup", "generic", "lapsed_winback")


@dataclass(frozen=True)
class Experiment:
    hypothesis: str
    predicts: str
    feature_rule: dict[str, Any]
    segment: str
    confidence: float
    agent: str = "unknown"
    lineage: tuple[str, ...] = field(default_factory=tuple)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            digest = hashlib.sha1(repr((self.hypothesis, self.predicts, self.feature_rule, self.segment, self.lineage)).encode()).hexdigest()[:12]
            object.__setattr__(self, "id", f"exp_{digest}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def random_rule(rng: random.Random, *, prior: str = "mixed") -> dict[str, Any]:
    rule: dict[str, Any] = {}
    if prior == "offer" or rng.random() < 0.65:
        rule["offer_type"] = rng.choice(OFFER_TYPES)
    if prior == "framing" or rng.random() < 0.58:
        rule["framing"] = rng.choice(FRAMINGS)
    if prior == "urgency" or rng.random() < 0.35:
        rule["min_urgency"] = round(rng.choice([0.0, 0.2, 0.4, 0.6]), 2)
    if rng.random() < 0.28:
        rule["numeric_offer_present"] = rng.choice([True, False])
    if rng.random() < 0.22:
        rule["has_emoji"] = rng.choice([True, False])
    return rule or {"framing": "generic"}


def make_experiment(rng: random.Random, *, agent: str, rule: dict[str, Any] | None = None, prior: str = "mixed") -> Experiment:
    feature_rule = dict(rule or random_rule(rng, prior=prior))
    offer = str(feature_rule.get("offer_type", "creative")).replace("_", " ")
    framing = str(feature_rule.get("framing", "broad")).replace("_", " ")
    return Experiment(
        hypothesis=f"{framing} {offer} creative will be kept alive more often than baseline ads.",
        predicts="winner",
        feature_rule=feature_rule,
        segment=rng.choice(["all studied ads", "recent UK sportsbook ads", "football-intent creatives", "offer-led creatives"]),
        confidence=round(rng.uniform(0.52, 0.78), 3),
        agent=agent,
    )


def mutate(experiment: Experiment, rng: random.Random, mutation_rate: float) -> Experiment:
    rule = dict(experiment.feature_rule)
    if rng.random() < mutation_rate:
        rule["offer_type"] = rng.choice(OFFER_TYPES)
    if rng.random() < mutation_rate:
        rule["framing"] = rng.choice(FRAMINGS)
    if rng.random() < mutation_rate:
        rule["min_urgency"] = round(max(0.0, min(1.0, float(rule.get("min_urgency", 0.0)) + rng.choice([-0.2, 0.2]))), 2)
    if rng.random() < mutation_rate:
        rule["numeric_offer_present"] = not bool(rule.get("numeric_offer_present", False))
    return Experiment(
        hypothesis=f"Mutation of {experiment.id}: {rule} should predict ads kept alive.",
        predicts=experiment.predicts,
        feature_rule=rule,
        segment=experiment.segment,
        confidence=round(max(0.5, min(0.92, experiment.confidence + rng.uniform(-0.04, 0.05))), 3),
        agent=f"{experiment.agent}+mut",
        lineage=experiment.lineage + (experiment.id,),
    )


def crossover(a: Experiment, b: Experiment, rng: random.Random) -> Experiment:
    rule = {key: rng.choice([a.feature_rule.get(key), b.feature_rule.get(key)]) for key in set(a.feature_rule) | set(b.feature_rule)}
    rule = {key: value for key, value in rule.items() if value is not None}
    return Experiment(
        hypothesis=f"Crossover of {a.id} and {b.id}: combine held-out predictive creative traits.",
        predicts="winner",
        feature_rule=rule or random_rule(rng),
        segment=rng.choice([a.segment, b.segment]),
        confidence=round(max(a.confidence, b.confidence) * rng.uniform(0.96, 1.03), 3),
        agent="crossover",
        lineage=(a.id, b.id),
    )

