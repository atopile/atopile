# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class can_attach_to_footprint_symmetrically(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()
