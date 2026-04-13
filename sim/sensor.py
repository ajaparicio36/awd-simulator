from __future__ import annotations

import numpy as np


class SensorModel:
    def __init__(
        self,
        sample_period_hours: float,
        noise_std: float,
        quantization_levels: int,
        seed: int,
    ) -> None:
        if sample_period_hours <= 0:
            raise ValueError("sample_period_hours must be > 0")
        if noise_std < 0:
            raise ValueError("noise_std must be >= 0")
        if quantization_levels < 2:
            raise ValueError("quantization_levels must be >= 2")

        self.sample_period_hours = sample_period_hours
        self.noise_std = noise_std
        self.quantization_levels = quantization_levels
        self.rng = np.random.default_rng(seed)

        self._last_sample_hour: float | None = None
        self._held_value: float = 0.0

    def sample(self, true_moisture: float, hour: float) -> float:
        hour = float(hour)
        if self._last_sample_hour is not None:
            elapsed = hour - self._last_sample_hour
            if elapsed < (self.sample_period_hours - 1e-12):
                return self._held_value

        noisy = float(true_moisture) + float(self.rng.normal(0.0, self.noise_std))
        clipped = max(0.0, min(1.0, noisy))

        step = 1.0 / (self.quantization_levels - 1)
        quantized = round(clipped / step) * step
        quantized = max(0.0, min(1.0, quantized))

        self._last_sample_hour = hour
        self._held_value = quantized
        return quantized

