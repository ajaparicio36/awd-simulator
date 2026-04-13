from __future__ import annotations

import pandas as pd

from sim.config import SimulationConfig
from sim.engine import run_controller_comparison
from sim.metrics import compute_performance_metrics
from sim.network import simulate_sensor_network


def pid_gain_study(
    cfg: SimulationConfig,
    seed: int,
    gain_sets: list[tuple[float, float, float]],
) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for idx, (kp, ki, kd) in enumerate(gain_sets):
        results = run_controller_comparison(
            controller_names=["pid", "timer"],
            cfg=cfg,
            seed=seed + idx,
            pid_params={"kp": kp, "ki": ki, "kd": kd, "setpoint": 0.6},
        )
        metrics = compute_performance_metrics(results=results, cfg=cfg, baseline_controller="timer")
        pid_row = metrics.loc[metrics["controller"] == "pid"].iloc[0]
        rows.append(
            {
                "kp": kp,
                "ki": ki,
                "kd": kd,
                "water_usage": float(pid_row["water_usage"]),
                "water_savings_pct": float(pid_row["water_savings_pct"]),
                "yield_proxy": float(pid_row["yield_proxy"]),
            }
        )
    return pd.DataFrame(rows)


def sampling_rate_study(
    cfg: SimulationConfig,
    seed: int,
    sample_rates: list[float],
    controller_name: str = "linear_awd",
) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    for idx, sample_rate in enumerate(sample_rates):
        results = run_controller_comparison(
            controller_names=[controller_name, "timer"],
            cfg=cfg,
            seed=seed + (idx * 5),
            sensor_sample_period_hours=float(sample_rate),
        )
        metrics = compute_performance_metrics(results=results, cfg=cfg, baseline_controller="timer")
        cand = metrics.loc[metrics["controller"] == controller_name].iloc[0]
        rows.append(
            {
                "sample_period_hours": float(sample_rate),
                "water_usage": float(cand["water_usage"]),
                "water_savings_pct": float(cand["water_savings_pct"]),
                "yield_proxy": float(cand["yield_proxy"]),
            }
        )
    return pd.DataFrame(rows)


def network_node_scaling_study(
    node_counts: list[int],
    hours: int,
    seed: int,
    mac_protocol: str,
    path_loss_model: str = "free_space",
) -> pd.DataFrame:
    rows: list[dict[str, float | int]] = []
    for idx, node_count in enumerate(node_counts):
        network = simulate_sensor_network(
            node_count=node_count,
            hours=hours,
            seed=seed + idx,
            mac_protocol=mac_protocol,
            path_loss_model=path_loss_model,
        )
        perf = network["performance"]
        battery = network["battery"]
        rows.append(
            {
                "node_count": int(node_count),
                "delivery_rate": float(perf["delivery_rate"].mean()),
                "mean_battery_pct": float(battery.groupby("node_id")["battery_pct"].last().mean()),
            }
        )
    return pd.DataFrame(rows)

