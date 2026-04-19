# Smart Paddy AWD Irrigation Simulator

Streamlit app for irrigation control simulation as a feedback-control problem.

## Features

- First-order soil moisture dynamics with irrigation input, rainfall, ET disturbance, and deep percolation
- Sensor sampling/hold, Gaussian noise, and quantization
- Controllers: Linear/Step/Aggressive/Conservative AWD, PID, bang-bang hysteresis, timer baseline
- Pump actuator with on/off state and flow constraints
- Metrics: water usage, savings vs timer, moisture stress/violations, yield proxy
- Network model: free-space/log-distance path loss, PER from SNR, CSMA/CA or TDMA, topology and battery depletion
- Parametric studies for PID gains, sampling rates, and node-count scaling

## Install

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Docker (Railway)

```bash
docker build -t smart-paddy .
```

Bash/Zsh (uses `PORT` if set, defaults to 8501):
```bash
docker run --rm -e PORT=${PORT:-8501} -p ${PORT:-8501}:${PORT:-8501} smart-paddy
```

Shell-agnostic fixed-port:
```bash
docker run --rm -e PORT=8501 -p 8501:8501 smart-paddy
```

Railway notes:
- Railway auto-detects the `Dockerfile` and builds the image automatically.
- Railway provides `PORT`; the container command already binds Streamlit to that port.

## Test

```bash
pytest -q
```
