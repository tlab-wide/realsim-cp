# Benchmark

RealSim-CP is evaluated with **CoopDet3D**, a state-of-the-art multimodal V2I
cooperative 3D object-detection framework, to confirm that the dataset supports
cooperative-perception research and to provide a reference baseline.

## Object classes

The dataset annotates **12 classes**:

> Pedestrian · Bicycle · Motorbike · Small car · Compact car · Medium car ·
> Luxury car · Heavy truck · Semitractor · Semitrailer · Bus · Other

For evaluation, RealSim-CP classes are mapped onto the TUMTraf V2X class set used
by CoopDet3D:

| RealSim-CP class | Evaluation class |
|---|---|
| Small / Compact / Medium / Luxury car | Car |
| Motorbike | Bicycle |
| Heavy truck / Semitractor | Truck |
| Semitrailer | Trailer |
| Bus | Bus |
| Pedestrian | Pedestrian |
| Other | *(excluded)* |

## Evaluation setup

- Per map, **2–4 RSUs** and **1 vehicle** were selected for evaluation.
- Agents are counted within a **30 m radius** of the evaluation RSU: mean
  **3.58** agents per frame (median 3.00), range 1–8.
- Two settings are compared: **Cooperative** (RSU + vehicle, early fusion) and
  **RSU-only** (late fusion baseline).

## Results — overall (BEV)

| Setting | mAP | mATE | mASE | mAOE | mAVE | NDS |
|---|---:|---:|---:|---:|---:|---:|
| **Cooperative** | 0.2025 | 0.8753 | 0.7573 | 0.9930 | 0.7143 | 0.1858 |
| **RSU only** | 0.1902 | 0.8881 | 0.7454 | 0.9888 | 0.7143 | 0.1794 |

The cooperative setting improves mAP by **~1.23%** over the RSU-only baseline,
confirming that sharing vehicle and infrastructure observations helps.

## Results — per class (cooperative, BEV mAP)

| Class | mAP |
|---|---:|
| Car | 0.691 |
| Bus | 0.726 |
| Truck / Trailer / Van / Pedestrian / Bicycle | 0.000 |

Common classes (cars, buses) are detected well. Rare classes score near zero,
which reflects the strong **class imbalance** in the data (see
[Scenarios → class imbalance](dataset/scenarios.md#class-imbalance)) rather than a
limitation of the framework — addressing it is part of future work.

## Where RealSim-CP sits

Compared with existing simulator-built cooperative-perception datasets (e.g.
V2V-Sim, V2XSet, OPV2V, IRV2V, SCOPE, Adver-City), RealSim-CP is distinguished by
its **physics-based, calibrated** sensor simulation and its focus on **Japanese**
urban traffic with multiple cooperating agents and both camera and LiDAR
modalities.

## Takeaway

High-fidelity simulation can meaningfully bridge the simulation-to-real gap while
greatly reducing data-collection cost, and the cooperative setting measurably
improves detection over infrastructure-only perception. Full numbers, tables, and
methodology are in the [paper](overview.md#paper).
