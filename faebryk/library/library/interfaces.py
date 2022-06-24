# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

from faebryk.library.core import Interface
from faebryk.library.traits import *
from faebryk.library.traits.interface import contructable_from_interface_list


class Electrical(Interface):
    def __init__(self) -> None:
        super().__init__()

        class _contructable_from_interface_list(contructable_from_interface_list):
            @staticmethod
            def from_interfaces(interfaces: list[Electrical]) -> Electrical:
                return next(interfaces)

        self.add_trait(_contructable_from_interface_list())


class Power(Interface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.IFs.hv = Electrical()
        self.IFs.lv = Electrical()

        class _contructable_from_interface_list(contructable_from_interface_list):
            @staticmethod
            def from_interfaces(interfaces: list[Electrical]) -> Power:
                p = Power()
                p.IFs.hv = next(interfaces)
                p.IFs.lv = next(interfaces)

                return p

        self.add_trait(_contructable_from_interface_list())

    def connect(self, other: Interface) -> Interface:
        # TODO feels a bit weird
        # maybe we need to look at how aggregate interfaces connect
        assert type(other) is Power, "can't connect to non power"
        for s, d in zip(self.IFs.get_all(), other.IFs.get_all()):
            s.connect(d)

        return self
