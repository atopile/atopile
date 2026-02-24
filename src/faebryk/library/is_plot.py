# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class is_plot(fabll.Node):
    """Trait marking a node as a plot. Provides uniform metadata access."""

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def get_owner(self) -> fabll.Node:
        return fabll.Traits.bind(self).get_obj(fabll.Node)

    def _str_field(self, name: str) -> str | None:
        owner = self.get_owner()
        try:
            return getattr(owner, name).get().try_extract_singleton()
        except Exception:
            return None

    def get_title(self) -> str | None:
        return self._str_field("title")

    def get_x(self) -> str | None:
        return self._str_field("x")

    def get_y(self) -> str | None:
        return self._str_field("y")

    def get_y_secondary(self) -> str | None:
        return self._str_field("y_secondary")

    def get_color(self) -> str | None:
        return self._str_field("color")

    def get_simulation(self) -> str | None:
        return self._str_field("simulation")

    def get_plot_limits(self) -> str | None:
        return self._str_field("plot_limits")
