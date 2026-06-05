# Traffic Simulator (osmx-trafficsim)

A naturalistic traffic simulator that fuses **Lanelet2 OSM** lane geometry with
**OpenDRIVE (XODR)** metadata, simulates IDM-like vehicle / pedestrian / cyclist
flows with traffic-light logic, and **exports per-agent trajectory CSVs**. Those
trajectories feed scenario design for DIVP simulation.

!!! abstract "Separate repository"
    The traffic simulator lives in its own repository, not in this one:
    [:material-github: **tlab-wide/osmx-trafficsim**](https://github.com/tlab-wide/osmx-trafficsim)

## What it does

- Loads lane graphs from Lanelet2 OSM maps and merges XODR signals, stop lines,
  and crosswalks.
- Simulates vehicles, pedestrians, and cyclists with IDM-like dynamics and a
  traffic-light state machine.
- Animates the scene with Matplotlib (zoom / pan).
- Exports per-agent CSV trajectories — `[time, id, type, x, y, heading, speed]`.

The first three columns are directly compatible with the
[trajectory visualizer](trajectory-visualizer.md).

## Quick start

See the [project README](https://github.com/tlab-wide/osmx-trafficsim) for full
instructions. In brief:

```bash
git clone https://github.com/tlab-wide/osmx-trafficsim
cd osmx-trafficsim
python -m venv .venv && source .venv/bin/activate   # or .\.venv\Scripts\activate on Windows
pip install numpy matplotlib pyyaml
python main.py --config configs/config_example.yaml
```

It also ships helpers to **augment** a Lanelet2 map with XODR signals
(`tools/lanelet2_augment.py`) and to **inspect** traffic-light timing
(`tools/traffic_light_inspector.py`).
