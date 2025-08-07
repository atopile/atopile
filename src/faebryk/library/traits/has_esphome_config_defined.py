# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_esphome_config_defined(F.has_esphome_config.impl()):
    def __init__(self, config: dict):
        super().__init__()
        self._config = config

    def get_config(self) -> dict:
        return self._config
