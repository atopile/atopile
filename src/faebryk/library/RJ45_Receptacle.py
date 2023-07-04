# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.differential_pair import (
    DifferentialPair,
)
from faebryk.library.has_defined_type_description import has_defined_type_description
from faebryk.libs.util import times


class RJ45_Receptacle(Module):
    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            twisted_pairs = times(4, DifferentialPair)

        self.IFs = _IFs(self)

        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": self.IFs.twisted_pairs[0].NODEs.p,
                    "2": self.IFs.twisted_pairs[0].NODEs.n,
                    "3": self.IFs.twisted_pairs[1].NODEs.p,
                    "4": self.IFs.twisted_pairs[1].NODEs.n,
                    "5": self.IFs.twisted_pairs[2].NODEs.p,
                    "6": self.IFs.twisted_pairs[2].NODEs.n,
                    "7": self.IFs.twisted_pairs[3].NODEs.p,
                    "8": self.IFs.twisted_pairs[3].NODEs.n,
                }
            )
        )
        self.add_trait(has_defined_type_description("x"))
