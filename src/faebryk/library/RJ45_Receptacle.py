# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.DifferentialPair import (
    DifferentialPair,
)
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
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
                    "1": self.IFs.twisted_pairs[0].IFs.p,
                    "2": self.IFs.twisted_pairs[0].IFs.n,
                    "3": self.IFs.twisted_pairs[1].IFs.p,
                    "4": self.IFs.twisted_pairs[1].IFs.n,
                    "5": self.IFs.twisted_pairs[2].IFs.p,
                    "6": self.IFs.twisted_pairs[2].IFs.n,
                    "7": self.IFs.twisted_pairs[3].IFs.p,
                    "8": self.IFs.twisted_pairs[3].IFs.n,
                }
            )
        )
        self.add_trait(has_designator_prefix_defined("P"))
