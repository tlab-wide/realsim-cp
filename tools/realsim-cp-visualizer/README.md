# RealSim-CP Visualizer

Desktop viewer for RealSim-CP variants.

## Run

Use Python 3.12 for this viewer. Python 3.14 is currently too new for `open3d`
on Windows, and dependency installation can fail with:

```text
ERROR: No matching distribution found for open3d>=0.18
```

Windows can keep multiple Python versions installed side by side. For example,
you can keep Python 3.14 for other work and install Python 3.12 for this
project. Install Python 3.12 from
<https://www.python.org/downloads/release/python-312/> and include the **Python
Launcher** during installation.

After installing, open a new PowerShell and list installed versions:

```powershell
py -0p
```

You should see entries similar to:

```text
 -3.14-64   C:\Users\ehsan\AppData\Local\Programs\Python\Python314\python.exe
 -3.12-64   C:\Users\ehsan\AppData\Local\Programs\Python\Python312\python.exe
```

Create a project-local virtual environment with Python 3.12:

```powershell
cd tools/realsim-cp-visualizer
py -3.12 -m venv .venv
.\.venv\Scripts\activate
python --version
```

Then install the viewer dependencies once:

```powershell
python -m pip install -e .
```

Run the viewer with the path to a downloaded dataset variant:

```powershell
python -m realsim_viz "C:\data\RealSim-CP\daiba_station_scenario\night_1"
```

For Shutoko:

```powershell
python -m realsim_viz "C:\data\RealSim-CP\shutoko_scenario\sunny_1"
```

Download the dataset from the
[project Drive](https://drive.google.com/drive/folders/12aOsca1vCpP0ncBdA1NF39xsphXoEV-Z)
(see the [docs](https://tlab-wide.github.io/realsim-cp/getting-started/quickstart/)).

If `py` is not recognized, add the Python Launcher to your user `PATH`:

```text
C:\Users\ehsan\AppData\Local\Programs\Python\Launcher\
```

If `python` is not recognized outside the activated `.venv`, add the selected
Python install and scripts folders to `PATH`, for example:

```text
C:\Users\ehsan\AppData\Local\Programs\Python\Python312\
C:\Users\ehsan\AppData\Local\Programs\Python\Python312\Scripts\
```

Controls:

- Space: play / pause
- Left / Right: step one frame
- View buttons: switch the 3D scene between Top, Side, and 3D angled views
- Sidebar: toggle scene layers, individual agents, all RSUs, or all vehicles
- Right dashboard: choose an agent, select a camera or LiDAR, and add it as a
  tile with the Add camera / Add lidar buttons
- Overlay LiDAR: camera tiles show the selected agent LiDAR by default; use the
  checkbox to turn it off or choose another source from the overlay dropdown
- Distortion: camera tiles default to pinhole projection; enable the checkbox
  to apply the label file's `k1..k6` distortion coefficients
- Loaded data: expand the left sidebar section to see frame, agent, camera,
  LiDAR, image, PCD, and object counts
- Maximize: choose a tile under Tile actions and press Maximize for a larger
  camera or LiDAR view

The viewer tolerates missing point-cloud files, which is required for `sunny_1`
and `sunny_2`.

Implemented layers:

- source-colored LiDAR point clouds
- scene-frame 3D cuboids
- agent markers
- camera frustums
- agent trajectories
- per-agent camera and LiDAR dashboard tiles
- LiDAR scan projection over camera tiles
- loaded dataset summary
- maximized camera/LiDAR tile dialog
