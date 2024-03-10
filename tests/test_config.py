from atopile import config
from ruamel.yaml import YAML
import copy

yaml = YAML()


def test_roundtrip():
    config_dict = yaml.load("""
        ato-version: ^0.2.0
        builds:
            debug:
                entry: elec/src/debug.ato:Debug
        unknown: test
        # comments
        dependencies:
        - tps63020dsjr # comments
        - usb-connectors ^v2.0.1
        - name: esp32-s3
          version: ^v0.0.1
          path: ../esp32-s3
        """)
    cfg = config.ProjectConfig.structure(config_dict)
    assert config_dict == cfg.patch_config(config_dict)
    assert cfg.ato_version == "^0.2.0"

    cfg.ato_version = "10"
    config_dict_2 = copy.deepcopy(config_dict)
    config_dict_2["ato-version"] = "10"
    assert config_dict_2 == cfg.patch_config(config_dict)
