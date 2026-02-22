# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import faebryk.core.node as fabll


class is_spice_simulation(fabll.Node):
    """Trait marking a node as a SPICE simulation.

    Replaces SimulationConfig. Added to all simulation types
    (SimulationTransient, SimulationAC, SimulationDCOP, SimulationSweep).
    Provides uniform discovery and common accessor methods.
    """

    is_trait = fabll.Traits.MakeEdge(
        fabll.ImplementsTrait.MakeChild().put_on_type()
    ).put_on_type()
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()

    # Runtime cache (not graph parameters — only lives within a build run)
    _result: object = None
    _net_aliases: dict | None = None

    def get_owner(self) -> fabll.Node:
        """Get the simulation module this trait is attached to."""
        return fabll.Traits.bind(self).get_obj(fabll.Node)

    def get_simulation_type(self) -> str:
        """Return 'transient', 'ac', 'dcop', or 'sweep'."""
        from faebryk.library.Simulations import (
            SimulationAC,
            SimulationDCOP,
            SimulationSweep,
            SimulationTransient,
        )

        owner = self.get_owner()
        if isinstance(owner, SimulationTransient):
            return "transient"
        elif isinstance(owner, SimulationSweep):
            return "sweep"
        elif isinstance(owner, SimulationAC):
            return "ac"
        elif isinstance(owner, SimulationDCOP):
            return "dcop"
        return "transient"  # default

    # --- Delegating getters (access owning node's fields) ---
    def get_spice(self) -> str | None:
        return self.get_owner().get_spice()

    def get_extra_spice(self) -> list[str]:
        return self.get_owner().get_extra_spice()

    def get_remove_elements(self) -> list[str]:
        return self.get_owner().get_remove_elements()

    # --- Result caching ---
    def store_result(self, result: object, net_aliases: dict | None = None) -> None:
        self._result = result
        self._net_aliases = net_aliases

    def get_result(self) -> object:
        return self._result

    def get_net_aliases(self) -> dict | None:
        return self._net_aliases
