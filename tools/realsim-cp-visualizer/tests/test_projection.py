from pathlib import Path

import numpy as np

from realsim_viz.loader import RealSimVariant
from realsim_viz.panels import panel_data, render_camera_tile, render_lidar_topdown
from realsim_viz.projection import cuboid_corners, project_points


ROOT = Path(__file__).resolve().parents[2]


def test_loader_reads_night_1():
    variant = RealSimVariant(ROOT / "dataset" / "daiba_station_scenario" / "night_1")
    assert len(variant) == 101
    assert "vehicle_10000" in variant.agent_ids
    assert variant.sensors_for_agent("vehicle_10000", "camera")


def test_cuboid_corners_are_finite():
    variant = RealSimVariant(ROOT / "dataset" / "daiba_station_scenario" / "night_1")
    frame = variant.frame(0)
    corners = cuboid_corners(frame.cuboids[0])
    assert corners.shape == (8, 3)
    assert np.isfinite(corners).all()


def test_projection_returns_pixels_and_mask():
    variant = RealSimVariant(ROOT / "dataset" / "daiba_station_scenario" / "night_1")
    frame = variant.frame(0)
    sensor = variant.sensor("vehicle_10000/camera_9")
    pixels, valid = project_points(sensor, cuboid_corners(frame.cuboids[0]), variant.scene_to_sensor(frame, sensor.stream_id))
    assert pixels.shape == (8, 2)
    assert valid.shape == (8,)
    assert np.isfinite(pixels).all()


def test_agent_panel_renders_tiles():
    variant = RealSimVariant(ROOT / "dataset" / "daiba_station_scenario" / "night_1")
    frame = variant.frame(10)
    data = panel_data(variant, frame, "vehicle_10000")
    camera = render_camera_tile(variant, frame, data.cameras[0][0], data.cameras[0][1])
    lidar = render_lidar_topdown(variant, frame, data.lidars[0][0], data.lidars[0][1])
    assert camera.size == (360, 230)
    assert lidar.size == (360, 230)


def test_camera_tile_renders_lidar_overlay():
    variant = RealSimVariant(ROOT / "dataset" / "daiba_station_scenario" / "night_1")
    frame = variant.frame(10)
    camera = variant.sensor("vehicle_10000/camera_9")
    lidar = variant.sensor("vehicle_10000/lidar_5")
    tile = render_camera_tile(
        variant,
        frame,
        camera,
        frame.streams[camera.stream_id],
        overlay_lidar=(lidar, frame.streams[lidar.stream_id]),
    )
    assert tile.size == (360, 230)


def test_lidar_projection_uses_realsim_camera_image_axes():
    variant = RealSimVariant(ROOT / "dataset" / "daiba_station_scenario" / "night_1")
    frame = variant.frame(10)
    camera = variant.sensor("vehicle_10000/camera_9")
    lidar = variant.sensor("vehicle_10000/lidar_5")

    from realsim_viz.panels import _read_ascii_pcd_xyz
    from realsim_viz.transforms import transform_points

    points_lidar = _read_ascii_pcd_xyz(str(frame.streams[lidar.stream_id]), 30000)
    points_scene = transform_points(variant.point_cloud_to_scene(frame, lidar.stream_id), points_lidar)
    _pixels, valid = project_points(camera, points_scene, variant.scene_to_sensor(frame, camera.stream_id))
    assert valid.sum() > 1000
