import csv
import logging
import json
from pathlib import Path
from typing import Any

LOG_FILE = Path("~/.atopile/kicad-plugin.log").expanduser().absolute()
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

log = logging.getLogger(__name__)
log.addHandler(logging.FileHandler(str(LOG_FILE), "w", "utf-8"))
log.setLevel(logging.DEBUG)


def get_prj_dir(path: Path) -> Path:
    """Return the atopile project directory."""
    path = Path(path)
    if (path / "ato.yaml").exists():
        return path
    for p in path.parents:
        if (p / "ato.yaml").exists():
            return p
    raise FileNotFoundError("ato.yaml not found in any parent directory")


def get_board_artifact_manifest(board_path: Path) -> dict:
    """Return a dict of the artifact manifest related to this board."""
    manifest_path = get_prj_dir(board_path) / "build" / "manifest.json"
    with manifest_path.open("r") as f:
        manifest = json.load(f)
    return manifest.get("by-layout", {}).get(str(board_path), {})


def get_csv_path(board_path: Path) -> Path:
    """Return the path to the group_map.csv file."""
    manifest = get_board_artifact_manifest(str(board_path))
    layout_group_path = manifest["groups"]
    return Path(layout_group_path)


def parse_hierarchy(board_path: Path) -> dict[str, Any]:
    csv_file = get_csv_path(board_path)

    hierarchy_dict = {}
    with csv_file.open("r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row if present

        for row in reader:
            # Extract name and designator
            package, package_instance, name, designator = row

            # Check if top level exists in dict
            if package_instance not in hierarchy_dict:
                hierarchy_dict[package_instance] = {}
                hierarchy_dict[package_instance]['_package'] = package

            # Add the designator and full name as a key-value pair
            hierarchy_dict[package_instance][designator] = name

    return hierarchy_dict


def get_layout_path(prj_path: Path, heir: str) -> Path:
    """Return the path to the layout.csv file."""
    return prj_path / ".ato" / "modules" / heir / "elec" / "layout.csv"


def name2des(name: str, input_dict: dict):
    for key, value in input_dict.items():
        if value == name:
            return key
    return None
