from enum import Enum

class ActionCmd(str, Enum):
    INIT = "init"
    DEL = "del"
    COPY = "copy"

class RatType(str, Enum):
    LTE =  "LTE"
    FOUR_G = "4g"
    FIVE_G = "5g"

class BtsId(str, Enum):
    BTS_147568 = "147568"
    BTS_131297 = "131297"
    BTS_20000 = "20000"
    BTS_50000 = "50000"

DEFAULT_XML_MAP = {
    ("init", "4g", "147568"): "MRBTS147568.xml",
    ("init", "5g", "131297"): "5G_DU30_Ref_20240705.xml",
    ("init", "5g", "147568"): "MRBTS147568.xml"
}

class ConfigManager:
    def __init__(self):
        self.config = {
            "action_cmd": None,
            "rat_type": None,
            "tgt_bts": None,
            "reference_config": None,
        }

    def set(self, key, value):
        if key == "action_cmd":
            if value not in ActionCmd._value2member_map_:
                raise ValueError(f"Invalid action_cmd: {value}")
            self.config["action_cmd"] = value

        elif key == "rat_type":
            if value not in RatType._value2member_map_:
                raise ValueError(f"Invalid rat_type: {value}")
            self.config["rat_type"] = value

        elif key == "tgt_bts":
            if value not in BtsId._value2member_map_:
                raise ValueError(f"Invalid tgt_bts: {value}")
            self.config["tgt_bts"] = value

        elif key == "reference_config":
            self.config["reference_config"] = value

        elif key == "xml_tree":
          self.config["xml_tree"] = value  # 내부용

        else:
            raise KeyError(f"Unknown config key: {key}")

        self._try_auto_set_reference_config()

    def _try_auto_set_reference_config(self):
        """자동 reference_config 매칭"""
        if self.config["reference_config"]:
            return

        key = (
            self.config["action_cmd"],
            self.config["rat_type"],
            self.config["tgt_bts"]
        )
        if all(key) and key in DEFAULT_XML_MAP:
            self.config["reference_config"] = DEFAULT_XML_MAP[key]

    def get(self, key):
        return self.config.get(key)

    def to_dict(self):
        return self.config

    def reset(self):
        for key in self.config:
            self.config[key] = None
