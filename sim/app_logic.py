from __future__ import annotations

import numpy as np


def awd_guidance(current_moisture: float, low_threshold: float = 0.42, high_threshold: float = 0.7) -> dict[str, object]:
    moisture = max(0.0, min(1.0, float(current_moisture)))

    if moisture < low_threshold:
        phase = "Irrigate"
        recommendation = "Moisture is below AWD lower threshold. Start irrigation."
    elif moisture > high_threshold:
        phase = "Saturated"
        recommendation = "Field is above saturation band. Stop pumping and allow drying."
    else:
        phase = "Drying"
        recommendation = "Within AWD band. Monitor and hold unless rapid drying continues."

    return {
        "phase": phase,
        "recommendation": recommendation,
        "below_low": moisture < low_threshold,
        "above_high": moisture > high_threshold,
        "low_threshold": low_threshold,
        "high_threshold": high_threshold,
        "moisture": moisture,
    }


def moisture_grid(base_moisture: float, rows: int, cols: int, seed: int) -> np.ndarray:
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be > 0")

    rng = np.random.default_rng(seed)
    x = np.linspace(0.0, 1.0, cols)
    y = np.linspace(0.0, 1.0, rows)
    xx, yy = np.meshgrid(x, y)

    spatial_pattern = 0.03 * np.sin(2 * np.pi * xx) + 0.02 * np.cos(2 * np.pi * yy)
    noise = rng.normal(0.0, 0.01, size=(rows, cols))
    grid = np.clip(float(base_moisture) + spatial_pattern + noise, 0.0, 1.0)
    return grid

