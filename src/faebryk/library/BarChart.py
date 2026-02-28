# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class BarChart(fabll.Node):
    """Declarative bar chart: x=sweep param, y=measurement(net).

    Usage in ato::

        plot_bar = new BarChart
        plot_bar.title = "Peak-to-Peak vs Capacitance"
        plot_bar.x = "COUT"
        plot_bar.y = "peak_to_peak(dut.power_out.hv)"

        req.required_plot = "plot_bar"
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_plot = fabll.Traits.MakeEdge(F.is_plot.MakeChild())
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    title = F.Parameters.StringParameter.MakeChild()
    x = F.Parameters.StringParameter.MakeChild()   # sweep param name
    y = F.Parameters.StringParameter.MakeChild()    # "measurement(net)"
    simulation = F.Parameters.StringParameter.MakeChild()    # simulation name override
    plot_limits = F.Parameters.StringParameter.MakeChild()   # "true" (default) or "false"

    def get_title(self) -> str | None:
        try:
            return self.title.get().try_extract_singleton()
        except Exception:
            return None

    def get_x(self) -> str | None:
        try:
            return self.x.get().try_extract_singleton()
        except Exception:
            return None

    def get_y(self) -> str | None:
        try:
            return self.y.get().try_extract_singleton()
        except Exception:
            return None

    def get_simulation(self) -> str | None:
        try:
            return self.simulation.get().try_extract_singleton()
        except Exception:
            return None
