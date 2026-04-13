from __future__ import annotations

import math

import numpy as np
import pandas as pd

from sim.config import SimulationConfig


def hargreaves_et(temp_min_c: float, temp_max_c: float, temp_mean_c: float, et_coeff: float) -> float:
    temp_range = max(temp_max_c - temp_min_c, 0.0)
    et = et_coeff * math.sqrt(temp_range) * max(temp_mean_c + 17.8, 0.0)
    return max(et, 0.0)


def generate_disturbance_profile(cfg: SimulationConfig, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float]] = []

    for step in range(cfg.total_steps):
        hour = step * cfg.dt_hours
        day_phase = (hour % 24.0) / 24.0
        seasonal_phase = hour / max(cfg.sim_days * 24.0, 1.0)

        seasonal_term = math.sin(2.0 * math.pi * seasonal_phase)
        diurnal_term = math.sin(2.0 * math.pi * (day_phase - 0.25))

        temp_mean_c = 28.0 + 3.0 * seasonal_term + 4.0 * diurnal_term
        temp_span = 8.0 + 1.5 * math.cos(2.0 * math.pi * day_phase)
        temp_min_c = temp_mean_c - (temp_span / 2.0)
        temp_max_c = temp_mean_c + (temp_span / 2.0)

        rain_prob = 0.08 + 0.08 * max(0.0, math.sin(2.0 * math.pi * seasonal_phase + 1.2))
        rainfall = float(rng.gamma(shape=1.8, scale=0.7)) if rng.random() < rain_prob else 0.0

        et0 = hargreaves_et(
            temp_min_c=temp_min_c,
            temp_max_c=temp_max_c,
            temp_mean_c=temp_mean_c,
            et_coeff=cfg.et_coeff,
        )

        rows.append(
            {
                "hour": hour,
                "temp_min_c": temp_min_c,
                "temp_max_c": temp_max_c,
                "temp_mean_c": temp_mean_c,
                "rainfall": rainfall,
                "et0": et0,
            }
        )

    return pd.DataFrame(rows)

