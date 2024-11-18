# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.trait import Trait


class has_esphome_config(Trait):
    @abstractmethod
    def get_config(self) -> dict: ...
