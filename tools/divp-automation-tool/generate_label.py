import json
from lib.utils import load_json_file
from lib.calculate_matrix import convert_euler_to_quaternion
import xml.etree.ElementTree as ET


dummy_scenario_settings = {
    "divp_Veh_DaihatsuCopen_1": {
        "camera": {"camera_1": {}, "camera_2": {}, "camera_4": {}, "camera_5": {}},
        "lidar": {"lidar_1": {}},
        "radar": {},
    },
    "divp_Veh_DaihatsuRocky_1": {
        "camera": {"camera_6": {}, "camera_7": {}, "camera_8": {}, "camera_9": {}},
        "lidar": {"lidar_2": {}},
        "radar": {},
    },
    "object_1": {
        "camera": {"camera_10": {}, "camera_11": {}, "camera_12": {}, "camera_13": {}},
        "lidar": {"lidar_3": {}},
        "radar": {},
    },
}


class LabelGenerator:
    def __init__(
        self,
        scenario_name,
        scenario_id,
        scenario_settings,
        get_agent_id,
        stop_time,
        rsu_object_ids,
    ):
        self.scenario_name = scenario_name
        self.scenario_id = scenario_id
        self.scenario_settings = {
            "agents": scenario_settings,
            "frame_nums": int(stop_time / 0.1) + 1,
            "time_step": 0.1,
        }
        self.get_agent_id = get_agent_id
        self.output_file = f"scenarios/{scenario_name}/output_data/{scenario_id}/label_OpenLABEL_style.json"
        self.label_data = {
            "openlabel": {
                "metadata": {"schema_version": "1.0.0"},
            }
        }
        self.rsu_object_ids = rsu_object_ids

    def generate_label(self):
        self.label_data["openlabel"]["streams"] = self.generate_streams()
        self.label_data["openlabel"]["frames"] = self.generate_frames()
        self.label_data["openlabel"]["coordinate_systems"] = (
            self.generate_coordinate_systems()
        )
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.label_data, f, ensure_ascii=False, indent=2)

    def generate_coordinate_systems(self):
        """OpenLABEL仕様に従って座標系を生成"""
        coordinate_systems = {}
        coordinate_systems["scene"] = {"type": "scene_cs", "parent": "", "children": []}

        scenario_xml = (
            f"scenarios/{self.scenario_name}/scenario/{self.scenario_name}_csv_osi.xml"
        )
        rsu_poses = self._extract_rsu_poses(scenario_xml)

        vehicle_cs_names = []
        for agent_name in self.scenario_settings["agents"].keys():
            if (
                not self.scenario_settings["agents"][agent_name]["camera"]
                and not self.scenario_settings["agents"][agent_name]["lidar"]
                and not self.scenario_settings["agents"][agent_name]["radar"]
            ):
                continue
            agent_id = self.get_agent_id(agent_name)
            vehicle_cs_name = f"{agent_id}_local"
            vehicle_cs_names.append(vehicle_cs_name)

            # RSUの場合は位置・姿勢を設定
            if agent_name.startswith("rsu_"):
                pose = rsu_poses.get(agent_name, None)
                if pose:
                    coordinate_systems[vehicle_cs_name] = {
                        "type": "local_cs",
                        "parent": "scene",
                        "pose_wrt_parent": {
                            "quaternion": pose["quaternion"],
                            "translation": pose["translation"],
                        },
                        "children": [],
                    }
                else:
                    coordinate_systems[vehicle_cs_name] = {
                        "type": "local_cs",
                        "parent": "scene",
                        "children": [],
                    }
            else:
                coordinate_systems[vehicle_cs_name] = {
                    "type": "local_cs",
                    "parent": "scene",
                    "children": [],
                }

        coordinate_systems["scene"]["children"] = vehicle_cs_names

        sensor_poses = self._extract_sensor_poses(scenario_xml)

        for agent_name, sensors in self.scenario_settings["agents"].items():
            if (
                not self.scenario_settings["agents"][agent_name]["camera"]
                and not self.scenario_settings["agents"][agent_name]["lidar"]
                and not self.scenario_settings["agents"][agent_name]["radar"]
            ):
                continue
            agent_id = self.get_agent_id(agent_name)
            vehicle_cs_name = f"{agent_id}_local"
            sensor_children = []

            # カメラの座標系
            for camera_id in sensors["camera"].keys():
                sensor_cs_name = f"{agent_id}/{camera_id}_cs"
                sensor_children.append(sensor_cs_name)

                # XMLから位置・姿勢を取得
                obj_id = agent_name  # または適切なマッピング
                pose = sensor_poses.get((obj_id, camera_id), None)

                if pose:
                    coordinate_systems[sensor_cs_name] = {
                        "type": "sensor_cs",
                        "parent": vehicle_cs_name,
                        "pose_wrt_parent": {
                            "quaternion": pose["quaternion"],  # [w, x, y, z]
                            "translation": pose["translation"],  # [x, y, z]
                        },
                        "children": [],
                    }
                else:
                    # デフォルト（位置・姿勢情報がない場合）
                    coordinate_systems[sensor_cs_name] = {
                        "type": "sensor_cs",
                        "parent": vehicle_cs_name,
                        "children": [],
                    }

            # LiDARの座標系（同様に処理）
            for lidar_id in sensors["lidar"].keys():
                sensor_cs_name = f"{agent_id}/{lidar_id}_cs"
                sensor_children.append(sensor_cs_name)

                obj_id = agent_name
                pose = sensor_poses.get((obj_id, lidar_id), None)

                if pose:
                    coordinate_systems[sensor_cs_name] = {
                        "type": "sensor_cs",
                        "parent": vehicle_cs_name,
                        "pose_wrt_parent": {
                            "quaternion": pose["quaternion"],
                            "translation": pose["translation"],
                        },
                        "children": [],
                    }
                else:
                    coordinate_systems[sensor_cs_name] = {
                        "type": "sensor_cs",
                        "parent": vehicle_cs_name,
                        "children": [],
                    }

            # vehicle座標系のchildrenを更新
            coordinate_systems[vehicle_cs_name]["children"] = sensor_children

        return coordinate_systems

    def _extract_sensor_poses(self, xml_path):
        """XMLファイルからセンサの位置・姿勢情報を抽出"""
        tree = ET.parse(xml_path)
        root = tree.getroot()

        sensor_poses = {}
        space = root.find("space")
        if space is None:
            return sensor_poses

        objects = space.find("objects")
        if objects is None:
            return sensor_poses

        for obj in objects.findall("object"):
            obj_id = obj.get("id")
            if not obj_id:
                continue

            # カメラとLiDARを処理
            for sensor in obj.findall("camera") + obj.findall("lidar"):
                sensor_id = sensor.get("id")
                if not sensor_id:
                    continue

                coord = sensor.find("coordinate[@type='relative']")
                if coord is None:
                    continue

                position = coord.find("position")
                attitude = coord.find("attitude")

                if position is not None and attitude is not None:
                    # 位置（translation）
                    translation = [
                        float(position.get("x", 0)),
                        float(position.get("y", 0)),
                        float(position.get("z", 0)),
                    ]

                    # オイラー角（attitude: x=roll, y=pitch, z=yaw）
                    roll = float(attitude.get("x", 0))
                    pitch = float(attitude.get("y", 0))
                    yaw = float(attitude.get("z", 0))

                    # オイラー角をクォータニオンに変換
                    quaternion = convert_euler_to_quaternion(roll, pitch, yaw)

                    sensor_poses[(obj_id, sensor_id)] = {
                        "translation": translation,
                        "quaternion": quaternion,
                    }

        return sensor_poses

    def _extract_rsu_poses(self, xml_path):
        """XMLファイルからRSUの位置・姿勢情報を抽出

        scenarios -> concreteScenario[id=scenario_id] -> initialization ->
        entity[id=agent_name] -> event -> action[index=0] (position) と action[index=1] (attitude)
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        rsu_poses = {}
        scenarios = root.find("scenarios")
        if scenarios is None:
            return rsu_poses

        concrete_scenarios = scenarios.find("concreteScenarios")
        if concrete_scenarios is None:
            return rsu_poses

        # scenario_idに一致するconcreteScenarioを探す
        scenario_id = self.scenario_id
        concrete_scenario = None
        for cs in concrete_scenarios.findall("concreteScenario"):
            if cs.get("id") == scenario_id:
                concrete_scenario = cs
                break

        if concrete_scenario is None:
            return rsu_poses

        initialization = concrete_scenario.find("initialization")
        if initialization is None:
            return rsu_poses

        # 各entityを処理
        for entity in initialization.findall("entity"):
            entity_id = entity.get("id")
            if not entity_id or not entity_id.startswith("rsu_"):
                continue

            # eventを探す
            event = entity.find("event")
            if event is None:
                continue

            # action[index=0] (position) と action[index=1] (attitude) を取得
            position_action = None
            attitude_action = None

            for action in event.findall("action"):
                index = action.get("index")
                if index == "0":
                    position_action = action
                elif index == "1":
                    attitude_action = action

            if position_action is not None and attitude_action is not None:
                position = position_action.find("position")
                attitude = attitude_action.find("attitude")

                if position is not None and attitude is not None:
                    # 位置（translation）
                    translation = [
                        float(position.get("x", 0)),
                        float(position.get("y", 0)),
                        float(position.get("z", 0)),
                    ]

                    # オイラー角（attitude: x=roll, y=pitch, z=yaw）
                    roll = float(attitude.get("x", 0))
                    pitch = float(attitude.get("y", 0))
                    yaw = float(attitude.get("z", 0))

                    # オイラー角をクォータニオンに変換
                    quaternion = convert_euler_to_quaternion(roll, pitch, yaw)

                    rsu_poses[entity_id] = {
                        "translation": translation,
                        "quaternion": quaternion,
                    }

        return rsu_poses

    def generate_streams(self):
        streams = {}
        for agent_name, sensors in self.scenario_settings["agents"].items():
            for camera_id, camera_contents in sensors["camera"].items():
                stream_id = f"{self.get_agent_id(agent_name)}/{camera_id}"
                streams[stream_id] = {
                    "type": "camera",
                    "description": camera_contents.get("description", ""),
                    "stream_properties": {
                        "intrinsics_custom": {
                            "distortion_file": "lens_distortion_i49.csv",
                            "camera_parameters": self._extract_camera_parameters(),
                        },
                        **CameraParameters().get_image_size(),
                    },
                }
            for lidar_id, lidar_contents in sensors["lidar"].items():
                stream_id = f"{self.get_agent_id(agent_name)}/{lidar_id}"
                streams[stream_id] = {
                    "type": "lidar",
                    "description": lidar_contents.get("description", ""),
                }

        return streams

    def _extract_camera_parameters(self):
        camera_config_file = "camera_rendering_automation.json"
        camera_settings = load_json_file(camera_config_file)
        if camera_settings is None:
            raise FileNotFoundError(
                f"Could not load camera settings from {camera_config_file}"
            )
        image_size = camera_settings["rendering"]["camera"]["image_size"]
        (fx, fy, cx, cy) = (
            camera_settings["rendering"]["camera"]["focal_length"]
            * image_size["width"]
            / camera_settings["rendering"]["camera"]["cmos_width"],
            camera_settings["rendering"]["camera"]["focal_length"]
            * image_size["height"]
            / camera_settings["rendering"]["camera"]["cmos_height"],
            image_size["width"] / 2,
            image_size["height"] / 2,
        )
        return {
            "fx": fx,
            "fy": fy,
            "cx": cx,
            "cy": cy,
            "k1": 2.6948211748,
            "k2": 0.5986442976,
            "k3": 0.0081148076,
            "k4": 3.1498897006,
            "k5": 1.5120334123,
            "k6": 0.0934822259,
        }

    def generate_frames(self):
        frames = {}
        initial_agent_id, initial_camera_id = self.get_sensor_for_grand_truth()
        for frame_index in range(self.scenario_settings["frame_nums"]):
            frame_manager = FrameManager(
                self.scenario_name,
                self.scenario_id,
                self.scenario_settings,
                self.generate_streams(),
                frame_index,
                initial_agent_id,
                initial_camera_id,
                self.rsu_object_ids,
            )
            frames[frame_index] = frame_manager.generate_label()

        return frames

    def get_sensor_for_grand_truth(self):
        for agent_name, sensors in self.scenario_settings["agents"].items():
            for camera_id in sensors["camera"].keys():
                return self.get_agent_id(agent_name), camera_id
        return None, None


class CameraParameters:
    def __init__(self):
        camera_config_file = "camera_rendering_automation.json"
        self.camera_settings = load_json_file(camera_config_file)
        if self.camera_settings is None:
            raise FileNotFoundError(
                f"Could not load camera settings from {camera_config_file}"
            )

    def get_image_size(self):
        return self.camera_settings["rendering"]["camera"]["image_size"]


class FrameManager:
    def __init__(
        self,
        scenario_name,
        scenario_id,
        scenario_settings,
        streams,
        frame_index,
        initial_agent_id,
        initial_camera_id,
        rsu_object_ids,
    ):
        self.scenario_name = scenario_name
        self.scenario_id = scenario_id
        self.scenario_settings = scenario_settings
        self.clock = frame_index * scenario_settings["time_step"]
        self.streams = streams
        self.frame_index = frame_index
        self.rsu_object_ids = rsu_object_ids

        ground_truth_file = f"scenarios/{self.scenario_name}/output_data/{self.scenario_id}/bounding_box/{initial_agent_id}/{initial_camera_id}/global_{self.clock:.6f}.txth"
        self.ground_truth_data = load_json_file(ground_truth_file)
        if self.ground_truth_data is None:
            raise FileNotFoundError(
                f"Could not load ground truth data from {ground_truth_file}"
            )

    def generate_label(self):
        frame_properties = self.get_frame_properties()
        objects = self.get_frame_objects()

        return {
            "frame_properties": frame_properties,
            "objects": objects,
        }

    def get_frame_properties(self):
        frame_properties = {}
        frame_properties["timestamp"] = self.clock
        frame_properties["streams"] = {
            stream_key: {
                "uri": f"images/{stream_key}/image_{str(self.frame_index).zfill(4)}00.png"
                if self.streams[stream_key]["type"] == "camera"
                else f"point_clouds/{stream_key}/velodyne_vlp_128/point_cloud_{self.clock:.1f}.pcd"
                if self.clock != 0
                else f"point_clouds/{stream_key}/velodyne_vlp_128/point_cloud_0.pcd"
            }
            for stream_key in self.streams.keys()
        }
        return frame_properties

    def get_frame_objects(self):
        objects = {}
        for object_info in self.ground_truth_data["moving_object"]:
            moving_object = MovingObject(object_info)
            obj_id, obj_label = moving_object.generate_label()
            if obj_id in self.rsu_object_ids:
                continue
            objects[obj_id] = {"object_data": obj_label}

        return objects


class MovingObject:
    def __init__(self, object_info):
        self.object_info = object_info

    def generate_label(self):
        object_id = self.object_info["id"]["value"]
        object_type = (
            self.object_info["vehicle_classification"]["type"]
            if self.object_info["type"] == "TYPE_VEHICLE"
            else self.object_info["type"]
        )

        object_data = {
            "type": object_type,
            "name": f"{object_type}_{object_id}",
            "cuboid": self.get_cuboid(),
        }
        return object_id, object_data

    def get_cuboid(self):
        cuboid = {}
        cuboid["name"] = "shape3D"
        cuboid["value"] = [
            self.object_info["base"]["position"]["x"],
            self.object_info["base"]["position"]["y"],
            self.object_info["base"]["position"]["z"],
            *convert_euler_to_quaternion(
                self.object_info["base"]["orientation"]["roll"],
                self.object_info["base"]["orientation"]["pitch"],
                self.object_info["base"]["orientation"]["yaw"],
            ),
            self.object_info["base"]["dimension"]["length"],
            self.object_info["base"]["dimension"]["width"],
            self.object_info["base"]["dimension"]["height"],
        ]
        cuboid["attributes"] = {"text": [], "num": [], "boolean": []}

        return cuboid


def generate_label(
    scenario_name,
    scenario_id,
    scenario_settings,
    get_agent_id,
    stop_time,
    rsu_object_ids,
):
    generator = LabelGenerator(
        scenario_name,
        scenario_id,
        scenario_settings,
        get_agent_id,
        stop_time,
        rsu_object_ids,
    )
    generator.generate_label()

    return 0


if __name__ == "__main__":
    rc = generate_label(
        "automation_scenario",
        "scenario_1_1",
        dummy_scenario_settings,
        lambda x: "vehicle_10000",
        1.0,
    )
    exit(rc)
