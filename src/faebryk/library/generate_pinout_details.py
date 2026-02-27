# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class generate_pinout_details(fabll.Node):
    """
    Marker trait indicating that pinout details should be generated
    for this component during the build process.

    Add this trait to any component (typically an MCU or IC) to produce
    a pinout report (.pinout.json, .pinout.csv, pinout.md) as build artifacts.
    """

    is_trait = fabll.Traits.MakeEdge(
        fabll.ImplementsTrait.MakeChild().put_on_type()
    ).put_on_type()
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()
