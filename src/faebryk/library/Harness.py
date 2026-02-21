# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class is_harness(fabll.Node):
    """
    Indicates that the module is a harness or wire interconnect between boards.

    Harnesses are excluded from PCB layout and represent physical wiring
    between boards. The cross-board DRC uses this trait to distinguish
    intended inter-board connections from wiring errors.
    """

    is_trait = fabll.Traits.MakeEdge(
        fabll.ImplementsTrait.MakeChild().put_on_type()
    ).put_on_type()
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()


class is_connector_plug(fabll.Node):
    """
    Marks a module as a plug (male) connector.

    Used by cross-board DRC to validate that connected connector pairs
    have opposite genders (one plug and one receptacle).
    """

    is_trait = fabll.Traits.MakeEdge(
        fabll.ImplementsTrait.MakeChild().put_on_type()
    ).put_on_type()
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()


class is_connector_receptacle(fabll.Node):
    """
    Marks a module as a receptacle (female) connector.

    Used by cross-board DRC to validate that connected connector pairs
    have opposite genders (one plug and one receptacle).
    """

    is_trait = fabll.Traits.MakeEdge(
        fabll.ImplementsTrait.MakeChild().put_on_type()
    ).put_on_type()
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()
