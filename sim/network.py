from __future__ import annotations

import math

import numpy as np
import pandas as pd


def path_loss_db(
    distance_m: float,
    freq_hz: float = 2.4e9,
    model: str = "free_space",
    reference_distance_m: float = 1.0,
    path_loss_exponent: float = 2.7,
) -> float:
    d_m = max(float(distance_m), 1e-3)
    f_mhz = max(float(freq_hz), 1.0) / 1e6

    if model == "free_space":
        return 32.44 + (20.0 * math.log10(d_m / 1000.0)) + (20.0 * math.log10(f_mhz))

    if model == "log_distance":
        d0 = max(float(reference_distance_m), 1e-3)
        pl_d0 = 32.44 + (20.0 * math.log10(d0 / 1000.0)) + (20.0 * math.log10(f_mhz))
        return pl_d0 + (10.0 * path_loss_exponent * math.log10(d_m / d0))

    raise ValueError(f"Unsupported path loss model: {model}")


def packet_error_rate_from_snr(snr_db: float, required_margin_db: float = 10.0) -> float:
    margin = float(snr_db) - float(required_margin_db)
    per = 1.0 / (1.0 + math.exp(margin / 2.0))
    return max(0.0, min(1.0, per))


def simulate_sensor_network(
    node_count: int,
    hours: int,
    seed: int,
    mac_protocol: str = "csma_ca",
    path_loss_model: str = "free_space",
    field_size_m: float = 100.0,
    tx_power_dbm: float = 8.0,
    noise_floor_dbm: float = -95.0,
) -> dict[str, pd.DataFrame]:
    if node_count <= 0:
        raise ValueError("node_count must be > 0")
    if hours <= 0:
        raise ValueError("hours must be > 0")
    if mac_protocol not in {"csma_ca", "tdma"}:
        raise ValueError("mac_protocol must be 'csma_ca' or 'tdma'")

    rng = np.random.default_rng(seed)
    gateway_x = field_size_m / 2.0
    gateway_y = field_size_m / 2.0

    node_x = rng.uniform(0.0, field_size_m, size=node_count)
    node_y = rng.uniform(0.0, field_size_m, size=node_count)

    topology_rows: list[dict[str, float]] = []
    for node_id in range(node_count):
        dx = node_x[node_id] - gateway_x
        dy = node_y[node_id] - gateway_y
        distance = float(math.hypot(dx, dy)) + 1.0
        pl = path_loss_db(distance_m=distance, model=path_loss_model)
        snr = tx_power_dbm - pl - noise_floor_dbm
        topology_rows.append(
            {
                "node_id": node_id,
                "x_m": float(node_x[node_id]),
                "y_m": float(node_y[node_id]),
                "distance_m": distance,
                "path_loss_db": pl,
                "snr_db": snr,
            }
        )

    topology_df = pd.DataFrame(topology_rows)

    battery = np.full(shape=node_count, fill_value=100.0, dtype=float)
    battery_rows: list[dict[str, float | int]] = []
    performance_rows: list[dict[str, float | str | int]] = []

    for hour in range(hours):
        active_nodes = battery > 0.0
        active_count = int(active_nodes.sum())

        if mac_protocol == "csma_ca":
            collision_penalty = min(0.7, max(0.0, 0.03 * (active_count - 1)))
            mac_efficiency = 1.0 - collision_penalty
            tx_cost = 0.32
        else:
            scheduling_overhead = min(0.25, 0.004 * active_count)
            mac_efficiency = 0.98 - scheduling_overhead
            tx_cost = 0.24

        successes = 0
        attempts = 0
        snr_samples: list[float] = []
        per_samples: list[float] = []

        for node_id in range(node_count):
            if battery[node_id] <= 0.0:
                battery_rows.append({"hour": hour, "node_id": node_id, "battery_pct": 0.0})
                continue

            attempts += 1
            topo_row = topology_df.iloc[node_id]
            snr = float(topo_row["snr_db"]) + float(rng.normal(0.0, 1.0))
            per = packet_error_rate_from_snr(snr_db=snr)
            success_prob = max(0.0, min(1.0, (1.0 - per) * mac_efficiency))
            success = rng.random() < success_prob

            if success:
                successes += 1

            snr_samples.append(snr)
            per_samples.append(per)

            energy = 0.03 + tx_cost * (1.0 if success else 1.15)
            battery[node_id] = max(0.0, battery[node_id] - energy)

            battery_rows.append(
                {
                    "hour": hour,
                    "node_id": node_id,
                    "battery_pct": float(battery[node_id]),
                }
            )

        delivery_rate = (successes / attempts) if attempts else 0.0
        performance_rows.append(
            {
                "hour": hour,
                "mac_protocol": mac_protocol,
                "node_count": node_count,
                "delivery_rate": delivery_rate,
                "avg_snr_db": float(np.mean(snr_samples)) if snr_samples else float("nan"),
                "avg_per": float(np.mean(per_samples)) if per_samples else float("nan"),
            }
        )

    return {
        "topology": topology_df,
        "battery": pd.DataFrame(battery_rows),
        "performance": pd.DataFrame(performance_rows),
    }

