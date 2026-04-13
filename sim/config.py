from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SimulationConfig:
    sim_days: int = 120
    dt_hours: float = 1.0
    seed: int = 7

    saturation: float = 1.0
    field_capacity: float = 0.7
    wilting_point: float = 0.3
    stress_threshold: float = 0.42
    initial_moisture: float = 0.62

    irrigation_gain: float = 0.012
    rain_gain: float = 0.008
    percolation_coeff: float = 0.03
    et_coeff: float = 0.00023
    et_moisture_scale: float = 0.25

    sensor_sample_period_hours: float = 2.0
    sensor_noise_std: float = 0.01
    sensor_quantization_levels: int = 256

    pump_max_flow: float = 12.0
    pump_on_threshold: float = 0.1

    yield_stress_sensitivity: float = 0.4

    grid_rows: int = 10
    grid_cols: int = 10

    def __post_init__(self) -> None:
        self.validate()

    @property
    def total_steps(self) -> int:
        return max(1, int(round((self.sim_days * 24.0) / self.dt_hours)))

    def validate(self) -> None:
        if self.sim_days <= 0:
            raise ValueError("sim_days must be > 0")
        if self.dt_hours <= 0:
            raise ValueError("dt_hours must be > 0")
        if not (0.0 < self.field_capacity <= self.saturation <= 1.0):
            raise ValueError("field_capacity and saturation must satisfy 0 < field_capacity <= saturation <= 1")
        if not (0.0 <= self.wilting_point < self.field_capacity):
            raise ValueError("wilting_point must satisfy 0 <= wilting_point < field_capacity")
        if not (0.0 <= self.initial_moisture <= 1.0):
            raise ValueError("initial_moisture must be in [0, 1]")
        if not (self.wilting_point <= self.stress_threshold <= self.saturation):
            raise ValueError("stress_threshold must be in [wilting_point, saturation]")
        if self.irrigation_gain <= 0 or self.rain_gain <= 0:
            raise ValueError("irrigation_gain and rain_gain must be > 0")
        if self.percolation_coeff < 0:
            raise ValueError("percolation_coeff must be >= 0")
        if self.et_coeff <= 0:
            raise ValueError("et_coeff must be > 0")
        if self.sensor_sample_period_hours <= 0:
            raise ValueError("sensor_sample_period_hours must be > 0")
        if self.sensor_noise_std < 0:
            raise ValueError("sensor_noise_std must be >= 0")
        if self.sensor_quantization_levels < 2:
            raise ValueError("sensor_quantization_levels must be >= 2")
        if self.pump_max_flow <= 0:
            raise ValueError("pump_max_flow must be > 0")
        if not (0.0 <= self.pump_on_threshold <= 1.0):
            raise ValueError("pump_on_threshold must be in [0, 1]")
        if self.yield_stress_sensitivity <= 0:
            raise ValueError("yield_stress_sensitivity must be > 0")
        if self.grid_rows <= 0 or self.grid_cols <= 0:
            raise ValueError("grid_rows and grid_cols must be > 0")
