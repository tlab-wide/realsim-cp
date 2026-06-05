"""Open3D GUI application for RealSim-CP."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .loader import RealSimVariant
from .panels import panel_data, pil_to_o3d_image, render_camera_tile, render_lidar_topdown, render_message_tile
from .playback import Playback
from .scene_3d import Open3DSceneBuilder, SceneLayers


class RealSimOpen3DApp:
    def __init__(self, variant_path: str | Path):
        self.variant = RealSimVariant(variant_path)
        self.playback = Playback(len(self.variant))
        self.rsu_agent_ids = [agent_id for agent_id in self.variant.agent_ids if agent_id.startswith("rsu_")]
        self.vehicle_agent_ids = [agent_id for agent_id in self.variant.agent_ids if agent_id.startswith("vehicle_")]
        self.visible_agents = self._initial_visible_agents()
        self.dashboard_agent = self._first_visible_agent_with_camera() or self._first_agent_with_camera() or self.variant.agent_ids[0]
        self.dashboard_tiles = []
        self.overlay_lidar_on_camera = True
        self.apply_camera_distortion = False
        self.overlay_lidar_stream = None
        self.max_tile_index = 0
        self.view_preset = "3d"
        self.layers = SceneLayers()
        self.builder = Open3DSceneBuilder(self.variant)
        self.o3d = self.builder.o3d

        gui = self.o3d.visualization.gui
        rendering = self.o3d.visualization.rendering
        self.gui = gui
        self.rendering = rendering
        self.app = gui.Application.instance
        self.app.initialize()
        self.window = self.app.create_window("RealSim-CP Visualizer", 1440, 900)
        self.scene_widget = gui.SceneWidget()
        self.scene_widget.scene = rendering.Open3DScene(self.window.renderer)
        self.scene_widget.scene.set_background([0.035, 0.039, 0.047, 1.0])
        self.window.add_child(self.scene_widget)
        self.status = None
        self.data_info = self._dataset_summary()
        self.agent_checks = {}
        self.rsu_group_check = None
        self.vehicle_group_check = None
        self._updating_agent_checks = False
        self.dashboard_images = []
        self._build_panel()
        self._build_dashboard()
        self.window.set_on_layout(self._on_layout)
        self.window.set_on_key(self._on_key)
        self.window.set_on_tick_event(self._on_tick)
        self._refresh_scene(reset_camera=True)

    def _initial_visible_agents(self) -> set[str]:
        visible = set()
        if self.vehicle_agent_ids:
            visible.add(self.vehicle_agent_ids[0])
        if self.rsu_agent_ids:
            visible.add(self.rsu_agent_ids[0])
        if not visible and self.variant.agent_ids:
            visible.add(self.variant.agent_ids[0])
        return visible

    def _first_agent_with_camera(self) -> str | None:
        for agent_id in self.variant.agent_ids:
            if self.variant.sensors_for_agent(agent_id, "camera"):
                return agent_id
        return None

    def _first_visible_agent_with_camera(self) -> str | None:
        for agent_id in self.variant.agent_ids:
            if agent_id in self.visible_agents and self.variant.sensors_for_agent(agent_id, "camera"):
                return agent_id
        return None

    def _build_panel(self) -> None:
        gui = self.gui
        em = self.window.theme.font_size
        self.panel = gui.Vert(0.4 * em, gui.Margins(em, em, em, em))

        title = gui.Label("RealSim-CP")
        self.panel.add_child(title)
        self.status = gui.Label("")
        self.panel.add_child(self.status)
        info = gui.CollapsableVert("Loaded data", 0.25 * em, gui.Margins(0, 0, 0, 0))
        info.add_child(gui.Label(self.data_info))
        self.panel.add_child(info)

        row = gui.Horiz(0.25 * em)
        play = gui.Button("Play / Pause")
        play.set_on_clicked(self._toggle_play)
        prev = gui.Button("<")
        prev.set_on_clicked(lambda: self._step(-1))
        nxt = gui.Button(">")
        nxt.set_on_clicked(lambda: self._step(1))
        row.add_child(prev)
        row.add_child(play)
        row.add_child(nxt)
        self.panel.add_child(row)

        self.frame_slider = gui.Slider(gui.Slider.INT)
        self.frame_slider.set_limits(0, max(0, len(self.variant) - 1))
        self.frame_slider.set_on_value_changed(lambda value: self._set_frame(int(value)))
        self.panel.add_child(self.frame_slider)

        view_row = gui.Horiz(0.25 * em)
        top_view = gui.Button("Top")
        top_view.set_on_clicked(lambda: self._set_view_preset("top"))
        side_view = gui.Button("Side")
        side_view.set_on_clicked(lambda: self._set_view_preset("side"))
        three_d_view = gui.Button("3D")
        three_d_view.set_on_clicked(lambda: self._set_view_preset("3d"))
        view_row.add_child(top_view)
        view_row.add_child(side_view)
        view_row.add_child(three_d_view)
        self.panel.add_child(view_row)

        speed_row = gui.Horiz(0.25 * em)
        speed_row.add_child(gui.Label("Speed"))
        self.speed = gui.Combobox()
        for item in ("0.25x", "0.5x", "1.0x", "2.0x", "4.0x"):
            self.speed.add_item(item)
        self.speed.selected_text = "1.0x"
        self.speed.set_on_selection_changed(lambda text, _idx: self._set_speed(text))
        speed_row.add_child(self.speed)
        self.panel.add_child(speed_row)

        self.panel.add_child(gui.Label("Layers"))
        for label, attr in (
            ("LiDAR", "point_clouds"),
            ("Cuboids", "cuboids"),
            ("Agents", "agents"),
            ("Grid", "grid"),
            ("Frustums", "frustums"),
            ("Trajectories", "trajectories"),
        ):
            cb = gui.Checkbox(label)
            cb.checked = getattr(self.layers, attr)
            cb.set_on_checked(lambda checked, a=attr: self._set_layer(a, checked))
            self.panel.add_child(cb)

        self.panel.add_child(gui.Label("Agents"))
        agent_list = gui.CollapsableVert("Visible agents", 0.25 * em, gui.Margins(0, 0, 0, 0))

        self.rsu_group_check = gui.Checkbox("All RSUs")
        self.rsu_group_check.checked = self._all_agents_visible(self.rsu_agent_ids)
        self.rsu_group_check.set_on_checked(lambda checked: self._set_agent_group(self.rsu_agent_ids, checked))
        agent_list.add_child(self.rsu_group_check)

        self.vehicle_group_check = gui.Checkbox("All vehicles")
        self.vehicle_group_check.checked = self._all_agents_visible(self.vehicle_agent_ids)
        self.vehicle_group_check.set_on_checked(lambda checked: self._set_agent_group(self.vehicle_agent_ids, checked))
        agent_list.add_child(self.vehicle_group_check)

        for agent_id in self.variant.agent_ids:
            cb = gui.Checkbox(agent_id)
            cb.checked = agent_id in self.visible_agents
            cb.set_on_checked(lambda checked, a=agent_id: self._set_agent(a, checked))
            self.agent_checks[agent_id] = cb
            agent_list.add_child(cb)
        self.panel.add_child(agent_list)

        self.window.add_child(self.panel)

    def _build_dashboard(self) -> None:
        gui = self.gui
        em = self.window.theme.font_size
        self.dashboard = gui.Vert(0.45 * em, gui.Margins(em, em, em, em))
        self.dashboard.add_child(gui.Label("Agent dashboard"))

        self.agent_combo = gui.Combobox()
        for agent_id in self.variant.agent_ids:
            if self.variant.sensors_for_agent(agent_id, "camera") or self.variant.sensors_for_agent(agent_id, "lidar"):
                self.agent_combo.add_item(agent_id)
        self.agent_combo.selected_text = self.dashboard_agent
        self.agent_combo.set_on_selection_changed(lambda text, _idx: self._set_dashboard_agent(text))
        self.dashboard.add_child(self.agent_combo)

        self.camera_combo = gui.Combobox()
        self.lidar_combo = gui.Combobox()
        self.overlay_lidar_combo = gui.Combobox()
        self._populate_sensor_combos()

        self.dashboard.add_child(gui.Label("Camera"))
        self.dashboard.add_child(self.camera_combo)
        camera_buttons = gui.Horiz(0.25 * em)
        add_camera = gui.Button("Add camera")
        add_camera.set_on_clicked(self._add_camera_tile)
        camera_buttons.add_child(add_camera)
        self.overlay_check = gui.Checkbox("Overlay LiDAR")
        self.overlay_check.checked = self.overlay_lidar_on_camera
        self.overlay_check.set_on_checked(self._set_lidar_overlay)
        camera_buttons.add_child(self.overlay_check)
        self.distortion_check = gui.Checkbox("Distortion")
        self.distortion_check.checked = self.apply_camera_distortion
        self.distortion_check.set_on_checked(self._set_camera_distortion)
        camera_buttons.add_child(self.distortion_check)
        self.dashboard.add_child(camera_buttons)

        self.dashboard.add_child(gui.Label("LiDAR"))
        self.dashboard.add_child(self.lidar_combo)
        lidar_buttons = gui.Horiz(0.25 * em)
        add_lidar = gui.Button("Add lidar")
        add_lidar.set_on_clicked(self._add_lidar_tile)
        remove_last = gui.Button("Remove last")
        remove_last.set_on_clicked(self._remove_last_tile)
        clear = gui.Button("Clear")
        clear.set_on_clicked(self._clear_tiles)
        lidar_buttons.add_child(add_lidar)
        lidar_buttons.add_child(remove_last)
        lidar_buttons.add_child(clear)
        self.dashboard.add_child(lidar_buttons)

        self.dashboard.add_child(gui.Label("LiDAR overlay source"))
        self.overlay_lidar_combo.set_on_selection_changed(lambda text, _idx: self._set_overlay_source(text))
        self.dashboard.add_child(self.overlay_lidar_combo)

        self.dashboard.add_child(gui.Label("Tile actions"))
        self.tile_combo = gui.Combobox()
        self.tile_combo.set_on_selection_changed(lambda _text, idx: self._set_max_tile_index(idx))
        self.dashboard.add_child(self.tile_combo)
        tile_buttons = gui.Horiz(0.25 * em)
        maximize = gui.Button("Maximize")
        maximize.set_on_clicked(self._maximize_selected_tile)
        tile_buttons.add_child(maximize)
        self.dashboard.add_child(tile_buttons)

        self.dashboard_status = gui.Label("")
        self.dashboard.add_child(self.dashboard_status)

        self.tile_area = gui.ScrollableVert()
        for _ in range(6):
            widget = gui.ImageWidget(pil_to_o3d_image(render_message_tile("")))
            self.dashboard_images.append(widget)
            self.tile_area.add_child(widget)
        self.dashboard.add_child(self.tile_area)
        self.window.add_child(self.dashboard)
        self._seed_dashboard_tiles()

    def _dataset_summary(self) -> str:
        camera_streams = [s for s in self.variant.streams.values() if s.kind == "camera"]
        lidar_streams = [s for s in self.variant.streams.values() if s.kind == "lidar"]
        image_refs = 0
        image_files = 0
        lidar_refs = 0
        lidar_files = 0
        object_ids = set()
        class_counts = {}
        for index in range(len(self.variant)):
            frame = self.variant.frame(index)
            object_ids.update(c.object_id for c in frame.cuboids)
            for cuboid in frame.cuboids:
                class_counts[cuboid.class_name] = class_counts.get(cuboid.class_name, 0) + 1
            for stream_id, path in frame.streams.items():
                sensor = self.variant.streams.get(stream_id)
                if not sensor:
                    continue
                if sensor.kind == "camera":
                    image_refs += 1
                    image_files += int(path.exists())
                elif sensor.kind == "lidar":
                    lidar_refs += 1
                    lidar_files += int(path.exists())
        classes = ", ".join(f"{k.replace('TYPE_', '')}:{v}" for k, v in sorted(class_counts.items()))
        return (
            f"Variant: {self.variant.root.name}\n"
            f"Frames: {len(self.variant)}\n"
            f"Agents: {len(self.variant.agent_ids)}\n"
            f"Cameras: {len(camera_streams)} streams, {image_files}/{image_refs} images\n"
            f"LiDARs: {len(lidar_streams)} streams, {lidar_files}/{lidar_refs} PCDs\n"
            f"Objects: {len(object_ids)} unique\n"
            f"Classes: {classes}"
        )

    def _on_layout(self, ctx) -> None:
        r = self.window.content_rect
        panel_width = 310
        dash_width = 410
        self.panel.frame = self.gui.Rect(r.x, r.y, panel_width, r.height)
        self.dashboard.frame = self.gui.Rect(r.get_right() - dash_width, r.y, dash_width, r.height)
        self.scene_widget.frame = self.gui.Rect(
            r.x + panel_width,
            r.y,
            max(100, r.width - panel_width - dash_width),
            r.height,
        )

    def _on_key(self, event) -> bool:
        if event.type != self.gui.KeyEvent.DOWN:
            return False
        if event.key == self.gui.KeyName.SPACE:
            self._toggle_play()
            return True
        if event.key == self.gui.KeyName.RIGHT:
            self._step(1)
            return True
        if event.key == self.gui.KeyName.LEFT:
            self._step(-1)
            return True
        return False

    def _on_tick(self) -> bool:
        if self.playback.tick():
            self._refresh_scene()
            return True
        return False

    def _toggle_play(self) -> None:
        self.playback.toggle()
        self._update_status()

    def _step(self, delta: int) -> None:
        self.playback.step(delta)
        self._refresh_scene()

    def _set_frame(self, index: int) -> None:
        if index != self.playback.index:
            self.playback.set_index(index)
            self._refresh_scene()

    def _set_speed(self, text: str) -> None:
        self.playback.speed = float(text.rstrip("x"))

    def _set_layer(self, attr: str, checked: bool) -> None:
        setattr(self.layers, attr, checked)
        self._refresh_scene()

    def _set_agent(self, agent_id: str, checked: bool) -> None:
        if self._updating_agent_checks:
            return
        if checked:
            self.visible_agents.add(agent_id)
        else:
            self.visible_agents.discard(agent_id)
        self._sync_agent_group_checks()
        self._refresh_scene()

    def _set_agent_group(self, agent_ids: list[str], checked: bool) -> None:
        if self._updating_agent_checks:
            return
        for agent_id in agent_ids:
            if checked:
                self.visible_agents.add(agent_id)
            else:
                self.visible_agents.discard(agent_id)

        self._updating_agent_checks = True
        try:
            for agent_id in agent_ids:
                cb = self.agent_checks.get(agent_id)
                if cb is not None:
                    cb.checked = checked
            self._sync_agent_group_checks()
        finally:
            self._updating_agent_checks = False

        self._refresh_scene()

    def _all_agents_visible(self, agent_ids: list[str]) -> bool:
        return bool(agent_ids) and all(agent_id in self.visible_agents for agent_id in agent_ids)

    def _sync_agent_group_checks(self) -> None:
        self._updating_agent_checks = True
        try:
            if self.rsu_group_check is not None:
                self.rsu_group_check.checked = self._all_agents_visible(self.rsu_agent_ids)
            if self.vehicle_group_check is not None:
                self.vehicle_group_check.checked = self._all_agents_visible(self.vehicle_agent_ids)
        finally:
            self._updating_agent_checks = False

    def _set_dashboard_agent(self, agent_id: str) -> None:
        self.dashboard_agent = agent_id
        self._populate_sensor_combos()
        self._refresh_dashboard()

    def _populate_sensor_combos(self) -> None:
        cameras = self.variant.sensors_for_agent(self.dashboard_agent, "camera")
        lidars = self.variant.sensors_for_agent(self.dashboard_agent, "lidar")

        self.camera_combo.clear_items()
        for sensor in cameras:
            self.camera_combo.add_item(sensor.stream_id)
        if cameras:
            self.camera_combo.selected_text = cameras[0].stream_id

        self.lidar_combo.clear_items()
        self.overlay_lidar_combo.clear_items()
        for sensor in lidars:
            self.lidar_combo.add_item(sensor.stream_id)
            self.overlay_lidar_combo.add_item(sensor.stream_id)
        if lidars:
            lidar_ids = {sensor.stream_id for sensor in lidars}
            if self.overlay_lidar_stream not in lidar_ids:
                self.overlay_lidar_stream = lidars[0].stream_id
            self.lidar_combo.selected_text = lidars[0].stream_id
            self.overlay_lidar_combo.selected_text = self.overlay_lidar_stream
        else:
            self.overlay_lidar_stream = None

    def _seed_dashboard_tiles(self) -> None:
        cameras = self.variant.sensors_for_agent(self.dashboard_agent, "camera")
        lidars = self.variant.sensors_for_agent(self.dashboard_agent, "lidar")
        if cameras:
            self.dashboard_tiles.append(("camera", cameras[0].stream_id))
        if lidars:
            self.dashboard_tiles.append(("lidar", lidars[0].stream_id))

    def _add_camera_tile(self) -> None:
        if self.camera_combo.number_of_items == 0:
            return
        self._add_tile("camera", self.camera_combo.selected_text)

    def _add_lidar_tile(self) -> None:
        if self.lidar_combo.number_of_items == 0:
            return
        self._add_tile("lidar", self.lidar_combo.selected_text)

    def _add_tile(self, kind: str, stream_id: str) -> None:
        if len(self.dashboard_tiles) >= len(self.dashboard_images):
            self.dashboard_tiles.pop(0)
        self.dashboard_tiles.append((kind, stream_id))
        self.max_tile_index = len(self.dashboard_tiles) - 1
        self._refresh_dashboard()

    def _remove_last_tile(self) -> None:
        if self.dashboard_tiles:
            self.dashboard_tiles.pop()
            self.max_tile_index = max(0, min(self.max_tile_index, len(self.dashboard_tiles) - 1))
        self._refresh_dashboard()

    def _clear_tiles(self) -> None:
        self.dashboard_tiles.clear()
        self.max_tile_index = 0
        self._refresh_dashboard()

    def _set_lidar_overlay(self, checked: bool) -> None:
        self.overlay_lidar_on_camera = checked
        self._refresh_dashboard()

    def _set_camera_distortion(self, checked: bool) -> None:
        self.apply_camera_distortion = checked
        self._refresh_dashboard()

    def _set_overlay_source(self, stream_id: str) -> None:
        self.overlay_lidar_stream = stream_id
        self._refresh_dashboard()

    def _set_max_tile_index(self, index: int) -> None:
        self.max_tile_index = max(0, index)

    def _set_view_preset(self, preset: str) -> None:
        self.view_preset = preset
        self._apply_view_preset()

    def _apply_view_preset(self) -> None:
        bounds = self.scene_widget.scene.bounding_box
        center = np.asarray(bounds.get_center(), dtype=float)
        extent = np.asarray(bounds.get_extent(), dtype=float)
        distance = max(float(np.max(extent)) * 1.35, 25.0)

        if self.view_preset == "top":
            eye = center + np.array([0.0, 0.0, distance])
            up = np.array([0.0, 1.0, 0.0])
        elif self.view_preset == "side":
            eye = center + np.array([0.0, -distance, 0.0])
            up = np.array([0.0, 0.0, 1.0])
        else:
            eye = center + np.array([-distance, -distance, distance * 0.65])
            up = np.array([0.0, 0.0, 1.0])

        self.scene_widget.setup_camera(60.0, bounds, center)
        if hasattr(self.scene_widget, "look_at"):
            self.scene_widget.look_at(center, eye, up)
        else:
            self.scene_widget.scene.camera.look_at(center, eye, up)

    def _refresh_scene(self, reset_camera: bool = False) -> None:
        frame = self.variant.frame(self.playback.index)
        self.scene_widget.scene.clear_geometry()
        for i, geometry in enumerate(self.builder.build(frame, self.visible_agents, self.layers)):
            self.scene_widget.scene.add_geometry(f"g{i}", geometry, self.rendering.MaterialRecord())
        if reset_camera:
            self._apply_view_preset()
        self.frame_slider.int_value = self.playback.index
        self._update_status(frame)
        self._refresh_dashboard(frame)

    def _refresh_dashboard(self, frame=None) -> None:
        frame = frame or self.variant.frame(self.playback.index)
        data = panel_data(self.variant, frame, self.dashboard_agent)
        selected_count = len(self.dashboard_tiles)
        self.dashboard_status.text = (
            f"{len(data.cameras)} cameras | {len(data.lidars)} lidar | "
            f"{selected_count} tiles | t={frame.timestamp:.1f}s"
        )

        images = []
        for kind, stream_id in self.dashboard_tiles:
            images.append(self._render_tile_image(frame, kind, stream_id))
        while len(images) < len(self.dashboard_images):
            images.append(render_message_tile(""))
        for widget, image in zip(self.dashboard_images, images[: len(self.dashboard_images)]):
            widget.update_image(pil_to_o3d_image(image))
        self._refresh_tile_selector()

    def _refresh_tile_selector(self) -> None:
        self.tile_combo.clear_items()
        for i, (kind, stream_id) in enumerate(self.dashboard_tiles):
            self.tile_combo.add_item(f"{i + 1}. {kind} {stream_id}")
        if self.dashboard_tiles:
            self.max_tile_index = min(self.max_tile_index, len(self.dashboard_tiles) - 1)
            self.tile_combo.selected_index = self.max_tile_index

    def _render_tile_image(self, frame, kind: str, stream_id: str, size=(360, 230)):
        sensor = self.variant.streams.get(stream_id)
        if not sensor:
            return render_message_tile(f"Unknown sensor\n{stream_id}", size)
        path = frame.streams.get(stream_id)
        path = path if path and path.exists() else None
        if kind == "camera":
            return render_camera_tile(
                self.variant,
                frame,
                sensor,
                path,
                draw_cuboids=self.layers.cuboids,
                overlay_lidar=self._overlay_lidar(frame, sensor),
                apply_distortion=self.apply_camera_distortion,
                size=size,
            )
        if kind == "lidar":
            return render_lidar_topdown(self.variant, frame, sensor, path, size=size)
        return render_message_tile(f"Unsupported tile\n{kind}", size)

    def _maximize_selected_tile(self) -> None:
        if not self.dashboard_tiles:
            return
        frame = self.variant.frame(self.playback.index)
        kind, stream_id = self.dashboard_tiles[min(self.max_tile_index, len(self.dashboard_tiles) - 1)]
        dialog = self.gui.Dialog(f"{kind}: {stream_id}")
        layout = self.gui.Vert(0.5 * self.window.theme.font_size, self.gui.Margins(12, 12, 12, 12))
        image = self._render_tile_image(frame, kind, stream_id, size=(980, 640))
        layout.add_child(self.gui.ImageWidget(pil_to_o3d_image(image)))
        close = self.gui.Button("Close")
        close.set_on_clicked(self.window.close_dialog)
        layout.add_child(close)
        dialog.add_child(layout)
        self.window.show_dialog(dialog)

    def _overlay_lidar(self, frame, camera_sensor):
        if not self.overlay_lidar_on_camera:
            return None
        stream_id = self.overlay_lidar_stream
        lidars = self.variant.sensors_for_agent(camera_sensor.agent_id, "lidar")
        lidar_ids = {sensor.stream_id for sensor in lidars}
        if not stream_id or stream_id not in lidar_ids:
            stream_id = lidars[0].stream_id if lidars else None
        if not stream_id:
            return None
        lidar_sensor = self.variant.streams.get(stream_id)
        if not lidar_sensor or lidar_sensor.kind != "lidar":
            return None
        path = frame.streams.get(stream_id)
        return lidar_sensor, path if path and path.exists() else None

    def _update_status(self, frame=None) -> None:
        frame = frame or self.variant.frame(self.playback.index)
        state = "playing" if self.playback.playing else "paused"
        self.status.text = (
            f"{self.variant.root.name} | frame {self.playback.index + 1}/{len(self.variant)} "
            f"(id {frame.frame_id}, t={frame.timestamp:.1f}s) | {state}"
        )

    def run(self) -> None:
        self.app.run()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Launch the RealSim-CP Open3D visualizer.")
    parser.add_argument(
        "variant_path",
        nargs="?",
        default="dataset/daiba_station_scenario/night_1",
        help="Path to a variant folder containing label_OpenLABEL_style.json.",
    )
    args = parser.parse_args(argv)
    RealSimOpen3DApp(args.variant_path).run()


if __name__ == "__main__":
    main()
