"""Stable color palettes for agents and object classes."""

from __future__ import annotations

import hashlib

AGENT_PALETTE = [
    (0.000, 0.447, 0.698),
    (0.902, 0.624, 0.000),
    (0.000, 0.620, 0.451),
    (0.835, 0.369, 0.000),
    (0.800, 0.475, 0.655),
    (0.941, 0.894, 0.259),
    (0.337, 0.706, 0.914),
    (0.000, 0.000, 0.000),
]

CLASS_COLORS = {
    "TYPE_PEDESTRIAN": (0.937, 0.231, 0.172),
    "TYPE_SMALL_CAR": (0.122, 0.467, 0.706),
    "TYPE_COMPACT_CAR": (0.172, 0.627, 0.172),
    "TYPE_MEDIUM_CAR": (1.000, 0.498, 0.055),
    "TYPE_LUXURY_CAR": (0.580, 0.404, 0.741),
    "TYPE_BUS": (0.549, 0.337, 0.294),
}


def _stable_index(key: str, modulo: int) -> int:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def agent_color(agent_id: str) -> tuple[float, float, float]:
    return AGENT_PALETTE[_stable_index(agent_id, len(AGENT_PALETTE))]


def class_color(class_name: str) -> tuple[float, float, float]:
    return CLASS_COLORS.get(class_name, (0.55, 0.55, 0.55))
