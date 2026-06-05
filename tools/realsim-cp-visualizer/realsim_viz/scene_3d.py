"""Open3D geometry builder for the unified RealSim-CP scene."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .colors import agent_color, class_color
from .loader import Cuboid, FrameData, RealSimVariant
from .projection import cuboid_corners, BOX_EDGES
from .transforms import make_transform


@dataclass
class SceneLayers:
    point_clouds: bool = True
    cuboids: bool = True
    agents: bool = True
    grid: bool = True
    frustums: bool = False
    trajectories: bool = False


def _require_open3d():
    try:
        import open3d as o3d
    except ImportError as exc:
        raise RuntimeError("Open3D is required for the 3D viewer. Install with: pip install open3d") from exc
    return o3d


class Open3DSceneBuilder:
    def __init__(self, variant: RealSimVariant, max_points_per_cloud: int = 80000):
        self.variant = variant
        self.max_points_per_cloud = max_points_per_cloud
        self.o3d = _require_open3d()
        self._frame_id_to_index = {frame_id: i for i, (frame_id, _frame) in enumerate(variant.frames)}

    def build(self, frame: FrameData, visible_agents: set[str], layers: SceneLayers) -> list[object]:
        geometries: list[object] = []
        if layers.grid:
            geometries.append(self._grid())
        if layers.point_clouds:
            geometries.extend(self._point_clouds(frame, visible_agents))
        if layers.cuboids:
            geometries.extend(self._cuboids(frame))
        if layers.frustums:
            geometries.extend(self._frustums(frame, visible_agents))
        if layers.trajectories:
            geometries.extend(self._trajectories(frame, visible_agents))
        if layers.agents:
            geometries.extend(self._agent_markers(frame, visible_agents))
        return geometries

    def _point_clouds(self, frame: FrameData, visible_agents: set[str]) -> list[object]:
        out = []
        for stream_id, path in frame.streams.items():
            sensor = self.variant.streams.get(stream_id)
            if not sensor or sensor.kind != "lidar" or sensor.agent_id not in visible_agents:
                continue
            if not Path(path).exists():
                continue
            if _pcd_has_no_points(path):
                continue
            cloud = self.o3d.io.read_point_cloud(str(path))
            if cloud.is_empty():
                continue
            points = np.asarray(cloud.points)
            if len(points) > self.max_points_per_cloud:
                step = max(1, len(points) // self.max_points_per_cloud)
                cloud = cloud.select_by_index(range(0, len(points), step))
            cloud.paint_uniform_color(agent_color(sensor.agent_id))
            cloud.transform(self.variant.point_cloud_to_scene(frame, stream_id))
            out.append(cloud)
        return out

    def _cuboids(self, frame: FrameData) -> list[object]:
        out = []
        for cuboid in frame.cuboids:
            corners = cuboid_corners(cuboid)
            line_set = self.o3d.geometry.LineSet()
            line_set.points = self.o3d.utility.Vector3dVector(corners)
            line_set.lines = self.o3d.utility.Vector2iVector(BOX_EDGES)
            color = class_color(cuboid.class_name)
            line_set.colors = self.o3d.utility.Vector3dVector([color] * len(BOX_EDGES))
            out.append(line_set)
        return out

    def _agent_markers(self, frame: FrameData, visible_agents: set[str]) -> list[object]:
        out = []
        for agent_id in sorted(visible_agents):
            tf = self.variant.local_to_scene(frame, agent_id)
            if agent_id.startswith("rsu_"):
                mesh = self.o3d.geometry.TriangleMesh.create_cylinder(radius=0.6, height=6.0)
                mesh.translate((0, 0, 3.0))
            else:
                cuboid = _agent_vehicle_cuboid(frame, agent_id)
                if cuboid is not None:
                    mesh = self._vehicle_mesh_from_cuboid(cuboid)
                    mesh.paint_uniform_color(agent_color(agent_id))
                    out.append(mesh)
                    continue

                length, width, height = 4.5, 2.0, 1.8
                mesh = self.o3d.geometry.TriangleMesh.create_box(width=length, height=width, depth=height)
                # Vehicle local poses in this dataset sit near the rear axle
                # ground contact, not at the geometric center.
                mesh.translate((0.30 * length - length / 2.0, -width / 2.0, 0.0))
            mesh.compute_vertex_normals()
            mesh.paint_uniform_color(agent_color(agent_id))
            mesh.transform(tf)
            out.append(mesh)
        return out

    def _vehicle_mesh_from_cuboid(self, cuboid: Cuboid):
        length, width, height = cuboid.extent
        mesh = self.o3d.geometry.TriangleMesh.create_box(width=length, height=width, depth=height)
        mesh.translate((-length / 2.0, -width / 2.0, -height / 2.0))
        mesh.compute_vertex_normals()
        mesh.transform(make_transform(cuboid.quaternion, cuboid.center))
        return mesh

    def _frustums(self, frame: FrameData, visible_agents: set[str]) -> list[object]:
        out = []
        for sensor in self.variant.streams.values():
            if sensor.kind != "camera" or sensor.agent_id not in visible_agents:
                continue
            width = sensor.width or 1158
            height = sensor.height or 750
            fx = sensor.intrinsics.get("fx", 600.0)
            fy = sensor.intrinsics.get("fy", 600.0)
            cx = sensor.intrinsics.get("cx", width / 2)
            cy = sensor.intrinsics.get("cy", height / 2)
            depth = 12.0
            corners = np.array(
                [
                    [0, 0, 0],
                    [(-cx) / fx * depth, (-cy) / fy * depth, depth],
                    [(width - cx) / fx * depth, (-cy) / fy * depth, depth],
                    [(width - cx) / fx * depth, (height - cy) / fy * depth, depth],
                    [(-cx) / fx * depth, (height - cy) / fy * depth, depth],
                ],
                dtype=float,
            )
            corners = self.variant.sensor_to_scene(frame, sensor.stream_id) @ np.c_[corners, np.ones(len(corners))].T
            points = corners.T[:, :3]
            lines = [(0, 1), (0, 2), (0, 3), (0, 4), (1, 2), (2, 3), (3, 4), (4, 1)]
            line_set = self.o3d.geometry.LineSet()
            line_set.points = self.o3d.utility.Vector3dVector(points)
            line_set.lines = self.o3d.utility.Vector2iVector(lines)
            line_set.colors = self.o3d.utility.Vector3dVector([agent_color(sensor.agent_id)] * len(lines))
            out.append(line_set)
        return out

    def _trajectories(self, frame: FrameData, visible_agents: set[str]) -> list[object]:
        out = []
        current = self._frame_id_to_index.get(frame.frame_id, 0)
        for agent_id in sorted(visible_agents):
            points = []
            for i in range(current + 1):
                f = self.variant.frame(i)
                pose = self.variant.local_to_scene(f, agent_id)
                points.append(pose[:3, 3])
            if len(points) < 2:
                continue
            line_set = self.o3d.geometry.LineSet()
            line_set.points = self.o3d.utility.Vector3dVector(np.asarray(points, dtype=float))
            line_set.lines = self.o3d.utility.Vector2iVector([(i, i + 1) for i in range(len(points) - 1)])
            line_set.colors = self.o3d.utility.Vector3dVector([agent_color(agent_id)] * (len(points) - 1))
            out.append(line_set)
        return out

    def _grid(self, size: int = 80, step: int = 10):
        lines = []
        points = []
        for i in range(-size, size + 1, step):
            points.extend([(i, -size, 0), (i, size, 0), (-size, i, 0), (size, i, 0)])
            n = len(points)
            lines.extend([(n - 4, n - 3), (n - 2, n - 1)])
        line_set = self.o3d.geometry.LineSet()
        line_set.points = self.o3d.utility.Vector3dVector(np.asarray(points, dtype=float))
        line_set.lines = self.o3d.utility.Vector2iVector(lines)
        line_set.colors = self.o3d.utility.Vector3dVector([(0.25, 0.25, 0.25)] * len(lines))
        return line_set


def _pcd_has_no_points(path: Path) -> bool:
    try:
        with Path(path).open("rb") as handle:
            for raw in handle:
                line = raw.decode("ascii", errors="ignore").strip()
                if line.startswith("POINTS"):
                    parts = line.split()
                    return len(parts) > 1 and int(float(parts[1])) == 0
                if line.startswith("DATA"):
                    return False
    except OSError:
        return True
    return False


def _agent_vehicle_cuboid(frame: FrameData, agent_id: str) -> Cuboid | None:
    if not agent_id.startswith("vehicle_"):
        return None
    object_id = agent_id.removeprefix("vehicle_")
    for cuboid in frame.cuboids:
        if cuboid.object_id == object_id:
            return cuboid
    return None
