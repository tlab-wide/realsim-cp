"""OpenLABEL dataset loader for RealSim-CP variants."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

import numpy as np

from .transforms import invert_transform, make_transform, pose_from_openlabel


@dataclass(frozen=True)
class Sensor:
    stream_id: str
    agent_id: str
    sensor_id: str
    kind: str
    width: int | None = None
    height: int | None = None
    intrinsics: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Cuboid:
    object_id: str
    class_name: str
    name: str
    value: tuple[float, ...]

    @property
    def center(self) -> np.ndarray:
        return np.asarray(self.value[:3], dtype=float)

    @property
    def quaternion(self) -> tuple[float, float, float, float]:
        return tuple(self.value[3:7])  # xyzw

    @property
    def extent(self) -> tuple[float, float, float]:
        return tuple(max(float(v), 1e-3) for v in self.value[7:10])


@dataclass(frozen=True)
class FrameData:
    frame_id: int
    timestamp: float
    streams: dict[str, Path]
    transforms: dict[str, np.ndarray]
    cuboids: list[Cuboid]


class RealSimVariant:
    """Parsed view of one RealSim-CP scenario variant."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        label_path = self.root / "label_OpenLABEL_style.json"
        if not label_path.exists():
            raise FileNotFoundError(f"Missing OpenLABEL file: {label_path}")

        with label_path.open("r", encoding="utf-8") as handle:
            self.raw = json.load(handle)["openlabel"]

        self.streams: dict[str, Sensor] = self._parse_streams()
        self.coordinate_systems = self.raw.get("coordinate_systems", {})
        self.frames = sorted((int(k), v) for k, v in self.raw.get("frames", {}).items())
        self.agent_ids = sorted({sensor.agent_id for sensor in self.streams.values()})
        self._sensor_to_local = self._parse_sensor_poses()
        self._static_scene_to_local = self._parse_static_agent_poses()

    def __len__(self) -> int:
        return len(self.frames)

    def _parse_streams(self) -> dict[str, Sensor]:
        sensors: dict[str, Sensor] = {}
        for stream_id, spec in self.raw.get("streams", {}).items():
            if "/" not in stream_id:
                continue
            agent_id, sensor_id = stream_id.split("/", 1)
            props = spec.get("stream_properties", {})
            camera = props.get("intrinsics_custom", {}).get("camera_parameters", {})
            sensors[stream_id] = Sensor(
                stream_id=stream_id,
                agent_id=agent_id,
                sensor_id=sensor_id,
                kind=spec.get("type", "unknown"),
                width=props.get("width"),
                height=props.get("height"),
                intrinsics={k: float(v) for k, v in camera.items() if isinstance(v, (int, float))},
            )
        return sensors

    def _parse_sensor_poses(self) -> dict[str, np.ndarray]:
        poses: dict[str, np.ndarray] = {}
        for cs_name, spec in self.coordinate_systems.items():
            if spec.get("type") != "sensor_cs" or not cs_name.endswith("_cs"):
                continue
            stream_id = cs_name[:-3]
            poses[stream_id] = pose_from_openlabel(spec.get("pose_wrt_parent"))
        return poses

    def _parse_static_agent_poses(self) -> dict[str, np.ndarray]:
        poses: dict[str, np.ndarray] = {}
        for cs_name, spec in self.coordinate_systems.items():
            if spec.get("type") != "local_cs" or spec.get("parent") != "scene":
                continue
            pose = spec.get("pose_wrt_parent")
            if pose:
                poses[cs_name] = pose_from_openlabel(pose)
        return poses

    def frame(self, index: int) -> FrameData:
        if index < 0 or index >= len(self.frames):
            raise IndexError(index)
        frame_id, frame = self.frames[index]
        props = frame.get("frame_properties", {})

        streams: dict[str, Path] = {}
        for stream_id, stream in props.get("streams", {}).items():
            uri = stream.get("uri")
            if uri:
                streams[stream_id] = self.root / uri

        transforms: dict[str, np.ndarray] = {}
        for name, spec in props.get("transforms", {}).items():
            tf = spec.get("transform_src_to_dst", {})
            transforms[name] = make_transform(tf.get("quaternion", [0, 0, 0, 1]), tf.get("translation", [0, 0, 0]))

        cuboids = []
        for object_id, obj in frame.get("objects", {}).items():
            data = obj.get("object_data", {})
            cuboid = data.get("cuboid", {})
            value = cuboid.get("value")
            if value and len(value) >= 10:
                cuboids.append(
                    Cuboid(
                        object_id=object_id,
                        class_name=data.get("type", "UNKNOWN"),
                        name=data.get("name", object_id),
                        value=tuple(float(v) for v in value[:10]),
                    )
                )

        return FrameData(
            frame_id=frame_id,
            timestamp=float(props.get("timestamp", frame_id)),
            streams=streams,
            transforms=transforms,
            cuboids=cuboids,
        )

    def sensor(self, stream_id: str) -> Sensor:
        return self.streams[stream_id]

    def sensors_for_agent(self, agent_id: str, kind: str | None = None) -> list[Sensor]:
        sensors = [s for s in self.streams.values() if s.agent_id == agent_id]
        if kind:
            sensors = [s for s in sensors if s.kind == kind]
        return sorted(sensors, key=lambda s: s.stream_id)

    def scene_to_local(self, frame: FrameData, agent_id: str) -> np.ndarray:
        local_name = f"{agent_id}_local"
        dynamic = frame.transforms.get(f"scene_to_{local_name}")
        if dynamic is not None:
            return dynamic
        return self._static_scene_to_local.get(local_name, np.eye(4))

    def local_to_scene(self, frame: FrameData, agent_id: str) -> np.ndarray:
        return invert_transform(self.scene_to_local(frame, agent_id))

    def local_to_sensor(self, stream_id: str) -> np.ndarray:
        # pose_wrt_parent is local -> sensor_cs in this OpenLABEL export.
        return self._sensor_to_local.get(stream_id, np.eye(4))

    def sensor_to_local(self, stream_id: str) -> np.ndarray:
        return invert_transform(self.local_to_sensor(stream_id))

    def sensor_to_scene(self, frame: FrameData, stream_id: str) -> np.ndarray:
        sensor = self.sensor(stream_id)
        return self.local_to_scene(frame, sensor.agent_id) @ self.sensor_to_local(stream_id)

    def scene_to_sensor(self, frame: FrameData, stream_id: str) -> np.ndarray:
        return invert_transform(self.sensor_to_scene(frame, stream_id))

    def point_cloud_to_scene(self, frame: FrameData, stream_id: str) -> np.ndarray:
        return self.sensor_to_scene(frame, stream_id)
