import matlab.engine
import xml.etree.ElementTree as ET
import os
from copy import deepcopy
import json
from generate_label import generate_label


class ObjectIDManager:
    def __init__(self, scenario_name, scenario_id):
        with open(
            f"scenarios/{scenario_name}/scenario/{scenario_name}_csv_{scenario_id}_osi_supl.json",
            "r",
        ) as f:
            self.objects = json.load(f)["object"]

    def get_agent_id(self, object_id):
        if object_id.startswith("rsu_"):
            return object_id

        target_obj = [
            obj for obj in self.objects if obj["scenario"]["object_id"] == object_id
        ]
        if len(target_obj) != 1:
            raise ValueError(f"Object ID {object_id} not found or not unique.")
        return "vehicle_" + str(target_obj[0]["id"])

    def rsu_object_ids(self):
        rsu_ids = []
        for obj in self.objects:
            if obj["scenario"]["object_id"].startswith("rsu_"):
                rsu_ids.append(obj["id"])
        return set(rsu_ids)


class ScenarioReader:
    def __init__(self, original_xml):
        tree = ET.parse(original_xml)
        self.root = tree.getroot()

    def get_sensor_settings(self):
        # find the objects container: /space/objects
        space = self.root.find("space")
        if space is None:
            raise ValueError("No <space> element found in the XML.")
        objects_container = space.find("objects")
        if objects_container is None:
            raise ValueError("No <objects> element found in the XML.")

        self.sensor_settings = {}
        objects = list(objects_container.findall("object"))
        for obj in objects:
            obj_id = obj.get("id")
            if not obj_id:
                continue
            self.sensor_settings[obj_id] = {
                "camera": {},
                "lidar": {},
                "radar": {},
            }
            for child in list(obj):
                if child.tag in ("camera", "lidar", "radar"):
                    self.sensor_settings[obj_id][child.tag][child.get("id")] = {}
        return self.sensor_settings

    def get_scenario_list(self):
        scenarios = self.root.find("scenarios").find("concreteScenarios")
        return [scn.get("id") for scn in scenarios.findall("concreteScenario")]


def generate_scenario_xml(scenario_name):
    original_xml = f"scenarios/{scenario_name}/scenario/{scenario_name}_csv_osi.xml"
    tree = ET.parse(original_xml)
    root = tree.getroot()

    # find the objects container: /space/objects
    space = root.find("space")
    if space is None:
        raise ValueError("No <space> element found in the XML.")
    objects_container = space.find("objects")
    if objects_container is None:
        raise ValueError("No <objects> element found in the XML.")

    objects = list(objects_container.findall("object"))

    # only target objects which are vehicles or RSUs"
    target_indices = [
        i
        for i, obj in enumerate(objects)
        if (obj.get("type") == "vehicle")
        or (obj.get("id") and obj.get("id").startswith("rsu_"))
    ]

    base = os.path.splitext(os.path.basename(original_xml))[0]
    out_dir = os.path.dirname(original_xml) or "."

    for idx in target_indices:
        # deep copy whole tree to modify safely
        target_obj = objects[idx]
        new_root = deepcopy(root)
        new_space = new_root.find("space")
        new_objects_container = new_space.find("objects")
        new_objects = list(new_objects_container.findall("object"))

        # Remove sensor tags from objects that are above target (index < idx)
        for j in range(0, idx):
            obj_j = new_objects[j]
            # remove direct child tags named camera, lidar, radar
            for child in list(obj_j):
                if child.tag in ("camera", "lidar", "radar"):
                    obj_j.remove(child)

        obj_id = target_obj.get("id")
        if not obj_id:
            # skip unnamed objects
            continue

        # Modify the relative paths in csvFile and osi/osiSupl tags
        new_maps = list(new_space.find("maps").findall("map"))
        for map_elem in new_maps:
            for route in map_elem.findall("routes/route"):
                csv_file = route.find("csvFile")
                if csv_file is not None and csv_file.get("file"):
                    csv_file.set("file", "../" + csv_file.get("file"))

        new_scenarios = list(
            new_root.find("scenarios")
            .find("concreteScenarios")
            .findall("concreteScenario")
        )
        for scenario in new_scenarios:
            ground_truth = scenario.find("groundTruth")
            if ground_truth is None:
                continue
            osi = ground_truth.find("osi")
            if osi is not None and osi.get("file"):
                osi.set("file", "../" + osi.get("file"))
            osi_supl = ground_truth.find("osiSupl")
            if osi_supl is not None and osi_supl.get("file"):
                osi_supl.set("file", "../" + osi_supl.get("file"))

        out_name = f"{base}_{obj_id}.xml"
        out_path = os.path.join(out_dir, "generated", out_name)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        # write tree
        ET.ElementTree(new_root).write(out_path, encoding="utf-8", xml_declaration=True)


