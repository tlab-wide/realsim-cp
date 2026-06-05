"""Transform helpers for OpenLABEL xyzw quaternions."""

from __future__ import annotations

import numpy as np


def quat_xyzw_to_matrix(q: list[float] | tuple[float, float, float, float]) -> np.ndarray:
    x, y, z, w = [float(v) for v in q]
    n = x * x + y * y + z * z + w * w
    if n < 1e-12:
        return np.eye(3)
    s = 2.0 / n
    xx, yy, zz = x * x * s, y * y * s, z * z * s
    xy, xz, yz = x * y * s, x * z * s, y * z * s
    wx, wy, wz = w * x * s, w * y * s, w * z * s
    return np.array(
        [
            [1.0 - yy - zz, xy - wz, xz + wy],
            [xy + wz, 1.0 - xx - zz, yz - wx],
            [xz - wy, yz + wx, 1.0 - xx - yy],
        ],
        dtype=float,
    )


def make_transform(
    quaternion_xyzw: list[float] | tuple[float, float, float, float],
    translation: list[float] | tuple[float, float, float],
) -> np.ndarray:
    matrix = np.eye(4, dtype=float)
    matrix[:3, :3] = quat_xyzw_to_matrix(quaternion_xyzw)
    matrix[:3, 3] = np.asarray(translation, dtype=float)
    return matrix


def invert_transform(matrix: np.ndarray) -> np.ndarray:
    inv = np.eye(4, dtype=float)
    rot = matrix[:3, :3]
    trans = matrix[:3, 3]
    inv[:3, :3] = rot.T
    inv[:3, 3] = -(rot.T @ trans)
    return inv


def transform_points(matrix: np.ndarray, points: np.ndarray) -> np.ndarray:
    if points.size == 0:
        return points.reshape((-1, 3))
    hom = np.c_[points[:, :3], np.ones(len(points))]
    return (matrix @ hom.T).T[:, :3]


def pose_from_openlabel(pose: dict | None) -> np.ndarray:
    if not pose:
        return np.eye(4)
    return make_transform(pose.get("quaternion", [0, 0, 0, 1]), pose.get("translation", [0, 0, 0]))
