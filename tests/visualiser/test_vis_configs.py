# contents of conftest.py
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from atopile.model.model import Model
from atopile.project.project import Project
from atopile.visualizer.project_handler import ProjectHandler


@pytest.fixture
def vis_config_data():
    return {
        "vdiv": {
            "ports": [
                {
                    "name": "top",
                    "location": "top"
                },
                {
                    "name": "right",
                    "location": "right"
                },
                {
                    "name": "bottom",
                    "location": "bottom"
                }
            ],
            "pins": [
                {
                    "name": "input",
                    "index": 0,
                    "private": False,
                    "port": "top"
                },
                {
                    "name": "output",
                    "index": 0,
                    "private": False,
                    "port": "right"
                },
                {
                    "name": "ground",
                    "index": 0,
                    "private": False,
                    "port": "bottom"
                }
            ],
            "signals": [
                {
                    "name": "input",
                    "is_stub": True
                },
                {
                    "name": "output",
                    "is_stub": True
                },
                {
                    "name": "ground",
                    "is_stub": False
                }
            ],
            "child_attrs": {
                "r_top": {
                    "position": {
                        "x": 10,
                        "y": 10
                    }
                },
                "r_bt": {
                    "position": {
                        "x": 10,
                        "y": 100
                    }
                }
            }
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
    assert dict(await project_handler.get_config("dummy_file.vis.json")) == vis_config_data
