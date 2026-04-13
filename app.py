from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from sim.app_logic import awd_guidance, moisture_grid
from sim.config import SimulationConfig
from sim.controllers import ALL_CONTROLLER_NAMES
from sim.engine import run_controller_comparison
from sim.metrics import compute_performance_metrics
from sim.network import simulate_sensor_network
from sim.parametric import network_node_scaling_study, pid_gain_study, sampling_rate_study

st.set_page_config(page_title="Smart Paddy AWD Simulator", layout="wide")
st.title("Smart Paddy: Irrigation Control Simulation")
st.caption("Feedback-control comparison of AWD strategies, PID, bang-bang, and timer baseline.")

with st.sidebar:
    st.header("Simulation inputs")
    seed = int(st.number_input("Random seed", min_value=0, max_value=999_999, value=7, step=1))
    sim_days = int(st.slider("Simulation horizon (days)", min_value=30, max_value=180, value=120))
    dt_hours = float(st.select_slider("Time step (hours)", options=[0.5, 1.0, 2.0], value=1.0))

    initial_moisture = float(st.slider("Initial soil moisture", min_value=0.0, max_value=1.0, value=0.62, step=0.01))
    field_capacity = float(st.slider("Field capacity threshold", min_value=0.45, max_value=0.9, value=0.7, step=0.01))
    stress_threshold = float(st.slider("Stress threshold", min_value=0.2, max_value=0.7, value=0.42, step=0.01))

    sample_period = float(st.select_slider("Sensor sampling period (h)", options=[0.5, 1.0, 2.0, 4.0, 6.0], value=2.0))
    sensor_noise = float(st.slider("Sensor noise (std)", min_value=0.0, max_value=0.05, value=0.01, step=0.001))
    quantization_levels = int(st.select_slider("Sensor quantization levels", options=[32, 64, 128, 256, 512], value=256))

    selected_controllers = st.multiselect(
        "Controllers to compare",
        options=list(ALL_CONTROLLER_NAMES),
        default=list(ALL_CONTROLLER_NAMES),
    )

    st.subheader("PID gains")
    kp = float(st.slider("Kp", min_value=0.1, max_value=6.0, value=2.0, step=0.1))
    ki = float(st.slider("Ki", min_value=0.0, max_value=0.5, value=0.08, step=0.01))
    kd = float(st.slider("Kd", min_value=0.0, max_value=1.0, value=0.2, step=0.01))

    st.subheader("Network simulation")
    node_count = int(st.slider("Sensor node count", min_value=4, max_value=40, value=12, step=1))
    mac_protocol = st.selectbox("MAC protocol", options=["csma_ca", "tdma"], index=0)
    path_loss_model = st.selectbox("Path loss model", options=["free_space", "log_distance"], index=0)

if not selected_controllers:
    st.warning("Select at least one controller.")
    st.stop()

try:
    cfg = SimulationConfig(
        sim_days=sim_days,
        dt_hours=dt_hours,
        seed=seed,
        initial_moisture=initial_moisture,
        field_capacity=field_capacity,
        stress_threshold=stress_threshold,
        sensor_sample_period_hours=sample_period,
        sensor_noise_std=sensor_noise,
        sensor_quantization_levels=quantization_levels,
    )
except ValueError as exc:
    st.error(f"Invalid input configuration: {exc}")
    st.stop()

pid_params = {"kp": kp, "ki": ki, "kd": kd, "setpoint": field_capacity - 0.05}
results = run_controller_comparison(
    controller_names=selected_controllers,
    cfg=cfg,
    seed=seed,
    pid_params=pid_params,
    sensor_sample_period_hours=sample_period,
)
metrics_df = compute_performance_metrics(results=results, cfg=cfg, baseline_controller="timer")

controller_focus = st.selectbox("Detailed view controller", options=selected_controllers, index=0)
focused = results.loc[results["controller"] == controller_focus].sort_values("hour")
latest_moisture = float(focused["moisture"].iloc[-1])
guidance = awd_guidance(latest_moisture, low_threshold=cfg.stress_threshold, high_threshold=cfg.field_capacity)

st.subheader("Soil moisture trajectory with control actions")
moisture_fig = make_subplots(specs=[[{"secondary_y": True}]])
for controller_name, group in results.groupby("controller"):
    moisture_fig.add_trace(
        go.Scatter(
            x=group["hour"],
            y=group["moisture"],
            mode="lines",
            name=f"{controller_name} moisture",
        ),
        secondary_y=False,
    )

