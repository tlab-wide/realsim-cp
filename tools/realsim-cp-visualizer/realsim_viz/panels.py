"""Per-agent dashboard rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .colors import class_color
from .loader import FrameData, RealSimVariant, Sensor
from .projection import BOX_EDGES, cuboid_corners, project_points
from .transforms import transform_points

TILE_SIZE = (360, 230)


@dataclass(frozen=True)
class AgentPanelData:
    agent_id: str
    cameras: list[tuple[Sensor, Path | None]]
    lidars: list[tuple[Sensor, Path | None]]


def panel_data(variant: RealSimVariant, frame: FrameData, agent_id: str) -> AgentPanelData:
    cameras = []
    lidars = []
    for sensor in variant.sensors_for_agent(agent_id):
        path = frame.streams.get(sensor.stream_id)
        item = (sensor, path if path and path.exists() else None)
        if sensor.kind == "camera":
            cameras.append(item)
        elif sensor.kind == "lidar":
            lidars.append(item)
    return AgentPanelData(agent_id=agent_id, cameras=cameras, lidars=lidars)


def render_camera_tile(
    variant: RealSimVariant,
    frame: FrameData,
    sensor: Sensor,
    path: Path | None,
    draw_cuboids: bool = True,
    overlay_lidar: tuple[Sensor, Path | None] | None = None,
    apply_distortion: bool = False,
    size: tuple[int, int] = TILE_SIZE,
) -> Image.Image:
    if path and path.exists():
        image = Image.open(path).convert("RGB")
    else:
        image = _blank(f"{sensor.stream_id}\nmissing image", (80, 84, 92), size)

    if draw_cuboids and path and path.exists():
        draw = ImageDraw.Draw(image)
        scene_to_camera = variant.scene_to_sensor(frame, sensor.stream_id)
        for cuboid in frame.cuboids:
            pixels, valid = project_points(
                sensor,
                cuboid_corners(cuboid),
                scene_to_camera,
                apply_distortion=apply_distortion,
            )
            color = _rgb(class_color(cuboid.class_name))
            for a, b in BOX_EDGES:
                if valid[a] and valid[b]:
                    draw.line([tuple(pixels[a]), tuple(pixels[b])], fill=color, width=3)
    overlay_count = None
    if overlay_lidar and path and path.exists():
        lidar_sensor, lidar_path = overlay_lidar
        overlay_count = _draw_lidar_overlay(
            variant,
            frame,
            image,
            sensor,
            lidar_sensor,
            lidar_path,
            apply_distortion=apply_distortion,
        )
    image.thumbnail(size, Image.Resampling.BILINEAR)
    label = sensor.sensor_id
    if overlay_lidar:
        count_text = "no pts" if not overlay_count else f"{overlay_count} pts"
        label = f"{label} + {overlay_lidar[0].sensor_id} ({count_text})"
    return _letterbox(image, size, label)


def render_lidar_topdown(
    variant: RealSimVariant,
    frame: FrameData,
    sensor: Sensor,
    path: Path | None,
    size: tuple[int, int] = TILE_SIZE,
) -> Image.Image:
    image = _blank("", (24, 28, 34), size)
    draw = ImageDraw.Draw(image)
    draw.text((10, 8), f"{sensor.sensor_id} top-down", fill=(220, 224, 230))
    if not path or not path.exists() or _pcd_has_no_points(path):
        draw.text((10, 32), "missing / empty PCD", fill=(150, 156, 166))
        return image

    points = _read_ascii_pcd_xyz(str(path), max_points=90000)
    if points.size == 0:
        draw.text((10, 32), "no drawable points", fill=(150, 156, 166))
        return image

    width, height = size
    x = points[:, 0]
    y = points[:, 1]
    if len(points) > 20:
        xmin, xmax = np.percentile(x, [1, 99])
        ymin, ymax = np.percentile(y, [1, 99])
    else:
        xmin, xmax = float(np.min(x)), float(np.max(x))
        ymin, ymax = float(np.min(y)), float(np.max(y))
    span = max(float(xmax - xmin), float(ymax - ymin), 1.0)
    cx = (float(xmin) + float(xmax)) / 2.0
    cy = (float(ymin) + float(ymax)) / 2.0
    pad = span * 0.08
    xmin, xmax = cx - span / 2.0 - pad, cx + span / 2.0 + pad
    ymin, ymax = cy - span / 2.0 - pad, cy + span / 2.0 + pad

    valid = (x >= xmin) & (x <= xmax) & (y >= ymin) & (y <= ymax)
    x = x[valid]
    y = y[valid]
    px = ((x - xmin) / max(xmax - xmin, 1e-6) * (width - 1)).astype(int)
    py = ((ymax - y) / max(ymax - ymin, 1e-6) * (height - 1)).astype(int)

    pix = image.load()
    for ix, iy in zip(px[:: max(1, len(px) // 18000)], py[:: max(1, len(py) // 18000)]):
        pix[int(ix), int(iy)] = (95, 185, 210)
    if xmin <= 0.0 <= xmax and ymin <= 0.0 <= ymax:
        ox = int((0.0 - xmin) / max(xmax - xmin, 1e-6) * (width - 1))
        oy = int((ymax - 0.0) / max(ymax - ymin, 1e-6) * (height - 1))
        draw.line([(ox, 0), (ox, height)], fill=(60, 65, 74))
        draw.line([(0, oy), (width, oy)], fill=(60, 65, 74))
        draw.ellipse((ox - 4, oy - 4, ox + 4, oy + 4), fill=(238, 178, 55))
    return image


def render_message_tile(text: str, size: tuple[int, int] = TILE_SIZE) -> Image.Image:
    return _blank(text, (22, 25, 31), size)


def _draw_lidar_overlay(
    variant: RealSimVariant,
    frame: FrameData,
    image: Image.Image,
    camera: Sensor,
    lidar: Sensor,
    lidar_path: Path | None,
    apply_distortion: bool = False,
) -> int:
    if not lidar_path or not lidar_path.exists() or _pcd_has_no_points(lidar_path):
        return 0
    points_lidar = _read_ascii_pcd_xyz(str(lidar_path), max_points=90000)
    if points_lidar.size == 0:
        return 0

    lidar_to_scene = variant.point_cloud_to_scene(frame, lidar.stream_id)
    scene_to_camera = variant.scene_to_sensor(frame, camera.stream_id)
    points_scene = transform_points(lidar_to_scene, points_lidar)
    points_cam = transform_points(scene_to_camera, points_scene)

    depth = points_cam[:, 0]
    valid_depth = (depth > 0.5) & (depth < 120.0)
    if not np.any(valid_depth):
        return 0

    points_scene = points_scene[valid_depth]
    depths = depth[valid_depth]
    pixels, valid = project_points(camera, points_scene, scene_to_camera, apply_distortion=apply_distortion)
    if not np.any(valid):
        return 0

    draw = ImageDraw.Draw(image)
    pixels = pixels[valid]
    depths = depths[valid]
    projected_count = len(pixels)
    stride = max(1, len(pixels) // 9000)
    pixels = pixels[::stride]
    depths = depths[::stride]
    dmin = float(np.percentile(depths, 5))
    dmax = float(np.percentile(depths, 95))
    span = max(dmax - dmin, 1e-6)
    for (x, y), depth in zip(pixels, depths):
        t = max(0.0, min(1.0, (float(depth) - dmin) / span))
        color = (int(255 * (1.0 - t)), int(255 * (1.0 - abs(t - 0.35))), int(255 * t))
        draw.ellipse((x - 3.5, y - 3.5, x + 3.5, y + 3.5), fill=color)
    return projected_count


def pil_to_o3d_image(image: Image.Image):
    import open3d as o3d

    return o3d.geometry.Image(np.asarray(image.convert("RGB")))


def _blank(text: str, color: tuple[int, int, int], size: tuple[int, int] = TILE_SIZE) -> Image.Image:
    image = Image.new("RGB", size, color)
    if text:
        draw = ImageDraw.Draw(image)
        for i, line in enumerate(text.splitlines()):
            draw.text((14, 18 + i * 18), line, fill=(225, 229, 235), font=ImageFont.load_default())
    return image


def _letterbox(image: Image.Image, size: tuple[int, int], label: str) -> Image.Image:
    canvas = Image.new("RGB", size, (22, 25, 31))
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, size[0], 24), fill=(12, 15, 20))
    draw.text((8, 6), label, fill=(232, 236, 241), font=ImageFont.load_default())
    return canvas


def _rgb(color: tuple[float, float, float]) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * 255))) for c in color)


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


@lru_cache(maxsize=64)
def _read_ascii_pcd_xyz(path: str, max_points: int) -> np.ndarray:
    points = []
    in_data = False
    try:
        with Path(path).open("r", encoding="ascii", errors="ignore") as handle:
            for line in handle:
                if not in_data:
                    in_data = line.strip().lower() == "data ascii"
                    continue
                parts = line.split()
                if len(parts) < 3:
                    continue
                try:
                    points.append((float(parts[0]), float(parts[1]), float(parts[2])))
                except ValueError:
                    continue
    except OSError:
        return np.empty((0, 3), dtype=float)
    if not points:
        return np.empty((0, 3), dtype=float)
    if len(points) > max_points:
        step = int(np.ceil(len(points) / max_points))
        points = points[::step]
    return np.asarray(points, dtype=float)
