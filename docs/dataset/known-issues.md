# Known Issues & Data Quirks

A short list of quirks to handle when loading RealSim-CP. The
[visualizer](../tools/visualizer.md) already tolerates all of these; if you write
your own loader, account for them too.

## Point-cloud gaps (Daiba daytime variants)

- **`sunny_1`** has LiDAR folders for only 8 of the 12 image agents, and each
  folder currently contains **only one `.pcd`** file instead of one per frame.
- **`sunny_2`** has **no `point_clouds/` directory** at all — images and the
  label JSON only.

The label JSON in these variants still references the missing point-cloud URIs,
so a loader should **skip missing files gracefully** (degrade to "no point cloud"
for that agent/frame) rather than erroring.

!!! tip "Want full LiDAR coverage?"
    Use a **night** variant (`night_1` / `night_2`) — these have complete
    per-frame LiDAR for all agents.

## Coordinate / projection quirks

- **Quaternion order** in cuboid vectors is **xyzw** (`[x, y, z, qx, qy, qz, qw,
  L, W, H]`), not wxyz.
- **Vehicle agent pose ≠ body center.** `vehicle_*_local` sits near the rear-axle
  ground point. Use the matching labeled object cuboid to draw the vehicle body.
  See [Label format](label-format.md#vehicle-pose-origin-vs-labeled-cuboid).
- **Camera image axis:** projection uses `+X` forward, `+Y` image-left, `+Z` up,
  so flip the horizontal axis when drawing to pixels.
- **Distortion vs. pinhole:** some rendered images align better with a pinhole
  model than with the full `k1…k6` distortion. Make distortion optional in your
  projection.
- **Per-frame transforms** exist for moving agents (vehicles); static RSU frames
  may instead rely on `coordinate_systems[rsu_*_local].pose_wrt_parent`.

## Reporting problems

Found something off in the data? Please open an issue on
[GitHub](https://github.com/tlab-wide/realsim-cp/issues).
