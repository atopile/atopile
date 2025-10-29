# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class has_esphome_config_defined(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(self, config: dict):
        super().__init__()
        self._config = config

    def get_config(self) -> dict:
        return self._config