moisture_fig.add_trace(
    go.Bar(
        x=focused["hour"],
        y=focused["irrigation_command"],
        name=f"{controller_focus} control",
        opacity=0.25,
        marker_color="#2ca02c",
    ),
    secondary_y=True,
)
moisture_fig.update_yaxes(title_text="Soil moisture", range=[0.0, 1.0], secondary_y=False)
moisture_fig.update_yaxes(title_text="Control action", range=[0.0, 1.0], secondary_y=True)
moisture_fig.update_layout(legend=dict(orientation="h"), margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(moisture_fig, use_container_width=True)

left, right = st.columns([1.1, 1.0])

with left:
    st.subheader("Controller performance")
    usage_fig = px.bar(
        metrics_df,
        x="controller",
        y="water_usage",
        color="water_savings_pct",
        color_continuous_scale="Blues",
        title="Water usage and savings",
    )
    st.plotly_chart(usage_fig, use_container_width=True)
    st.dataframe(
        metrics_df.sort_values("water_savings_pct", ascending=False).reset_index(drop=True),
        hide_index=True,
        use_container_width=True,
    )

with right:
    st.subheader("AWD realtime guidance")
    c1, c2, c3 = st.columns(3)
    c1.metric("Phase", str(guidance["phase"]))
    c2.metric("Current moisture", f"{latest_moisture:.3f}")
    c3.metric("Stress threshold", f"{cfg.stress_threshold:.3f}")

    st.info(str(guidance["recommendation"]))
    st.markdown(
        "\n".join(
            [
                f"- Low threshold indicator: {'🔴 below threshold' if guidance['below_low'] else '🟢 above threshold'}",
                f"- High threshold indicator: {'🔵 saturated band' if guidance['above_high'] else '🟡 not saturated'}",
                f"- Field capacity target: **{cfg.field_capacity:.2f}**",
            ]
        )
    )

st.subheader("Moisture distribution heatmap")
grid = moisture_grid(base_moisture=latest_moisture, rows=cfg.grid_rows, cols=cfg.grid_cols, seed=seed)
heatmap_fig = px.imshow(
    grid,
    color_continuous_scale="YlGnBu",
    zmin=0.0,
    zmax=1.0,
    labels={"x": "Field column", "y": "Field row", "color": "Moisture"},
)
st.plotly_chart(heatmap_fig, use_container_width=True)

st.subheader("Sensor network topology and battery")
network = simulate_sensor_network(
    node_count=node_count,
    hours=max(24, cfg.total_steps),
    seed=seed,
    mac_protocol=mac_protocol,
    path_loss_model=path_loss_model,
)

topo = network["topology"]
battery = network["battery"]
performance = network["performance"]

topo_fig = px.scatter(
    topo,
    x="x_m",
    y="y_m",
    color="snr_db",
    hover_data=["node_id", "distance_m", "path_loss_db"],
    title="Topology map",
)
topo_fig.add_trace(
    go.Scatter(
        x=[50.0],
        y=[50.0],
        mode="markers",
        marker=dict(symbol="x", size=14, color="red"),
        name="Gateway",
    )
)
st.plotly_chart(topo_fig, use_container_width=True)

battery_fig = px.line(battery, x="hour", y="battery_pct", color="node_id", title="Battery depletion timeline")
st.plotly_chart(battery_fig, use_container_width=True)

perf_fig = px.line(performance, x="hour", y="delivery_rate", title="Network delivery rate")
perf_fig.update_yaxes(range=[0.0, 1.0])
st.plotly_chart(perf_fig, use_container_width=True)

st.subheader("Parametric studies")

pid_gain_sets = [
    (max(0.1, kp * 0.6), max(0.0, ki * 0.6), max(0.0, kd * 0.6)),
    (kp, ki, kd),
    (min(6.0, kp * 1.4), min(0.5, ki * 1.4), min(1.0, kd * 1.4)),
]
pid_study_df = pid_gain_study(cfg=cfg, seed=seed + 100, gain_sets=pid_gain_sets)
pid_study_df["label"] = [f"Kp={r.kp:.2f},Ki={r.ki:.2f},Kd={r.kd:.2f}" for r in pid_study_df.itertuples()]
st.plotly_chart(
    px.bar(pid_study_df, x="label", y="water_usage", color="yield_proxy", title="PID gain sensitivity"),
    use_container_width=True,
)

sampling_df = sampling_rate_study(
    cfg=cfg,
    seed=seed + 200,
    sample_rates=[0.5, 1.0, 2.0, 4.0, 6.0],
    controller_name="linear_awd",
)
st.plotly_chart(
    px.line(
        sampling_df,
        x="sample_period_hours",
        y="water_savings_pct",
        markers=True,
        title="Sampling period impact on water savings",
    ),
    use_container_width=True,
)

node_counts = sorted({max(4, node_count // 2), node_count, min(40, node_count * 2)})
scaling_df = network_node_scaling_study(
    node_counts=node_counts,
    hours=24,
    seed=seed + 300,
    mac_protocol=mac_protocol,
    path_loss_model=path_loss_model,
)
scaling_fig = px.line(
    scaling_df,
    x="node_count",
    y="delivery_rate",
    markers=True,
    title="Network performance scaling vs node count",
)
scaling_fig.update_yaxes(range=[0.0, 1.0])
st.plotly_chart(scaling_fig, use_container_width=True)

st.caption("Deterministic seed controls disturbances, sensor noise, and network stochastic effects.")
