from __future__ import annotations

from dataclasses import dataclass

from sim.config import SimulationConfig


@dataclass(slots=True)
class PlantStepResult:
    moisture: float
    et_loss: float
    deep_percolation: float
    delta_moisture: float


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def soil_moisture_step(
    moisture: float,
    irrigation: float,
    rainfall: float,
    et0: float,
    temp_mean_c: float,
    cfg: SimulationConfig,
) -> PlantStepResult:
    moisture = _clamp(moisture, 0.0, cfg.saturation)
    irrigation = max(0.0, irrigation)
    rainfall = max(0.0, rainfall)

    temperature_factor = 1.0 + 0.01 * max(temp_mean_c - 25.0, 0.0)
    sat_span = max(cfg.saturation - cfg.field_capacity, 1e-9)
    moisture_factor = 1.0 + cfg.et_moisture_scale * max(moisture - cfg.field_capacity, 0.0) / sat_span
    et_loss = max(0.0, et0 * temperature_factor * moisture_factor)

    deep_percolation = cfg.percolation_coeff * max(moisture - cfg.field_capacity, 0.0)

    delta = cfg.dt_hours * (
        (cfg.irrigation_gain * irrigation)
        + (cfg.rain_gain * rainfall)
        - et_loss
        - deep_percolation
    )
    next_moisture = _clamp(moisture + delta, 0.0, cfg.saturation)

    return PlantStepResult(
        moisture=next_moisture,
        et_loss=et_loss,
        deep_percolation=deep_percolation,
        delta_moisture=delta,
    )

