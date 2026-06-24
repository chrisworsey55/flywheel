from __future__ import annotations

import json

from .config import FlywheelConfig
from .evolve import write_results


def main() -> None:
    cfg = FlywheelConfig.from_env()
    path = write_results(config=cfg)
    print(json.dumps({"latest": str(path), "history": str(cfg.runs_dir / "history.json"), "seed": cfg.seed}, indent=2))


if __name__ == "__main__":
    main()

