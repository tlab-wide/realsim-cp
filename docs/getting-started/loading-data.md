# Loading the Data

This page shows how to read a RealSim-CP variant in Python — walk the frames,
compose the transform chain, and decode object cuboids. The only hard dependency
for parsing is the standard library; `numpy` helps with the math and
`open3d` (or any PCD reader) loads the point clouds.

## Walk one variant

```python
import json, pathlib

root = pathlib.Path("daiba_station_scenario/night_1")
labels = json.loads((root / "label_OpenLABEL_style.json").read_text())
ol = labels["openlabel"]

for fid in sorted(ol["frames"], key=int):
    frame = ol["frames"][fid]
    props = frame["frame_properties"]
    t     = props["timestamp"]               # seconds
    uris  = props["streams"]                  # sensor -> { "uri": "images/.../image_*.png" }
    tfs   = props["transforms"]               # scene -> agent_local poses (this frame)

    for obj_id, obj in frame.get("objects", {}).items():
        data = obj["object_data"]
        cls  = data["type"]                   # e.g. "TYPE_MEDIUM_CAR"
        x, y, z, qx, qy, qz, qw, L, W, H = data["cuboid"]["value"]
        # ... your code here (cuboid is in the scene frame)
```

## Compose the transform chain

Sensor poses are split into a **per-frame agent pose** and a **static sensor
extrinsic**. Compose them to get a sensor's pose in the scene. Quaternions are
**xyzw** ordered.

```python
import numpy as np

def quat_xyzw_to_R(q):
    x, y, z, w = q
    return np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - z*w),     2*(x*z + y*w)],
        [2*(x*y + z*w),     1 - 2*(x*x + z*z), 2*(y*z - x*w)],
        [2*(x*z - y*w),     2*(y*z + x*w),     1 - 2*(x*x + y*y)],
    ])

def make_T(quaternion, translation):
    T = np.eye(4)
    T[:3, :3] = quat_xyzw_to_R(quaternion)
    T[:3, 3]  = translation
    return T

# 1) scene -> vehicle_local (this frame), then invert for local -> scene
src = tfs["scene_to_vehicle_10000_local"]["transform_src_to_dst"]
scene_to_local = make_T(src["quaternion"], src["translation"])
local_to_scene = np.linalg.inv(scene_to_local)

# 2) sensor extrinsic (static): vehicle_local -> sensor
cs = ol["coordinate_systems"]["vehicle_10000/lidar_5_cs"]["pose_wrt_parent"]
sensor_to_local = make_T(cs["quaternion"], cs["translation"])

# 3) full chain
sensor_to_scene = local_to_scene @ sensor_to_local
scene_to_sensor = np.linalg.inv(sensor_to_scene)
```

!!! note "Static RSUs"
    For RSUs the agent pose may live in
    `coordinate_systems["rsu_1_local"]["pose_wrt_parent"]` rather than the
    per-frame `transforms`. Check `transforms` first, then fall back to the
    static coordinate system.

## Load a point cloud into the scene frame

```python
import open3d as o3d

pcd_uri = uris["vehicle_10000/lidar_5"]["uri"]      # relative to the variant root
pcd = o3d.io.read_point_cloud(str(root / pcd_uri))
pcd.transform(sensor_to_scene)                       # now in the scene frame
```

Fusing several agents' clouds (each transformed into the scene frame) is exactly
what cooperative perception needs — and what the
[visualizer](../tools/visualizer.md) renders.

## Build a cuboid's 8 corners

```python
def cuboid_corners(value):
    x, y, z, qx, qy, qz, qw, L, W, H = value
    hl, hw, hh = L/2, W/2, H/2
    local = np.array([
        [ hl,  hw,  hh], [ hl,  hw, -hh], [ hl, -hw,  hh], [ hl, -hw, -hh],
        [-hl,  hw,  hh], [-hl,  hw, -hh], [-hl, -hw,  hh], [-hl, -hw, -hh],
    ])
    R = quat_xyzw_to_R([qx, qy, qz, qw])
    return (local @ R.T) + np.array([x, y, z])       # corners in the scene frame
```

To draw a box on a camera image, transform the corners with `scene_to_sensor`,
then apply the camera intrinsics (`fx, fy, cx, cy`, optionally `k1…k6`). Mind the
[image-axis convention](../dataset/known-issues.md#coordinate-projection-quirks)
(`+Y` is image-left).

## See also

- [Label format](../dataset/label-format.md) — full schema reference.
- [Known issues](../dataset/known-issues.md) — gaps and quirks to tolerate.
- [Visualizer](../tools/visualizer.md) — a reference implementation of all of the
  above.
