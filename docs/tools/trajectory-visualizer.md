# Trajectory Visualizer

A lightweight Matplotlib tool that plots agent trajectories from CSV files — a
quick way to sanity-check scenario motion before or after simulation.

**Location:** [`tools/trajectory-visualizer/`](https://github.com/tlab-wide/realsim-cp/tree/main/tools/trajectory-visualizer)

## What it does

Reads every `*.csv` in a folder, uses the **first three columns** (by position)
as `timestamp, pos_x, pos_y`, and plots all trajectories in a single figure with
a legend.

## Requirements

- Python 3.8+
- `pandas`, `matplotlib`

```bash
pip install pandas matplotlib
```

## Run

```bash
cd tools/trajectory-visualizer
python plot_trajectories.py --folder /path/to/csvs
```

The folder should contain trajectory CSVs whose first three columns are time,
x, and y (column names are ignored). Trajectory CSVs of this shape are produced
by the [traffic simulator](traffic-simulator.md).

!!! info "Sample CSVs not bundled"
    Sample trajectory CSVs are not included in this repository. Generate your own
    with the traffic simulator, or export them from a scenario.
