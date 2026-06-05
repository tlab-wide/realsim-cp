# Download

The full RealSim-CP dataset is hosted on Google Drive.

[:material-google-drive: **Download RealSim-CP**](https://drive.google.com/drive/folders/12aOsca1vCpP0ncBdA1NF39xsphXoEV-Z){ .md-button .md-button--primary }

!!! info "License"
    The dataset is released under **CC BY 4.0** — free to use, including
    commercially, with attribution. Please cite the paper (see
    [README → Citation](https://github.com/tlab-wide/realsim-cp#citation)).
    The tools in this repository are MIT-licensed.

## What you download

The dataset is organized by **scenario**, then by **weather/time variant**:

```
RealSim-CP/
└── <scenario>/                 # e.g. daiba_station_scenario
    ├── sunny_1/  sunny_2/       # clear daytime
    ├── night_1/  night_2/       # clear nighttime
    └── rainy_1/  rainy_2/       # rainy daytime
```

Each variant is a self-contained ~10-second clip at 10 Hz with its own images,
point clouds, and a single OpenLABEL annotation file. See
[Dataset structure](structure.md) for the per-variant layout.

## Grab only what you need

Variants are independent, so you can download a single weather/time variant of a
single scenario to get started (a few GB) rather than the whole dataset. A good
first download is one **night** variant of the Daiba Station scenario — it has
the most complete sensor coverage.

!!! tip "Recommended first scene"
    `daiba_station_scenario/night_1` — 4 RSUs + 11 vehicles, full camera and
    LiDAR coverage, 101 frames. Pair it with the
    [Quickstart](../getting-started/quickstart.md) and the
    [Visualizer](../tools/visualizer.md).

## Approximate sizes

A single fully-populated variant (images for all agents + LiDAR for all agents +
the label file) is on the order of a few gigabytes; image-heavy multi-vehicle
variants are larger. Daytime variants may omit some LiDAR (see
[Known issues](known-issues.md)). Plan disk accordingly before pulling multiple
scenarios.

## Next steps

- [Dataset structure](structure.md) — folders, agents, and sensor streams.
- [Sensors](sensors.md) — camera and LiDAR specifications.
- [Label format](label-format.md) — OpenLABEL schema and coordinate frames.
- [Loading the data](../getting-started/loading-data.md) — Python loading code.
