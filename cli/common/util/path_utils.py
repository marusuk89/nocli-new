import os
import sys

def get_base_dir(env_type: str):
    if env_type == "DEV":
        return os.path.join(os.getcwd(), "cli", "data")
    if getattr(sys, 'frozen', False):  # exe 환경
        return os.path.join(os.path.dirname(sys.executable), "data")
    return os.path.join(os.getcwd(), "data")

PATH_MAP = {
    "logs": ["logs"],
    "scripts": ["scripts"],
    "rulebook": ["rulebook"],
    "autocomm": ["autocomm"],
    "history": ["history"],
    "tmpl": ["tmpl_applied"],
    "xlsx": ["xlsx"],
    "mo_param": ["mo_param_dict"],
    "gen_scf": ["genScf"],
    "commit": ["generated"],
}

def get_path(env_type: str, category: str, *parts):
    base_dir = get_base_dir(env_type)
    if category not in PATH_MAP:
        raise ValueError(f"Unknown category: {category}")
    return os.path.join(base_dir, *PATH_MAP[category], *parts)
