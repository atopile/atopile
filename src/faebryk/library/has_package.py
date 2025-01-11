# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

from faebryk.core.module import Module
from faebryk.core.parameter import EnumDomain, EnumSet, Parameter


class has_package(Module.TraitT.decless()):
    """Module has a package parameter"""

    class Package(StrEnum):
        # TODO: make this more extensive
        C0201 = "C0201"
        C0402 = "C0402"
        C0603 = "C0603"
        C0805 = "C0805"
        R0201 = "R0201"
        R0402 = "R0402"
        R0603 = "R0603"
        R0805 = "R0805"
        L0201 = "L0201"
        L0402 = "L0402"
        L0603 = "L0603"
        L0805 = "L0805"

    def __init__(self, *package_candidates: str | Package) -> None:
        super().__init__()
        # Saved because it makes validation way easier
        self._enum_set = {self.Package(c) for c in package_candidates}
        self.package = Parameter(domain=EnumDomain(self.Package))
        self.package.constrain_subset(EnumSet(*self._enum_set))
