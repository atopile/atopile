# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class LineChart(fabll.Node):
    """Declarative line chart: x/y/color specify data axes.

    Usage in ato::

        plot_vout = new LineChart
        plot_vout.title = "Output Voltage Startup"
        plot_vout.x = "time"
        plot_vout.y = "dut.power_out.hv"

        req_001 = new Requirement
        req_001.required_plot = "plot_vout"
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_plot = fabll.Traits.MakeEdge(F.is_plot.MakeChild())
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    title = F.Parameters.StringParameter.MakeChild()
    x = F.Parameters.StringParameter.MakeChild()              # "time", "frequency", "dut.param"
    y = F.Parameters.StringParameter.MakeChild()               # "dut.net", "measurement(net)"
    y_secondary = F.Parameters.StringParameter.MakeChild()     # secondary y-axis signal
    color = F.Parameters.StringParameter.MakeChild()           # "dut" or omitted
    simulation = F.Parameters.StringParameter.MakeChild()      # simulation name override
    plot_limits = F.Parameters.StringParameter.MakeChild()     # "true" (default) or "false"
    y_range = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)  # y-axis range

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

    def get_y_secondary(self) -> str | None:
        try:
            return self.y_secondary.get().try_extract_singleton()
        except Exception:
            return None

    def get_color(self) -> str | None:
        try:
            return self.color.get().try_extract_singleton()
        except Exception:
            return None

    def get_simulation(self) -> str | None:
        try:
            return self.simulation.get().try_extract_singleton()
        except Exception:
            return None
