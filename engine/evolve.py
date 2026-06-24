from __future__ import annotations

import json
import random
from dataclasses import asdict
from pathlib import Path

from data.label import label_ads
from data.schema import load_ads

from .agents import default_swarm
from .config import FlywheelConfig, OBJECTIVE
from .diversity import n_eff_ratio, novelty_scores
from .evaluator import ExperimentScore, evaluate_experiments
from .experiments import Experiment, crossover, mutate
from .metaeval import run_metaeval
from .predict import metrics, temporal_split, train_and_predict


def initial_population(rng: random.Random, size: int) -> list[Experiment]:
    agents = default_swarm()
    per_agent = max(1, size // len(agents))
    population: list[Experiment] = []
    for agent in agents:
        population.extend(agent.propose(rng, per_agent))
    while len(population) < size:
        population.extend(rng.choice(agents).propose(rng, 1))
    return population[:size]


def run_evolution(config: FlywheelConfig | None = None) -> dict[str, object]:
    cfg = config or FlywheelConfig.from_env()
    rng = random.Random(cfg.seed)
    if not cfg.raw_path.exists():
        raise SystemExit(f"Missing sample data: {cfg.raw_path}. Run make fetch BRAND=\"{cfg.brand}\" MARKET=\"{cfg.market}\" or add the offline snapshot.")
    raw_payload = json.loads(cfg.raw_path.read_text(encoding="utf-8"))
    ads = load_ads(str(cfg.raw_path))
    labeled = label_ads(ads)
    if len({row.label for row in labeled}) < 2:
        raise SystemExit("Need both WINNER and LOSER labels after ambiguity drop.")

    population = initial_population(rng, cfg.experiments_per_cycle)
    cycles: list[dict[str, object]] = []
    history_rows: list[dict[str, object]] = []
    latest_scores: list[ExperimentScore] = []
    studied_payload = [row.to_dict() for row in sorted(labeled, key=lambda item: item.ad.started, reverse=True)[:18]]
    metaeval_payload = None
    accuracy_series: list[float] = []
    n_eff_series: list[float] = []

    for cycle in range(cfg.cycles):
        train, holdout = temporal_split(labeled, cycle, cfg.cycles)
        train_predictions = train_and_predict(train, train)
        holdout_predictions = train_and_predict(train, holdout)
        pred_metrics = metrics(holdout_predictions, len(train))
        metaeval = run_metaeval(train_predictions, holdout_predictions, cfg)
        metaeval_payload = asdict(metaeval)
        if not metaeval.passed:
            return _payload(cfg, labeled, cycles, studied_payload, [], metaeval_payload, valid=False, error="evaluator leaking", data_source=_data_source(raw_payload))

        diversity_n_eff, diversity_ratio, _ = n_eff_ratio(population, seed=cfg.seed + cycle)
        mutation_rate = cfg.high_mutation_rate if diversity_ratio < cfg.diversity_floor else cfg.mutation_rate
        scores = evaluate_experiments(population, train_predictions, holdout_predictions, cfg)
        ranked = _rank(scores, diversity_ratio < cfg.diversity_floor)
        latest_scores = [row for _, row in ranked]
        top = latest_scores[: cfg.experiments_per_cycle]
        accuracy_series.append(pred_metrics.accuracy)
        n_eff_series.append(diversity_ratio)
        cycle_payload = {
            "cycle": cycle,
            "metrics": asdict(pred_metrics),
            "n_eff": diversity_n_eff,
            "n_eff_ratio": diversity_ratio,
            "diversity_floor": cfg.diversity_floor,
            "mutation_rate": mutation_rate,
            "metaeval": metaeval_payload,
            "top_experiments": [_score_payload(row) for row in top],
        }
        cycles.append(cycle_payload)
        history_rows.append(
            {
                "cycle": cycle,
                "accuracy": pred_metrics.accuracy,
                "precision": pred_metrics.precision,
                "recall": pred_metrics.recall,
                "auc": pred_metrics.auc,
                "calibration": pred_metrics.calibration,
                "n_eff_ratio": diversity_ratio,
            "metaeval_fpr": metaeval.false_positive_rate,
            "metaeval_evaluated_nulls": metaeval.evaluated_null_count,
            "metaeval_fail_closed": metaeval.fail_closed_count,
            }
        )
        population = _breed(rng, ranked, cfg.experiments_per_cycle, mutation_rate)

    latest = _payload(cfg, labeled, cycles, studied_payload, [_score_payload(row) for row in latest_scores[: cfg.experiments_per_cycle]], metaeval_payload or {}, valid=True, data_source=_data_source(raw_payload))
    latest["history"] = history_rows
    latest["accuracy_series"] = accuracy_series
    latest["n_eff_series"] = n_eff_series
    latest["callout"] = {
        "model": "frozen creative-feature swarm",
        "example_copy": "England price boost tonight. Bet now with Fanatics Sportsbook.",
        "prediction": "winner" if (cycles[-1]["metrics"]["accuracy"] >= 0.5) else "loser",
        "honest_confidence": max(0.0, min(1.0, cycles[-1]["metrics"]["auc"])),
    }
    return latest


def _rank(scores: list[ExperimentScore], diversity_low: bool) -> list[tuple[float, ExperimentScore]]:
    nov = novelty_scores([row.experiment for row in scores])
    ranked = []
    for row in scores:
        novelty = nov.get(row.experiment.id, 0.0)
        fitness = row.honest_score * (1.0 + (0.35 if diversity_low else 0.12) * novelty) + 0.02 * row.p_real
        if not row.passed:
            fitness -= 0.01
        ranked.append((fitness, row))
    return sorted(ranked, key=lambda item: item[0], reverse=True)


def _breed(rng: random.Random, ranked: list[tuple[float, ExperimentScore]], size: int, mutation_rate: float) -> list[Experiment]:
    survivors = [row.experiment for _, row in ranked[: max(4, size // 3)]]
    children = survivors[: max(2, size // 6)]
    while len(children) < size:
        if len(survivors) >= 2:
            child = crossover(*rng.sample(survivors, 2), rng)
        else:
            child = survivors[0]
        children.append(mutate(child, rng, mutation_rate))
    return children[:size]


def _score_payload(row: ExperimentScore) -> dict[str, object]:
    return {
        **row.experiment.to_dict(),
        "naive_score": row.naive_score,
        "honest_score": row.honest_score,
        "p_real": row.p_real,
        "segment_n": row.segment_n,
        "passed": row.passed,
        "fail_reason": row.fail_reason,
    }


def _data_source(raw_payload: dict[str, object]) -> dict[str, object]:
    return {
        "synthetic": bool(raw_payload.get("synthetic", False)),
        "source": raw_payload.get("source") or raw_payload.get("backend") or "unknown",
        "backend": raw_payload.get("backend", "unknown"),
    }


def _payload(cfg: FlywheelConfig, labeled, cycles, studied, experiments, metaeval, *, valid: bool, error: str | None = None, data_source: dict[str, object] | None = None) -> dict[str, object]:
    latest_metrics = cycles[-1]["metrics"] if cycles else {"accuracy": 0, "precision": 0, "recall": 0, "auc": 0.5, "calibration": 0}
    return {
        "brand": cfg.brand,
        "market": cfg.market,
        "objective": OBJECTIVE,
        "valid": valid,
        "error": error,
        "seed": cfg.seed,
        "data_source": data_source or {"synthetic": False, "source": "unknown", "backend": "unknown"},
        "ads_studied": len(labeled),
        "headline": {
            "out_of_sample_hit_rate": latest_metrics["accuracy"],
            "precision": latest_metrics["precision"],
            "auc": latest_metrics["auc"],
            "calibration": latest_metrics["calibration"],
        },
        "studied_ads": studied,
        "todays_experiments": experiments,
        "cycles": cycles,
        "metaeval": metaeval,
        "architecture_notes": [
            "Diversity adapts the ATLAS Phase B inverse-Simpson N_eff/N breadth fix.",
            "Selection adapts ATLAS Darwinian breeding: honest score, novelty pressure, crossover, mutation, cull.",
            "Self-improvement means holdout accuracy on fresh real ads improving across cycles, not a score function climbing.",
        ],
    }


def write_results(path: Path | None = None, config: FlywheelConfig | None = None) -> Path:
    cfg = config or FlywheelConfig.from_env()
    payload = run_evolution(cfg)
    out = path or cfg.runs_dir / "latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    history = cfg.runs_dir / "history.json"
    history.write_text(json.dumps(payload.get("history", []), indent=2), encoding="utf-8")
    return out
