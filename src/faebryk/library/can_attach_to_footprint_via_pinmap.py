# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class can_attach_to_footprint_via_pinmap(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(
        self, pinmap: dict[str, F.Electrical | None] | dict[str, F.Electrical]
    ) -> None:
        super().__init__()
        self.pinmap: dict[str, F.Electrical | None] = pinmap  # type: ignore

    def attach(self, footprint: F.Footprint):
        self.obj.add(F.has_footprint_defined(footprint))
        footprint.get_trait(F.can_attach_via_pinmap).attach(self.pinmap)
