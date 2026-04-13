from __future__ import annotations

from typing import Sequence

import pandas as pd

from sim.actuator import PumpActuator
from sim.config import SimulationConfig
from sim.controllers import ALL_CONTROLLER_NAMES, build_controller
from sim.disturbances import generate_disturbance_profile
from sim.plant import soil_moisture_step
from sim.sensor import SensorModel

DEFAULT_CONTROLLER_NAMES: tuple[str, ...] = ALL_CONTROLLER_NAMES


def _stable_controller_seed_offset(controller_name: str) -> int:
    for idx, known_name in enumerate(ALL_CONTROLLER_NAMES):
        if known_name == controller_name:
            return idx * 101
    return sum(ord(ch) for ch in controller_name) % 997


def run_controller_simulation(
    controller_name: str,
    cfg: SimulationConfig,
    disturbance_profile: pd.DataFrame,
    seed: int,
    sensor_sample_period_hours: float | None = None,
    controller_kwargs: dict[str, float] | None = None,
) -> pd.DataFrame:
    controller = build_controller(controller_name, **(controller_kwargs or {}))
    sensor = SensorModel(
        sample_period_hours=sensor_sample_period_hours or cfg.sensor_sample_period_hours,
        noise_std=cfg.sensor_noise_std,
        quantization_levels=cfg.sensor_quantization_levels,
        seed=seed + _stable_controller_seed_offset(controller_name),
    )
    actuator = PumpActuator(max_flow_rate=cfg.pump_max_flow, on_threshold=cfg.pump_on_threshold)

    moisture = max(0.0, min(cfg.saturation, cfg.initial_moisture))
    rows: list[dict[str, float | bool | str]] = []

    for weather in disturbance_profile.itertuples(index=False):
        measured = sensor.sample(true_moisture=moisture, hour=float(weather.hour))
        command = controller.compute(
            measured_moisture=measured,
            hour=int(round(weather.hour)),
            dt_hours=cfg.dt_hours,
        )
        actuation = actuator.apply(command=command, dt_hours=cfg.dt_hours)
        plant = soil_moisture_step(
            moisture=moisture,
            irrigation=actuation.flow_rate,
            rainfall=float(weather.rainfall),
            et0=float(weather.et0),
            temp_mean_c=float(weather.temp_mean_c),
            cfg=cfg,
        )
        moisture = plant.moisture

        rows.append(
            {
                "hour": float(weather.hour),
                "controller": controller_name,
                "moisture": moisture,
                "measured_moisture": measured,
                "irrigation_command": command,
                "pump_on": actuation.pump_on,
                "flow_rate": actuation.flow_rate,
                "water_applied": actuation.water_applied,
                "rainfall": float(weather.rainfall),
                "temp_mean_c": float(weather.temp_mean_c),
                "temp_min_c": float(weather.temp_min_c),
                "temp_max_c": float(weather.temp_max_c),
                "et0": float(weather.et0),
                "et_loss": plant.et_loss,
                "deep_percolation": plant.deep_percolation,
            }
        )

    return pd.DataFrame(rows)


def run_controller_comparison(
    controller_names: Sequence[str],
    cfg: SimulationConfig,
    seed: int,
    pid_params: dict[str, float] | None = None,
    sensor_sample_period_hours: float | None = None,
) -> pd.DataFrame:
    disturbance_profile = generate_disturbance_profile(cfg=cfg, seed=seed)

    frames = []
    for idx, controller_name in enumerate(controller_names):
        kwargs = pid_params if controller_name == "pid" and pid_params else None
        frame = run_controller_simulation(
            controller_name=controller_name,
            cfg=cfg,
            disturbance_profile=disturbance_profile,
            seed=seed + idx * 13,
            sensor_sample_period_hours=sensor_sample_period_hours,
            controller_kwargs=kwargs,
        )
        frames.append(frame)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def run_all_controllers(cfg: SimulationConfig, seed: int) -> pd.DataFrame:
    return run_controller_comparison(controller_names=DEFAULT_CONTROLLER_NAMES, cfg=cfg, seed=seed)
