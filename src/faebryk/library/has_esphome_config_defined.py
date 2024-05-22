# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.library.has_esphome_config import has_esphome_config


class has_esphome_config_defined(has_esphome_config.impl()):
    def __init__(self, config: dict):
        super().__init__()
        self._config = config

    def get_config(self) -> dict:
        return self._config
