from pathlib import Path
from textwrap import dedent

import semver

from atopile.config import PROJECT_CONFIG_FILENAME, Dependency, config

TEST_CONFIG_TEXT = dedent(
    """
    ato-version: ^0.2.0
    requires-atopile-version: ^0.2.0
    repository: https://github.com/pepper-labs/my-project
    name: my-project
    version: 1.2.3
    builds:
      debug:
        entry: elec/src/debug.ato:Debug
    # comments
    dependencies:
    - tps63020dsjr # comments
    - usb-connectors ^v2.0.1
    - esp32-s3
    - name: rp2040
      path: ../rp2040
      version_spec: ^v0.0.1
      link_broken: true
    """
).lstrip()


def test_roundtrip(tmp_path: Path):
    config_path = tmp_path / PROJECT_CONFIG_FILENAME
    config_path.write_text(TEST_CONFIG_TEXT)
    config.project_dir = tmp_path

    assert config.project.ato_version == "^0.2.0"
    assert config.project.requires_atopile_version == "^0.2.0"
    assert config.project.version == semver.Version.parse("1.2.3")
    assert config.project.repository == "https://github.com/pepper-labs/my-project"
    assert config.project.name == "my-project"
    assert config.project.dependencies is not None
    assert config.project.dependencies[0].name == "tps63020dsjr"
    assert config.project.dependencies[1].name == "usb-connectors"
    assert config.project.dependencies[1].version_spec == "^v2.0.1"
    assert config.project.dependencies[2].name == "esp32-s3"
    assert config.project.dependencies[3].name == "rp2040"
    assert config.project.dependencies[3].path == Path("../rp2040")
    assert config.project.dependencies[3].version_spec == "^v0.0.1"
    assert config.project.dependencies[3].link_broken is True

    config.update_project_config(lambda data, new_data: data, {})

    assert config_path.read_text() == TEST_CONFIG_TEXT


def test_update_project_config(tmp_path: Path):
    config_path = tmp_path / PROJECT_CONFIG_FILENAME
    config_path.write_text(TEST_CONFIG_TEXT)
    config.project_dir = tmp_path

    # Make some changes and check that they are reflected in the config
    dep1 = Dependency(name="usb-connectors", version_spec="^v0.0.1", path=Path("test"))
    dep2 = Dependency(name="esp32-s3", version_spec="^v0.0.1", path=Path("../esp32-s3"))

    def add_dependency(config_data, new_data):
        config_data["dependencies"] = config_data["dependencies"] + [new_data]
        return config_data

    config.update_project_config(add_dependency, dep1.model_dump())
    config.update_project_config(add_dependency, dep2.model_dump())

    assert config.project.dependencies is not None

    assert config.project.dependencies[4].path == Path("test")
    assert config.project.dependencies[5].path == Path("../esp32-s3")
