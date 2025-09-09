class ConfigManager:
    def __init__(self):
        self.config = {
            "reference_config": None,
            "dest_bts": None,
            "dest_bts_ip": None,
            "cmd_status": None, #명령어 성공/실패 여부 저장
        }

    def set(self, key, value):

        if key == "dest_bts":
            self.config["dest_bts"] = value

        elif key == "dest_bts_ip":
            self.config["dest_bts_ip"] = value

        elif key == "reference_config":
            self.config["reference_config"] = value

        elif key == "xml_tree":
            self.config["xml_tree"] = value  # 내부용

        elif key == "cmd_status":
            self.config["cmd_status"] = value

        else:
            raise KeyError(f"Unknown config key: {key}")

    def get(self, key):
        return self.config.get(key)

    def to_dict(self):
        return self.config

    def reset(self):
        for key in self.config:
            self.config[key] = None
