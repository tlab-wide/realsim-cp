# Quickstart

Get from zero to exploring a RealSim-CP scene in three steps.

![Vehicle multi-camera preview](../assets/gif/vehicle-multicam.gif)

## 1. Download one scene

Grab a single variant to start — the **Daiba `night_1`** scene has the most
complete sensor coverage.

[:material-google-drive: Download RealSim-CP](https://drive.google.com/drive/folders/12aOsca1vCpP0ncBdA1NF39xsphXoEV-Z){ .md-button }

Download `daiba_station_scenario/night_1/` and note its local path, e.g.:

```text
C:\data\RealSim-CP\daiba_station_scenario\night_1
```

## 2. Install the visualizer

The [RealSim-CP Visualizer](../tools/visualizer.md) is an Open3D desktop viewer.
It needs **Python 3.12** (Open3D does not yet support 3.14 on Windows).

```powershell
# from the repository root
cd tools/realsim-cp-visualizer
py -3.12 -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e .
```

On macOS / Linux:

```bash
cd tools/realsim-cp-visualizer
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## 3. Run it

Point the viewer at the variant folder you downloaded:

```powershell
python -m realsim_viz "C:\data\RealSim-CP\daiba_station_scenario\night_1"
```

You'll get a unified 3D scene with the fused multi-agent point cloud, 3D
bounding boxes, and agent markers — plus a per-agent dashboard for inspecting
individual camera and LiDAR streams.

??? info "Key controls"
    - **Space** — play / pause
    - **← / →** — step one frame
    - **View buttons** — Top / Side / 3D camera presets
    - **Sidebar** — toggle layers, individual agents, all RSUs, all vehicles
    - **Dashboard** — pick an agent, add camera/LiDAR tiles
    - **Distortion** — toggle the `k1…k6` camera distortion model
    - **Overlay LiDAR** — project LiDAR points onto a camera tile

    Full reference: [Visualizer](../tools/visualizer.md).

## Prefer code?

To load the data programmatically (no GUI), head to
**[Loading the data](loading-data.md)** for a minimal Python walkthrough of the
OpenLABEL file, the transform chain, and cuboid decoding.
