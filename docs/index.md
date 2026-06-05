# RealSim-CP

**A high-fidelity, multi-modal cooperative-perception dataset for Japanese urban traffic.**

RealSim-CP provides synchronized **camera + LiDAR** data captured from multiple
**connected vehicles and roadside units (RSUs)** observing the same traffic
scene, with **3D object annotations** in the **ASAM OpenLABEL 1.0.0** schema.
Every scene is generated with the physics-based **[DIVP](simulator/divp.md)**
simulator (ray tracing + electromagnetic-wave sensor modeling), so the data
stays close to real sensor physics while costing a fraction of real-world
collection.

![RealSim-CP dataset overview](assets/img/dataset-overview.png)

/// caption
Multiple vehicles and RSUs observe one shared traffic scene. Each variant ships
synchronized camera images, LiDAR point clouds, calibration, per-frame poses,
and OpenLABEL 3D annotations.
///

<div class="grid cards" markdown>

- :material-rocket-launch: **[Quickstart](getting-started/quickstart.md)**
  Download a scene and explore it in the 3D visualizer in minutes.

- :material-download: **[Download the dataset](dataset/download.md)**
  Get the data from the project's Google Drive.

- :material-folder-table: **[Dataset structure](dataset/structure.md)**
  Scenarios, weather/time variants, agents, and sensor streams.

- :material-code-json: **[Label format](dataset/label-format.md)**
  OpenLABEL schema, coordinate systems, and the transform chain.

- :material-tools: **[Tools](tools/index.md)**
  3D visualizer, label-generation automation, and more.

- :material-chart-box: **[Benchmark](benchmark.md)**
  CoopDet3D cooperative-perception results.

</div>

## Why RealSim-CP?

Existing cooperative-perception datasets share two gaps that RealSim-CP is built
to close:

1. **Japanese traffic is under-represented.** Left-hand traffic, distinctive
   vehicle types (kei cars, Japanese buses/trucks), and region-specific
   infrastructure are rarely captured. Models trained elsewhere degrade when
   moved to a new region, so region-specific data matters.
2. **Real-world collection is expensive.** Instrumenting many cooperative agents
   and labeling multimodal data at scale is costly and slow. High-fidelity
   simulation produces large, diverse, perfectly-labeled data at far lower cost.

See the **[Overview](overview.md)** for the full motivation, methodology, and
contributions.

## At a glance

| | |
|---|---|
| **Domain** | Cooperative perception · V2V / V2I / V2X · autonomous driving |
| **Modalities** | RGB camera images + LiDAR point clouds (`.pcd`) |
| **Agents** | Connected vehicles + roadside units (RSUs) |
| **Region** | Tokyo, Japan (Aomi, Odaiba/Daiba, Shutoko Expressway) |
| **Conditions** | Clear day · rainy day · clear night |
| **Annotations** | 3D cuboids, 12 object classes, ASAM OpenLABEL 1.0.0 |
| **Rate** | 10 Hz synchronized capture |
| **Generator** | DIVP physics-based simulator |
| **Dataset license** | CC BY 4.0 |
| **Code license** | MIT |

## Citation

If you use RealSim-CP, please cite the paper — see the
[Citation section of the README](https://github.com/tlab-wide/realsim-cp#citation)
or [`CITATION.cff`](https://github.com/tlab-wide/realsim-cp/blob/main/CITATION.cff).
