from __future__ import annotations

from dataclasses import dataclass


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


class BaseController:
    name: str = "base"

    def reset(self) -> None:
        return

    def compute(self, measured_moisture: float, hour: int, dt_hours: float) -> float:
        raise NotImplementedError


@dataclass(slots=True)
class LinearAWDController(BaseController):
    dry_reference: float = 0.35
    target: float = 0.62
    name: str = "linear_awd"

    def compute(self, measured_moisture: float, hour: int, dt_hours: float) -> float:
        if measured_moisture >= self.target:
            return 0.0
        span = max(self.target - self.dry_reference, 1e-6)
        return _clamp01((self.target - measured_moisture) / span)


@dataclass(slots=True)
class AggressiveAWDController(BaseController):
    dry_reference: float = 0.40
    target: float = 0.68
    name: str = "aggressive_awd"

    def compute(self, measured_moisture: float, hour: int, dt_hours: float) -> float:
        if measured_moisture >= self.target:
            return 0.0
        span = max(self.target - self.dry_reference, 1e-6)
        return _clamp01((self.target - measured_moisture) / span)


@dataclass(slots=True)
class ConservativeAWDController(BaseController):
    dry_reference: float = 0.30
    target: float = 0.58
    name: str = "conservative_awd"

    def compute(self, measured_moisture: float, hour: int, dt_hours: float) -> float:
        if measured_moisture >= self.target:
            return 0.0
        span = max(self.target - self.dry_reference, 1e-6)
        return _clamp01((self.target - measured_moisture) / span)


class StepAWDController(BaseController):
    name = "step_awd"

    def compute(self, measured_moisture: float, hour: int, dt_hours: float) -> float:
        if measured_moisture < 0.35:
            return 1.0
        if measured_moisture < 0.45:
            return 0.75
        if measured_moisture < 0.55:
            return 0.50
        if measured_moisture < 0.62:
            return 0.25
        return 0.0


@dataclass(slots=True)
class PIDController(BaseController):
    kp: float = 2.0
    ki: float = 0.08
    kd: float = 0.2
    setpoint: float = 0.6
    integral_limit: float = 5.0
    name: str = "pid"

    _integral: float = 0.0
    _prev_error: float = 0.0

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = 0.0

    def compute(self, measured_moisture: float, hour: int, dt_hours: float) -> float:
        dt = max(dt_hours, 1e-6)
        error = self.setpoint - measured_moisture
        self._integral = max(
            -self.integral_limit,
            min(self.integral_limit, self._integral + error * dt),
        )
        derivative = (error - self._prev_error) / dt
        self._prev_error = error

        raw = (self.kp * error) + (self.ki * self._integral) + (self.kd * derivative)
        output = _clamp01(raw)
        if output != raw:
            self._integral = max(
                -self.integral_limit,
                min(self.integral_limit, self._integral - 0.5 * error * dt),
            )
        return output


@dataclass(slots=True)
class BangBangHysteresisController(BaseController):
    lower: float = 0.40
    upper: float = 0.62
    command_on: float = 1.0
    name: str = "bang_bang"

    _is_on: bool = False

    def reset(self) -> None:
        self._is_on = False

    def compute(self, measured_moisture: float, hour: int, dt_hours: float) -> float:
        if measured_moisture <= self.lower:
            self._is_on = True
        elif measured_moisture >= self.upper:
            self._is_on = False
        return self.command_on if self._is_on else 0.0


@dataclass(slots=True)
class TimerController(BaseController):
    period_hours: int = 12
    on_duration_hours: int = 2
    command_level: float = 0.8
    name: str = "timer"

    def compute(self, measured_moisture: float, hour: int, dt_hours: float) -> float:
        if self.period_hours <= 0:
            return 0.0
        phase = int(hour % self.period_hours)
        return self.command_level if phase < self.on_duration_hours else 0.0


ALL_CONTROLLER_NAMES = (
    "linear_awd",
    "step_awd",
    "aggressive_awd",
    "conservative_awd",
    "pid",
    "bang_bang",
    "timer",
)


def build_controller(name: str, **kwargs: float) -> BaseController:
    normalized = name.strip().lower()
    if normalized == "linear_awd":
        return LinearAWDController(**kwargs)
    if normalized == "step_awd":
        return StepAWDController()
    if normalized == "aggressive_awd":
        return AggressiveAWDController(**kwargs)
    if normalized == "conservative_awd":
        return ConservativeAWDController(**kwargs)
    if normalized == "pid":
        return PIDController(**kwargs)
    if normalized == "bang_bang":
        return BangBangHysteresisController(**kwargs)
    if normalized == "timer":
        return TimerController(**kwargs)
    raise ValueError(f"Unknown controller: {name}")

