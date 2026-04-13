from __future__ import annotations

import math

import numpy as np
import pandas as pd

from sim.config import SimulationConfig


def water_savings_percent(baseline_volume: float, candidate_volume: float) -> float:
    baseline = float(baseline_volume)
    candidate = float(candidate_volume)
    if baseline <= 0:
        return 0.0
    return ((baseline - candidate) / baseline) * 100.0


def yield_proxy_from_stress(stress_integral: float, sensitivity: float) -> float:
    stress = max(0.0, float(stress_integral))
    return float(math.exp(-max(0.0, sensitivity) * stress))


def compute_performance_metrics(
    results: pd.DataFrame,
    cfg: SimulationConfig,
    baseline_controller: str = "timer",
) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame(
            columns=[
                "controller",
                "water_usage",
                "water_savings_pct",
                "moisture_stress",
                "violation_hours",
                "yield_proxy",
                "pump_switches",
            ]
        )

    grouped = results.groupby("controller", sort=False)
    usage_by_controller = {
        name: float(group["water_applied"].sum()) for name, group in grouped
    }

    baseline_volume = usage_by_controller.get(
        baseline_controller,
        float(np.max(list(usage_by_controller.values()))),
    )

    rows = []
    for controller_name, group in grouped:
        moisture = group["moisture"].to_numpy(dtype=float)
        stress = float(np.maximum(0.0, cfg.stress_threshold - moisture).sum() * cfg.dt_hours)
        violations = float((group["moisture"] < cfg.stress_threshold).sum() * cfg.dt_hours)
        pump_switches = int(group["pump_on"].astype(int).diff().abs().fillna(0).sum())

        usage = usage_by_controller[controller_name]
        savings = 0.0 if controller_name == baseline_controller else water_savings_percent(baseline_volume, usage)

        rows.append(
            {
                "controller": controller_name,
                "water_usage": usage,
                "water_savings_pct": savings,
                "moisture_stress": stress,
                "violation_hours": violations,
                "yield_proxy": yield_proxy_from_stress(stress, cfg.yield_stress_sensitivity),
                "pump_switches": pump_switches,
            }
        )

    return pd.DataFrame(rows)

