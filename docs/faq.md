# FAQ

### What is RealSim-CP, in one sentence?

A high-fidelity, multimodal (camera + LiDAR) **cooperative-perception** dataset
for Japanese urban traffic, generated with the physics-based DIVP simulator and
annotated in ASAM OpenLABEL 1.0.0.

### Is the data real or simulated?

Simulated — but with a **physics-based** simulator (DIVP) that ray-traces sensor
operation and is calibrated against real measurements, so it stays close to real
sensor behavior. See [Simulator (DIVP)](simulator/divp.md).

### How do I download it?

From the project's Google Drive — see [Download](dataset/download.md). You can
grab a single scenario/variant (a few GB) rather than everything.

### How is it licensed? Can I use it commercially?

The **dataset** is **CC BY 4.0** — yes, including commercial use, with
attribution (cite the paper). The **code/tools** are **MIT**. See
[DATA_LICENSE.md](https://github.com/tlab-wide/realsim-cp/blob/main/DATA_LICENSE.md)
and [LICENSE](https://github.com/tlab-wide/realsim-cp/blob/main/LICENSE).

### What annotation format is used?

ASAM **OpenLABEL 1.0.0** — one JSON file per variant with streams, the
coordinate-system tree, per-frame poses, and 3D object cuboids. See
[Label format](dataset/label-format.md).

### Why does the agent pose not match the vehicle body center?

The `vehicle_*_local` frame is the parent for mounted sensors and sits near the
rear axle, not the body center. Use the matching labeled cuboid for the body. See
[Label format](dataset/label-format.md#vehicle-pose-origin-vs-labeled-cuboid).

### Some daytime scenes are missing point clouds — is that a bug?

The Daiba `sunny_1` / `sunny_2` variants have incomplete or absent LiDAR. Use a
**night** variant for full LiDAR coverage, and make your loader tolerate missing
files. See [Known issues](dataset/known-issues.md).

### What sensors are simulated?

Cameras modeled on the Sony IMX490 (120° HFOV) and LiDAR modeled on the Velodyne
VLS-128, at 10 Hz. See [Sensors](dataset/sensors.md).

### How do I view a scene quickly?

Install the [Visualizer](tools/visualizer.md) (Python 3.12 + Open3D) and run
`python -m realsim_viz <variant_path>`. See the [Quickstart](getting-started/quickstart.md).

### How do I cite RealSim-CP?

See the [Citation section of the README](https://github.com/tlab-wide/realsim-cp#citation)
or [`CITATION.cff`](https://github.com/tlab-wide/realsim-cp/blob/main/CITATION.cff).

### How do I report a problem or ask a question?

Open an issue on [GitHub](https://github.com/tlab-wide/realsim-cp/issues).
