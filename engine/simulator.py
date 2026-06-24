from __future__ import annotations

import hashlib
import math
from typing import Any

import numpy as np
import pandas as pd

from .experiments import Experiment


HOST_REGIONS = {"US", "Canada", "Mexico"}


class GrowthSimulator:
    def __init__(self, seed: int, n_fans: int) -> None:
        self.seed = seed
        self.fans = self._make_fans(n_fans)

    def _make_fans(self, n: int) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        sports = rng.choice(["nfl", "mlb", "nba", "nhl", "soccer"], n, p=[0.25, 0.17, 0.20, 0.10, 0.28])
        regions = rng.choice(["US", "Canada", "Mexico", "UK", "EU", "LatAm", "Asia"], n, p=[0.46, 0.06, 0.07, 0.08, 0.14, 0.12, 0.07])
        engagement = rng.choice([1, 2, 3, 4, 5], n, p=[0.18, 0.24, 0.26, 0.20, 0.12])
        spend = np.maximum(0, rng.lognormal(mean=2.55 + engagement * 0.22, sigma=0.8, size=n) - 8)
        has_bet_prob = 0.05 + 0.035 * engagement + (sports != "soccer") * 0.03
        has_bet = rng.random(n) < has_bet_prob
        df = pd.DataFrame(
            {
                "fan_id": np.arange(n),
                "primary_sport": sports,
                "secondary_sports": rng.choice(["soccer", "nfl", "nba", "mlb", "nhl", "none"], n),
                "region": regions,
                "engagement_tier": engagement,
                "monthly_spend": spend.round(2),
                "has_bet": has_bet,
                "collectibles_active": rng.random(n) < (0.16 + 0.05 * engagement),
                "days_since_signup": rng.integers(1, 1800, n),
                "age_band": rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"], n, p=[0.18, 0.32, 0.24, 0.16, 0.10]),
                "device": rng.choice(["ios", "android", "web"], n, p=[0.45, 0.38, 0.17]),
            }
        )
        base = 0.004 + 0.0025 * df["engagement_tier"] + 0.00015 * np.sqrt(df["monthly_spend"])
        base += (df["primary_sport"].eq("soccer") & df["region"].isin(HOST_REGIONS)).astype(float) * 0.004
        base -= df["has_bet"].astype(float) * 0.006
        df["baseline_conversion"] = np.clip(base, 0.001, 0.07)
        return df

    def segment_mask(self, experiment: Experiment, fans: pd.DataFrame | None = None) -> np.ndarray:
        df = self.fans if fans is None else fans
        mask = np.ones(len(df), dtype=bool)
        for key, value in experiment.segment_filter.items():
            if value == "any" or value is None:
                continue
            if key == "min_engagement_tier":
                mask &= df["engagement_tier"].to_numpy() >= int(value)
            elif key in df.columns:
                mask &= df[key].to_numpy() == value
        return mask

    def true_lift(self, fans: pd.DataFrame, experiment: Experiment) -> np.ndarray:
        # Hidden ground truth. The evaluator never calls this except for demo audit fields.
        sport_soccer = fans["primary_sport"].eq("soccer").to_numpy()
        secondary_soccer = fans["secondary_sports"].eq("soccer").to_numpy()
        host = fans["region"].isin(HOST_REGIONS).to_numpy()
        latam_eu = fans["region"].isin(["LatAm", "EU", "UK"]).to_numpy()
        engaged = fans["engagement_tier"].to_numpy()
        never_bet = ~fans["has_bet"].to_numpy()
        collectibles = fans["collectibles_active"].to_numpy()
        amount = float(experiment.offer_params.get("amount", 20))
        amount_effect = min(amount, 60) / 60.0
        lift = np.zeros(len(fans), dtype=float)
        if experiment.offer_type == "world_cup_free_bet":
            lift += 0.006 + 0.032 * sport_soccer + 0.014 * secondary_soccer + 0.018 * host + 0.009 * latam_eu
            lift += 0.007 * np.maximum(0, engaged - 2) + 0.012 * never_bet + 0.010 * amount_effect
        elif experiment.offer_type == "odds_boost":
            lift += 0.004 + 0.018 * sport_soccer + 0.009 * host + 0.004 * np.maximum(0, engaged - 3)
        elif experiment.offer_type == "jersey_credit":
            lift += 0.003 + 0.011 * sport_soccer + 0.016 * collectibles + 0.004 * amount_effect
        elif experiment.offer_type == "collectibles_bundle":
            lift += 0.002 + 0.018 * collectibles + 0.004 * sport_soccer
        elif experiment.offer_type == "generic_cashback":
            lift += 0.002 + 0.003 * never_bet
        channel_mult = {"push": 1.10, "in_app": 1.18, "email": 0.92, "paid_social": 0.82, "affiliate": 0.70, "creator": 1.04}[experiment.channel]
        if experiment.channel in {"push", "in_app"}:
            channel_mult += 0.06 * (engaged >= 4)
        if experiment.channel == "creator":
            channel_mult += 0.10 * sport_soccer
        if experiment.offer_params.get("urgency") == "matchday":
            channel_mult += 0.08 * sport_soccer
        lift = lift * channel_mult
        lift -= fans["has_bet"].to_numpy() * 0.018
        return np.clip(lift, -0.01, 0.14)

    def expected_true_lift(self, experiment: Experiment, fans: pd.DataFrame | None = None) -> float:
        df = self.fans if fans is None else fans
        mask = self.segment_mask(experiment, df)
        if int(mask.sum()) == 0:
            return 0.0
        return float(np.mean(self.true_lift(df.loc[mask], experiment)))

    def split_indices(self, generation: int, discovery_n: int, holdout_n: int) -> tuple[np.ndarray, np.ndarray]:
        rng = np.random.default_rng(self.seed + generation * 9973)
        idx = rng.permutation(len(self.fans))
        return idx[:discovery_n], idx[discovery_n : discovery_n + holdout_n]

    def outcomes(self, experiment: Experiment, indices: np.ndarray, salt: str, treatment_fraction: float) -> pd.DataFrame:
        fans = self.fans.iloc[indices].copy()
        mask = self.segment_mask(experiment, fans)
        fans = fans.loc[mask].copy()
        if fans.empty:
            return pd.DataFrame(columns=["fan_id", "treated", "converted"])
        seed = int(hashlib.sha1(f"{self.seed}:{experiment.id}:{salt}".encode()).hexdigest()[:12], 16) % (2**32)
        rng = np.random.default_rng(seed)
        treated = rng.random(len(fans)) < treatment_fraction
        base = fans["baseline_conversion"].to_numpy()
        lift = self.true_lift(fans, experiment)
        p = np.clip(base + treated * lift, 0.0005, 0.45)
        converted = rng.random(len(fans)) < p
        return pd.DataFrame({"fan_id": fans["fan_id"].to_numpy(), "treated": treated, "converted": converted})

