"""Cuboid corner generation and camera projection."""

from __future__ import annotations

import numpy as np

from .loader import Cuboid, Sensor
from .transforms import make_transform, transform_points

BOX_EDGES = (
    (0, 1), (1, 3), (3, 2), (2, 0),
    (4, 5), (5, 7), (7, 6), (6, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)


def cuboid_corners(cuboid: Cuboid) -> np.ndarray:
    length, width, height = cuboid.extent
    x = length / 2.0
    y = width / 2.0
    z = height / 2.0
    local = np.array(
        [
            [-x, -y, -z], [x, -y, -z], [-x, y, -z], [x, y, -z],
            [-x, -y, z], [x, -y, z], [-x, y, z], [x, y, z],
        ],
        dtype=float,
    )
    tf = make_transform(cuboid.quaternion, cuboid.center)
    return transform_points(tf, local)


def project_points(
    sensor: Sensor,
    points_scene: np.ndarray,
    scene_to_camera: np.ndarray,
    apply_distortion: bool = True,
    convention: str = "realsim",
) -> tuple[np.ndarray, np.ndarray]:
    camera_points = transform_points(scene_to_camera, points_scene)
    if convention == "opencv":
        depth = camera_points[:, 2]
        horizontal = camera_points[:, 0]
        vertical = camera_points[:, 1]
    else:
        # RealSim camera frames follow an automotive convention: +X forward,
        # +Y points toward image-left, +Z up. Convert that to pinhole image
        # coordinates where pixel x grows to image-right.
        depth = camera_points[:, 0]
        horizontal = -camera_points[:, 1]
        vertical = -camera_points[:, 2]
    valid = depth > 1e-6

    x = horizontal / np.where(valid, depth, 1.0)
    y = vertical / np.where(valid, depth, 1.0)

    if apply_distortion:
        k1 = sensor.intrinsics.get("k1", 0.0)
        k2 = sensor.intrinsics.get("k2", 0.0)
        k3 = sensor.intrinsics.get("k3", 0.0)
        k4 = sensor.intrinsics.get("k4", 0.0)
        k5 = sensor.intrinsics.get("k5", 0.0)
        k6 = sensor.intrinsics.get("k6", 0.0)
        r2 = x * x + y * y
        numerator = 1.0 + k1 * r2 + k2 * r2**2 + k3 * r2**3
        denominator = 1.0 + k4 * r2 + k5 * r2**2 + k6 * r2**3
        scale = numerator / np.where(np.abs(denominator) > 1e-9, denominator, 1.0)
        x = x * scale
        y = y * scale

    fx = sensor.intrinsics.get("fx", 1.0)
    fy = sensor.intrinsics.get("fy", 1.0)
    cx = sensor.intrinsics.get("cx", 0.0)
    cy = sensor.intrinsics.get("cy", 0.0)
    pixels = np.c_[fx * x + cx, fy * y + cy]

    if sensor.width and sensor.height:
        valid &= (pixels[:, 0] >= 0) & (pixels[:, 0] < sensor.width)
        valid &= (pixels[:, 1] >= 0) & (pixels[:, 1] < sensor.height)
    return pixels, valid
