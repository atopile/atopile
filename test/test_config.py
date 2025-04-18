from pathlib import Path
from textwrap import dedent

import semver
from pydantic.networks import HttpUrl

from atopile.config import (
    PROJECT_CONFIG_FILENAME,
    FileDependencySpec,
    RegistryDependencySpec,
    config,
)

TEST_CONFIG_TEXT = dedent(
    """
    requires-atopile: ^0.2.0
    package:
      identifier: pepper-labs/my-project
      version: 1.2.3
      repository: https://github.com/pepper-labs/my-project
    builds:
      debug:
        entry: elec/src/debug.ato:Debug
    # comments
    dependencies:
    - atopile/tps63020dsjr # comments
    - atopile/usb-connectors@v2.0.1
    - atopile/esp32-s3
    - type: file
      identifier: atopile/rp2040
      path: ../rp2040
    """
).lstrip()


def test_roundtrip(tmp_path: Path):
    config_path = tmp_path / PROJECT_CONFIG_FILENAME
    config_path.write_text(TEST_CONFIG_TEXT, encoding="utf-8")
    config.project_dir = tmp_path

    assert config.project.requires_atopile == "^0.2.0"
    assert config.project.package is not None
    assert config.project.package.version == semver.Version.parse("1.2.3")
    assert config.project.package.repository == HttpUrl(
        "https://github.com/pepper-labs/my-project"
    )
    assert config.project.package.identifier == "pepper-labs/my-project"
    assert config.project.dependencies is not None
    assert config.project.dependencies[0].identifier == "atopile/tps63020dsjr"
    assert config.project.dependencies[1].identifier == "atopile/usb-connectors"
    assert isinstance(config.project.dependencies[1], RegistryDependencySpec)
    assert config.project.dependencies[1].release == "v2.0.1"
    assert config.project.dependencies[2].identifier == "atopile/esp32-s3"
    assert config.project.dependencies[3].identifier == "atopile/rp2040"
    assert isinstance(config.project.dependencies[3], FileDependencySpec)
    assert config.project.dependencies[3].path == Path("../rp2040")

    config.update_project_settings(lambda data, new_data: data, {})

    assert config_path.read_text(encoding="utf-8") == TEST_CONFIG_TEXT


def test_update_project_config(tmp_path: Path):
    config_path = tmp_path / PROJECT_CONFIG_FILENAME
    config_path.write_text(TEST_CONFIG_TEXT, encoding="utf-8")
    config.project_dir = tmp_path

    # Make some changes and check that they are reflected in the config
    dep1 = RegistryDependencySpec(identifier="usb-connectors", release="v0.0.1")
    dep2 = FileDependencySpec(identifier="esp32-s3", path=Path("../esp32-s3"))

    def add_dependency(config_data, new_data):
        config_data["dependencies"] = config_data["dependencies"] + [new_data]
        return config_data

    config.update_project_settings(add_dependency, dep1.model_dump())
    config.update_project_settings(add_dependency, dep2.model_dump())

    assert config.project.dependencies is not None

    assert isinstance(config.project.dependencies[4], RegistryDependencySpec)
    assert config.project.dependencies[4].release == "v0.0.1"
    assert isinstance(config.project.dependencies[5], FileDependencySpec)
    assert config.project.dependencies[5].path == Path("../esp32-s3")
