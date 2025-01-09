# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum, auto

from faebryk.core.module import Module
from faebryk.core.parameter import EnumDomain, EnumSet, Parameter


class has_package(Module.TraitT.decless()):
    """Module has a package parameter"""

    class Package(StrEnum):
        # TODO: make this more extensive
        C0201 = auto()
        C0402 = auto()
        C0603 = auto()
        C0805 = auto()
        R0201 = auto()
        R0402 = auto()
        R0603 = auto()
        R0805 = auto()
        L0201 = auto()
        L0402 = auto()
        L0603 = auto()
        L0805 = auto()

    def __init__(self, *package_candidates: str | Package) -> None:
        super().__init__()
        # Saved because it makes validation way easier
        self._enum_set = {self.Package(c) for c in package_candidates}
        self.package = Parameter(domain=EnumDomain(self.Package))
        self.package.constrain_subset(EnumSet(*self._enum_set))
