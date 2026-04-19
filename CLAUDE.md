# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Environment (Python 3.12):

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the Streamlit UI:

```bash
streamlit run app.py
```

Tests:

```bash
pytest -q                                   # full suite
pytest tests/test_engine_metrics.py -q      # single file
pytest tests/test_controllers.py::<name> -q # single test
```

`pytest.ini` sets `pythonpath = .` so imports like `from sim.engine import ...` resolve without installing the package.

Docker (matches Railway deploy):

```bash
docker build -t smart-paddy .
docker run --rm -e PORT=8501 -p 8501:8501 smart-paddy
```

The Dockerfile only copies `app.py` and `sim/`; anything new that the Streamlit app imports at runtime must be added to the `COPY` lines or the image will break even though tests pass locally.

## Architecture

The codebase is a single Streamlit front-end (`app.py`) over a pure-Python simulation library (`sim/`). The UI owns no simulation logic — it constructs a `SimulationConfig` from sidebar widgets, calls into `sim/`, and renders the returned DataFrames with Plotly. All simulation code is deterministic given `(cfg, seed)`; keep it that way.

### Simulation pipeline

The per-step loop lives in `sim/engine.py::run_controller_simulation` and composes five independent modules in order:

1. `disturbances.generate_disturbance_profile(cfg, seed)` — produces the full weather time series (rainfall, ET0, temperatures) up-front, once per comparison run, so every controller sees identical weather.
2. `sensor.SensorModel.sample` — applies sample-and-hold at `sensor_sample_period_hours`, Gaussian noise, and quantization to the true moisture.
3. `controllers.BaseController.compute` — returns a command in `[0, 1]`.
4. `actuator.PumpActuator.apply` — converts command to `flow_rate` / `pump_on` / `water_applied`, gated by `pump_on_threshold` and `pump_max_flow`.
5. `plant.soil_moisture_step` — first-order moisture dynamics: `Δm = dt * (irrigation_gain·u + rain_gain·r − ET − percolation)` with ET scaled by temperature and over-capacity moisture, and deep percolation only above field capacity.

`run_controller_comparison` runs this loop once per controller against the shared disturbance profile and concatenates the per-step rows into one tidy long-format DataFrame keyed by `controller` and `hour`. Downstream code (`metrics.compute_performance_metrics`, all plotting in `app.py`) relies on that schema — adding new per-step outputs means updating both the row dict in `engine.py` and any consumers.

### Determinism and seeds

Seeds are layered, not global. `run_controller_comparison` offsets `seed` per controller (`seed + idx * 13`); inside each run the sensor gets a further stable offset from `_stable_controller_seed_offset(controller_name)` so adding/removing/reordering controllers in `ALL_CONTROLLER_NAMES` shifts sensor noise streams. Parametric studies in `sim/parametric.py` offset again (`seed + idx * 5`, `seed + 100`, etc.). If you touch seed arithmetic, expect regression-test deltas.

### Controllers

`controllers.ALL_CONTROLLER_NAMES` is the canonical registry and the default ordering used by the UI and by `run_all_controllers`. `build_controller(name, **kwargs)` is the only constructor entry point; `**kwargs` only flows through for PID (and the AWD variants that take `dry_reference` / `target`) — see the `pid_params` special-case in `engine.run_controller_comparison`. `timer` is the baseline for `water_savings_pct`; renaming or removing it will silently zero out savings.

### Metrics and parametric studies

`metrics.compute_performance_metrics` expects columns `water_applied`, `moisture`, `pump_on` and uses `cfg.dt_hours` + `cfg.stress_threshold` to integrate stress and violation hours. The `yield_proxy` is `exp(-sensitivity · stress_integral)` — a monotone transform, not a calibrated yield model. `sim/parametric.py` re-runs the full comparison per study point; these are the slow paths in the UI.

### Network model

`sim/network.py` is independent of the irrigation loop — it simulates a star topology around a gateway at the field center, computes SNR from path loss (`free_space` or `log_distance` at 2.4 GHz, 8 dBm TX, −95 dBm noise floor), converts SNR to PER via a logistic, and applies a MAC efficiency factor (`csma_ca` degrades with active-node count; `tdma` adds scheduling overhead). Battery drains per-hour from a fixed TX cost with a penalty on failed transmissions. Returns three DataFrames (`topology`, `battery`, `performance`) — the UI expects all three.

### Adding features

- New controller → add class in `sim/controllers.py`, register in `ALL_CONTROLLER_NAMES`, extend `build_controller`, cover in `tests/test_controllers.py`. The UI picks it up automatically via `ALL_CONTROLLER_NAMES`.
- New per-step output → append to the row dict in `engine.run_controller_simulation` and update metrics/plots that consume it.
- New `SimulationConfig` field → add to the dataclass, extend `validate()`, and plumb through the sidebar in `app.py` if user-facing.
