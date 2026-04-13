from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ActuationResult:
    pump_on: bool
    normalized_command: float
    flow_rate: float
    water_applied: float


class PumpActuator:
    def __init__(self, max_flow_rate: float, on_threshold: float = 0.1) -> None:
        if max_flow_rate <= 0:
            raise ValueError("max_flow_rate must be > 0")
        if not (0.0 <= on_threshold <= 1.0):
            raise ValueError("on_threshold must be in [0, 1]")
        self.max_flow_rate = max_flow_rate
        self.on_threshold = on_threshold

    def apply(self, command: float, dt_hours: float) -> ActuationResult:
        if dt_hours <= 0:
            raise ValueError("dt_hours must be > 0")
        normalized_command = max(0.0, min(1.0, float(command)))
        pump_on = normalized_command >= self.on_threshold
        flow_rate = self.max_flow_rate * normalized_command if pump_on else 0.0
        water_applied = flow_rate * dt_hours
        return ActuationResult(
            pump_on=pump_on,
            normalized_command=normalized_command,
            flow_rate=flow_rate,
            water_applied=water_applied,
        )

