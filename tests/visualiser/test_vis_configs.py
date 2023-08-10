import copy
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from atopile.model.model import Model
from atopile.project.project import Project
from atopile.viewer.project_handler import ProjectHandler


@pytest.fixture
def vis_config_data():
    return {
        "vdiv": {
            "ports": {
                "top": {"location": "top"},
                "right": {"location": "right"},
                "bottom": {"location": "bottom"},
            },
            "pins": {
                "input": {"index": 0, "private": False, "port": "top"},
                "output": {"index": 0, "private": False, "port": "right"},
                "ground": {"index": 0, "private": False, "port": "bottom"},
            },
            "signals": {
                "input": {"is_stub": True},
                "output": {"is_stub": True},
                "ground": {"is_stub": False},
            },
            "child_attrs": {
                "r_top": {"position": {"x": 10, "y": 10}},
                "r_bt": {"position": {"x": 10, "y": 100}},
            },
        }
    }


@pytest.fixture
def mocked_project(tmp_path: Path):
    _mocked_project = MagicMock()
    _mocked_project.root = tmp_path
    return _mocked_project


@pytest.fixture
def project_handler(dummy_model: Model, mocked_project: Project, vis_config_data: dict):
    _project_handler = ProjectHandler()
    _project_handler._model = dummy_model
    _project_handler.project = mocked_project

    vis_config_path = mocked_project.root / "dummy_file.vis.yaml"
    with vis_config_path.open("w") as f:
        yaml.dump(vis_config_data, f)

    return _project_handler


@pytest.mark.asyncio
async def test_load_yaml(project_handler: ProjectHandler, vis_config_data: dict):
    assert (
        dict(await project_handler.get_config("dummy_file.vis.json")) == vis_config_data
    )


@pytest.mark.asyncio
async def test_update_yaml(project_handler: ProjectHandler, vis_config_data: dict):
    await project_handler.update_config(
        "dummy_file.vis.json", {"vdiv": {"pins": {"input": {"private": True}}}}
    )

    expected = copy.deepcopy(vis_config_data)
    expected["vdiv"]["pins"]["input"]["private"] = True

    actual = dict(await project_handler.get_config("dummy_file.vis.json"))
    assert actual == expected
