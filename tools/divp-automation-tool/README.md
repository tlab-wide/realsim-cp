# DIVP Automation Tool

Automation around **DIVP** (Driving Intelligence Validation Platform) simulation
runs. It parses DIVP scenario XML, decomposes a multi-agent (V2X) scene into
per-agent scenarios, drives the MATLAB/Simulink models that render camera and
LiDAR data for each agent, and generates **OpenLABEL 1.0.0** annotations from the
outputs. This is the tool used to build the RealSim-CP dataset.

> Full documentation:
> <https://tlab-wide.github.io/realsim-cp/tools/automation-tool/>

## Requirements

- Python **3.11+**
- A licensed **MATLAB** compatible with `matlabengine==24.1.4`, plus the DIVP
  **V-Drive** toolbox.
- Python deps (see `pyproject.toml`): `matlabengine==24.1.4`, `numpy>=2.3.4`,
  `pandas>=2.3.3`.

> **Note.** This tool requires DIVP and MATLAB, so it is published mainly for
> transparency and reproducibility. Most users only need the resulting
> [dataset](https://tlab-wide.github.io/realsim-cp/dataset/download/).

## Install

```bash
pip install -e .
```

## Run

```bash
python main.py
```

By default `main.py` runs the `automation_scenario` example. It expects a
`scenarios/<name>/` tree containing the DIVP scenario XML, the OSI supplement
JSON, and trajectory CSVs; outputs are written under
`scenarios/<name>/output_data/`.

## Layout

| File | Purpose |
|---|---|
| `main.py` | Entry point: `generate_scenario_xml()` (per-agent decomposition) and `SimulationManager` (drives the MATLAB engine) |
| `generate_label.py` | Assembles the OpenLABEL annotation file from simulation outputs |
| `lib/calculate_matrix.py` | Rotation-matrix / Euler→quaternion helpers |
| `lib/utils.py` | JSON I/O helpers |
| `CameraAutomation.slx`, `LidarV20Automation.slx`, `GroundTruthBboxAutomation.slx` | DIVP/Simulink automation models |
| `LidarXYMapAutomationV20.m` | LiDAR XY-map MATLAB helper |
| `camera_rendering_automation.json`, `lidar_rendering_v20_automation.json` | Render configs |
| `V20SpecFileAutomation.csv` | LiDAR V20 sensor spec |

> The large per-location scenario inputs/outputs are **not** included in this
> repository. The rendered, annotated result is the published RealSim-CP dataset.
