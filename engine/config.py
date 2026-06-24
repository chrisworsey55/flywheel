from __future__ import annotations

import os
import random
from dataclasses import dataclass
from pathlib import Path


OBJECTIVE = "Predict which real ads a real advertiser keeps alive versus kills, then breed the hypotheses that best predicted fresh holdout reality."


@dataclass(frozen=True)
class FlywheelConfig:
    seed: int = 42
    brand: str = "Fanatics Sportsbook"
    market: str = "GB"
    cycles: int = 6
    experiments_per_cycle: int = 25
    min_holdout_n: int = 4
    max_false_positive_rate: float = 0.05
    metaeval_nulls: int = 220
    mutation_rate: float = 0.22
    high_mutation_rate: float = 0.38
    diversity_floor: float = 0.60
    raw_dir: Path = Path(__file__).resolve().parents[1] / "data" / "raw"
    runs_dir: Path = Path(__file__).resolve().parents[1] / "runs"

    @classmethod
    def from_env(cls) -> "FlywheelConfig":
        seed_raw = os.environ.get("SEED", "42")
        seed = random.SystemRandom().randint(1, 2_147_483_647) if seed_raw.lower() == "random" else int(seed_raw)
        return cls(
            seed=seed,
            brand=os.environ.get("BRAND", cls.brand),
            market=os.environ.get("MARKET", cls.market),
            cycles=int(os.environ.get("CYCLES", cls.cycles)),
        )

    @property
    def raw_path(self) -> Path:
        slug = self.brand.lower().replace(" ", "_").replace("/", "_")
        return self.raw_dir / f"{slug}_{self.market.lower()}.json"