class SimulationManager:
    def __init__(self, scenario_name, stop_time):
        self.scenario_name = scenario_name
        self.scenario_xml = (
            f"scenarios/{scenario_name}/scenario/{scenario_name}_csv_osi.xml"
        )
        self.stop_time = stop_time
        self.camera_model_name = "CameraAutomation"
        self.lidar_model_names = ["LidarV20Automation"]
        self.bbox_model_name = "GroundTruthBboxAutomation"
        self.engine = matlab.engine.start_matlab()

    def load_projects(self):
        try:
            self.engine.load_system(self.camera_model_name, nargout=0)
            for lidar_model_name in self.lidar_model_names:
                self.engine.load_system(lidar_model_name, nargout=0)
            self.engine.load_system(self.bbox_model_name, nargout=0)
        except Exception as e:
            print(f"Error loading projects: {e}")
            self.engine.quit()

    def set_matlab_string(self, var_name, value):
        self.engine.eval(f'{var_name} = "{value}";', nargout=0)

    def set_stop_time(self):
        self.engine.set_param(
            self.camera_model_name, "StopTime", str(self.stop_time), nargout=0
        )
        for lidar_model_name in self.lidar_model_names:
            self.engine.set_param(
                lidar_model_name, "StopTime", str(self.stop_time), nargout=0
            )
        self.engine.set_param(
            self.bbox_model_name, "StopTime", str(self.stop_time), nargout=0
        )

    def simulate_one_agent(self, scenario_id, agent_id, sensors):
        self.set_matlab_string("agentID", agent_id)
        # collect camera data
        for sensor_id in sensors["camera"]:
            self.set_matlab_string("sensorID", sensor_id)
            self.set_matlab_string(
                "outputDir",
                f"scenarios/{self.scenario_name}/output_data/{scenario_id}/images/{agent_id}/{sensor_id}",
            )

            self.engine.sim(self.camera_model_name)

        # collect lidar data
        for sensor_id in sensors["lidar"]:
            self.set_matlab_string("sensorID", sensor_id)
            for lidar_model_name in self.lidar_model_names:
                self.engine.sim(lidar_model_name)

        # collect bounding box
        for sensor_id in sensors["camera"]:
            self.set_matlab_string("sensorID", sensor_id)
            self.set_matlab_string(
                "outputDir",
                f"scenarios/{self.scenario_name}/output_data/{scenario_id}/bounding_box/{agent_id}/{sensor_id}",
            )
            self.engine.sim(self.bbox_model_name)

    def simulate(self):
        try:
            self.load_projects()
            self.set_stop_time()

            self.set_matlab_string(
                "cameraConfigFile", "camera_rendering_automation.json"
            )
            self.set_matlab_string(
                "lidarConfigFile", "lidar_rendering_v20_automation.json"
            )
            self.set_matlab_string("scenarioName", self.scenario_name)

            scenario_reader = ScenarioReader(self.scenario_xml)
            sensor_settings = scenario_reader.get_sensor_settings()
            scenario_ids = scenario_reader.get_scenario_list()

            for scenario_id in scenario_ids:
                self.set_matlab_string("scenarioID", scenario_id)
                object_id_manager = ObjectIDManager(self.scenario_name, scenario_id)

                for object_id, sensors in sensor_settings.items():
                    if (
                        not sensors["camera"]
                        and not sensors["lidar"]
                        and not sensors["radar"]
                    ):
                        continue
                    agent_id = object_id_manager.get_agent_id(object_id)
                    self.set_matlab_string(
                        "scenarioXML",
                        f"scenarios/{self.scenario_name}/scenario/generated/{self.scenario_name}_csv_osi_{object_id}.xml",
                    )
                    self.simulate_one_agent(scenario_id, agent_id, sensors)

                generate_label(
                    self.scenario_name,
                    scenario_id,
                    sensor_settings,
                    object_id_manager.get_agent_id,
                    self.stop_time,
                    object_id_manager.rsu_object_ids(),
                )

        finally:
            self.engine.quit()


if __name__ == "__main__":
    scenario_name = "automation_scenario"
    generate_scenario_xml(scenario_name)
    sim_manager = SimulationManager(scenario_name, 5)
    sim_manager.simulate()
