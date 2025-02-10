# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import StrEnum
from pathlib import Path

from faebryk.core.graph import GraphFunctions
from faebryk.core.module import Module
from faebryk.core.parameter import EnumDomain, EnumSet, Parameter
from faebryk.core.solver.solver import Solver
from faebryk.libs.util import KeyErrorAmbiguous, KeyErrorNotFound, once

logger = logging.getLogger(__name__)


class has_package(Module.TraitT.decless()):
    """Module has a package parameter"""

    class Package(StrEnum):
        # TODO: make this more extensive
        C0201 = "C0201"
        C0402 = "C0402"
        C0603 = "C0603"
        C0805 = "C0805"
        C1206 = "C1206"
        C1210 = "C1210"
        C1812 = "C1812"
        C2010 = "C2010"
        C2512 = "C2512"
        R0201 = "R0201"
        R0402 = "R0402"
        R0603 = "R0603"
        R0805 = "R0805"
        R1206 = "R1206"
        R1210 = "R1210"
        R1812 = "R1812"
        R2010 = "R2010"
        R2512 = "R2512"
        L0201 = "L0201"
        L0402 = "L0402"
        L0603 = "L0603"
        L0805 = "L0805"
        L1206 = "L1206"
        L1210 = "L1210"
        L1812 = "L1812"
        L2010 = "L2010"
        L2512 = "L2512"

    def __init__(self, *package_candidates: str | Package) -> None:
        super().__init__()
        # Saved because it makes validation way easier
        self._enum_set = {self.Package(c) for c in package_candidates}
        self.package = Parameter(domain=EnumDomain(self.Package))
        self.package.constrain_subset(EnumSet(*self._enum_set))

        # Cache the resolved package
        self._package: "has_package.Package | None" = None

    def get_package(self, solver: Solver) -> Package:
        if self._package is not None:
            return self._package

        package_superset = solver.inspect_get_known_supersets(self.package)

        if package_superset.is_empty():
            raise KeyErrorNotFound()

        if not package_superset.is_single_element():
            # TODO: add the actual candidates to the exception
            raise KeyErrorAmbiguous([])

        # We have guaranteed `.any()` returns only one thing
        # package_superset.any() is a similar enum to a package, however it's not
        # actually a member of the has_package.Package enum.
        self._package = self.Package(package_superset.any().value)

        return self._package

    def try_get_package(self, solver: Solver | None = None) -> Package | None:
        if solver is None:
            return self._package

        try:
            return self.get_package(solver)
        except (KeyErrorNotFound, KeyErrorAmbiguous):
            return None

    @classmethod
    def standardize_footprints(cls, app: Module, solver: Solver) -> None:
        """
        Attach standard footprints for known packages

        This must be done before the create_footprint_library is run
        """
        import faebryk.library._F as F
        from atopile.packages import KNOWN_PACKAGES_TO_FOOTPRINT
        from faebryk.libs.kicad.fileformats import C_kicad_footprint_file

        gf = GraphFunctions(app.get_graph())

        # TODO: make this caching global. Shit takes time
        @once
        def _get_footprint(fp_path: Path) -> C_kicad_footprint_file:
            return C_kicad_footprint_file.loads(fp_path)

        for node, pkg_t in gf.nodes_with_trait(cls):
            package = pkg_t.try_get_package(solver)
            if package is None:
                continue

            # Skip nodes with footprints already
            # TODO: consider elevating this to an exception
            if node.has_trait(F.has_footprint):
                continue

            if fp_path := KNOWN_PACKAGES_TO_FOOTPRINT.get(package):
                if can_attach_t := node.try_get_trait(F.can_attach_to_footprint):
                    fp = _get_footprint(fp_path)
                    kicad_fp = F.KicadFootprint.from_file(fp)
                    kicad_fp.add(F.KicadFootprint.has_file(fp_path))
                    can_attach_t.attach(kicad_fp)
                else:
                    # TODO: consider elevating this to an exception
                    logger.warning(
                        "%s has a package requirement but no can_attach_to_footprint"
                        " trait",
                        node,
                    )
