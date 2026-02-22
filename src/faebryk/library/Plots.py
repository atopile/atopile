# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import faebryk.core.node as fabll
import faebryk.library._F as F

if TYPE_CHECKING:
    import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# Plot context — lightweight data passed from the verification pipeline
# to avoid circular imports with requirement.py
# ---------------------------------------------------------------------------


@dataclass
class PlotContext:
    """Requirement context for annotating plots with pass/fail info.

    Built by the verification pipeline from RequirementResult + Requirement.
    Avoids circular dependency between library/Plots.py and exporters/.
    """

    actual: float
    passed: bool
    min_val: float
    max_val: float
    measurement: str
    req_name: str = ""
    display_net: str = ""
    settling_tolerance: float | None = None
    context_keys: list[str] = field(default_factory=list)
    diff_ref_key: str | None = None
    sweep_param_name: str = ""
    sweep_param_unit: str = ""
    measurement_unit: str = ""
    signal_key: str = ""


# ---------------------------------------------------------------------------
# Utility functions (moved from exporters/simulation/requirement.py)
# ---------------------------------------------------------------------------

_SI_PREFIXES = [
    (1e-15, "f"),
    (1e-12, "p"),
    (1e-9, "n"),
    (1e-6, "u"),
    (1e-3, "m"),
    (1.0, ""),
    (1e3, "k"),
    (1e6, "M"),
    (1e9, "G"),
]


def format_eng(value: float, unit: str) -> str:
    """Format a value in engineering notation with SI prefix.

    Examples:
        format_eng(7.5, "V")   -> "7.500 V"
        format_eng(0.3, "s")   -> "300.0 ms"
        format_eng(12.5, "%")  -> "12.50%"
    """
    if unit == "%":
        return f"{value:.2f}%"

    abs_val = abs(value)
    if abs_val == 0:
        return f"0.000 {unit}"

    for threshold, prefix in _SI_PREFIXES:
        if abs_val < threshold * 1000:
            scaled = value / threshold
            return f"{scaled:.4g} {prefix}{unit}"

    # Fallback for very large values
    return f"{value:.4g} {unit}"


def auto_scale_time(t_max: float) -> tuple[float, str]:
    """Choose time unit scale factor and label."""
    if t_max <= 0:
        return 1.0, "s"
    if t_max < 1e-6:
        return 1e9, "ns"
    if t_max < 1e-3:
        return 1e6, "us"
    if t_max < 1.0:
        return 1e3, "ms"
    return 1.0, "s"


def signal_unit(key: str) -> str:
    """Infer unit type from signal key: 'V' for voltage, 'A' for current."""
    if key.startswith("i("):
        return "A"
    return "V"


_CTX_COLORS = ["orange", "green", "purple", "brown"]


def _compute_settling_milestones(
    signal_data: list[float],
    time_data: list[float],
    final: float,
) -> list[tuple[float, float, str]]:
    """Compute 90%, 95%, 99% settling times.

    Returns list of (time, tolerance_pct, label) tuples.
    """
    if final == 0:
        return []

    milestones = []
    for pct, tol in [(90, 0.10), (95, 0.05), (99, 0.01)]:
        band = abs(final * tol)
        settled_time = 0.0
        for i in range(len(signal_data) - 1, -1, -1):
            if abs(signal_data[i] - final) > band:
                settled_time = time_data[i] if i < len(time_data) else float("inf")
                break
        if settled_time != float("inf"):
            milestones.append((settled_time, pct, f"{pct}%"))
    return milestones


def _interpolate_at_freq(
    freq: list[float], values: list[float], target: float
) -> float:
    """Log-frequency interpolation of values at target frequency."""
    if not freq or target <= 0:
        return float("nan")
    if target <= freq[0]:
        return values[0]
    if target >= freq[-1]:
        return values[-1]
    for i in range(len(freq) - 1):
        if freq[i] <= target <= freq[i + 1]:
            log_f0 = math.log10(freq[i])
            log_f1 = math.log10(freq[i + 1])
            log_ft = math.log10(target)
            t = (log_ft - log_f0) / (log_f1 - log_f0) if log_f1 != log_f0 else 0.0
            return values[i] + t * (values[i + 1] - values[i])
    return values[-1]


# ---------------------------------------------------------------------------
# Marker base class
# ---------------------------------------------------------------------------


class PlotBase(fabll.Node):
    """Marker base for Python isinstance() checks on plot nodes.

    Not intended for direct use in ato — use LineChart or BodePlotChart.
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    title = F.Parameters.StringParameter.MakeChild()

    def get_title(self) -> str | None:
        try:
            return self.title.get().try_extract_singleton()
        except (AttributeError, Exception):
            return None


# ---------------------------------------------------------------------------
# LineChart — time-domain plot with measurement-specific render methods
# ---------------------------------------------------------------------------


class LineChart(fabll.Node):
    """Time-domain line chart (flat — no inheritance from PlotBase).

    Usage in ato::

        plot = new Plots.LineChart
        plot.y ~ power_out.hv
        plot.title = "Output Voltage"

    Rendering::

        plot.render(tran_data, "v(power_out_hv)", path, ctx=PlotContext(...))
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    title = F.Parameters.StringParameter.MakeChild()
    y = F.Electrical.MakeChild()
    x_label = F.Parameters.StringParameter.MakeChild()
    y_label = F.Parameters.StringParameter.MakeChild()

    def get_title(self) -> str | None:
        try:
            return self.title.get().try_extract_singleton()
        except (AttributeError, Exception):
            return None

    # -------------------------------------------------------------------
    # Public render entry point
    # -------------------------------------------------------------------

    def render(
        self,
        tran_data: Any,
        net_key: str,
        path: str | Path,
        ctx: PlotContext | None = None,
    ) -> Path | None:
        """Render this chart to an HTML file.

        If *ctx* is provided, dispatches to a measurement-specific renderer
        that adds pass/fail annotations, limit lines, etc.
        Otherwise renders a basic time-domain line plot.
        """
        try:
            import plotly  # noqa: F401
        except ImportError:
            return None

        path = Path(path)

        if ctx is not None:
            method = getattr(self, f"_render_{ctx.measurement}", None)
            if method:
                return method(tran_data, net_key, path, ctx)

        return self._render_basic(tran_data, net_key, path, ctx)

    # -------------------------------------------------------------------
    # Figure building helpers
    # -------------------------------------------------------------------

    def _build_figure(
        self,
        tran_data: Any,
        net_key: str,
        ctx: PlotContext | None = None,
    ) -> tuple[
        go.Figure,
        list[float],  # time_scaled
        list[float],  # nut_signal
        str,  # nut_unit
        float,  # scale
        str,  # t_unit
        bool,  # has_secondary_y
    ]:
        """Create figure with NUT signal + context signals."""
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        nut_unit = signal_unit(net_key)

        # Auto-scale time axis
        t_max = tran_data.time[-1] if tran_data.time else 1.0
        scale, t_unit = auto_scale_time(t_max)
        time_scaled = [t * scale for t in tran_data.time]

        # Compute differential signal if diff_ref is set
        diff_ref_key = ctx.diff_ref_key if ctx else None
        if diff_ref_key:
            ref_key = (
                f"v({diff_ref_key})"
                if not diff_ref_key.startswith(("v(", "i("))
                else diff_ref_key
            )
            nut_signal = [
                a - b for a, b in zip(tran_data[net_key], tran_data[ref_key])
            ]
            display_key = f"{net_key} - {ref_key}"
        else:
            nut_signal = list(tran_data[net_key])
            display_key = net_key

        # Partition context signals by unit
        context_keys = ctx.context_keys if ctx else []
        same_unit: list[str] = []
        diff_unit: list[str] = []
        for ctx_key in context_keys:
            if ctx_key in tran_data:
                if signal_unit(ctx_key) == nut_unit:
                    same_unit.append(ctx_key)
                else:
                    diff_unit.append(ctx_key)

        has_secondary = bool(diff_unit)
        if has_secondary:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
        else:
            fig = go.Figure()

        # NUT signal (thick blue)
        nut_label = ctx.display_net if ctx and ctx.display_net else display_key
        fig.add_trace(
            go.Scatter(
                x=time_scaled,
                y=nut_signal,
                mode="lines",
                name=nut_label,
                line=dict(color="royalblue", width=3),
            ),
            secondary_y=False if has_secondary else None,
        )

        # Same-unit context signals (thin, left axis — hidden by default)
        for i, ctx_key in enumerate(same_unit):
            c = _CTX_COLORS[i % len(_CTX_COLORS)]
            fig.add_trace(
                go.Scatter(
                    x=time_scaled,
                    y=list(tran_data[ctx_key]),
                    mode="lines",
                    name=ctx_key,
                    line=dict(color=c, width=1.2),
                    visible="legendonly",
                ),
                secondary_y=False if has_secondary else None,
            )

        unit_label = (
            f"Voltage ({nut_unit})" if nut_unit == "V" else f"Current ({nut_unit})"
        )

        # Different-unit context signals (right axis — hidden by default)
        if has_secondary:
            for i, ctx_key in enumerate(diff_unit):
                c = _CTX_COLORS[(i + len(same_unit)) % len(_CTX_COLORS)]
                fig.add_trace(
                    go.Scatter(
                        x=time_scaled,
                        y=list(tran_data[ctx_key]),
                        mode="lines",
                        name=ctx_key,
                        line=dict(color=c, width=1.2),
                        visible="legendonly",
                    ),
                    secondary_y=True,
                )
            diff_unit_type = signal_unit(diff_unit[0])
            right_label = (
                f"Voltage ({diff_unit_type})"
                if diff_unit_type == "V"
                else f"Current ({diff_unit_type})"
            )
            fig.update_yaxes(title_text=right_label, secondary_y=True)

        fig.update_xaxes(title_text=f"Time ({t_unit})")
        fig.update_yaxes(
            title_text=unit_label,
            secondary_y=False if has_secondary else None,
        )

        return fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_secondary

    @staticmethod
    def _add_limit_labels(
        fig: go.Figure,
        min_val: float,
        max_val: float,
        unit: str,
    ) -> None:
        """Add horizontal limit lines with text annotations."""
        fig.add_hline(y=min_val, line=dict(color="red", dash="dot", width=2))
        fig.add_hline(y=max_val, line=dict(color="red", dash="dot", width=2))

        fig.add_annotation(
            x=0.02, y=min_val, xref="paper", yref="y",
            text=f"LSL = {format_eng(min_val, unit)}",
            showarrow=False, font=dict(color="red", size=10),
            xanchor="left", yanchor="bottom",
        )
        fig.add_annotation(
            x=0.98, y=max_val, xref="paper", yref="y",
            text=f"USL = {format_eng(max_val, unit)}",
            showarrow=False, font=dict(color="red", size=10),
            xanchor="right", yanchor="top",
        )

    @staticmethod
    def _add_time_limit_labels(
        fig: go.Figure,
        min_val: float,
        max_val: float,
        scale: float,
        t_unit: str,
    ) -> None:
        """Add vertical limit lines at time values."""
        min_scaled = min_val * scale
        max_scaled = max_val * scale
        fig.add_vline(x=min_scaled, line=dict(color="red", dash="dot", width=2))
        fig.add_vline(x=max_scaled, line=dict(color="red", dash="dot", width=2))

        fig.add_annotation(
            x=min_scaled, y=0.98, xref="x", yref="paper",
            text=f"LSL = {format_eng(min_val, 's')}",
            showarrow=False, font=dict(color="red", size=10),
            xanchor="right", yanchor="top", textangle=-90,
        )
        fig.add_annotation(
            x=max_scaled, y=0.98, xref="x", yref="paper",
            text=f"USL = {format_eng(max_val, 's')}",
            showarrow=False, font=dict(color="red", size=10),
            xanchor="left", yanchor="top", textangle=-90,
        )

    def _finalize(
        self,
        fig: go.Figure,
        title: str,
        subtitle: str,
        time_scaled: list[float],
        path: Path,
    ) -> Path:
        """Apply layout, save as HTML."""
        t_margin = 0.0
        if time_scaled:
            t_span = time_scaled[-1] - time_scaled[0]
            t_margin = 0.05 * t_span

        fig.update_layout(
            title=dict(
                text=f"<b>{title}</b><br><span style='font-size:12px;color:gray'>"
                     f"{subtitle}</span>",
                x=0.5,
            ),
            width=900,
            height=500,
            template="plotly_white",
            showlegend=True,
            legend=dict(
                font=dict(size=10), x=1.02, y=1,
                xanchor="left", yanchor="top",
            ),
        )

        if time_scaled:
            fig.update_xaxes(
                range=[
                    time_scaled[0] - t_margin,
                    time_scaled[-1] + t_margin,
                ]
            )

        self._last_figs = [fig]
        fig.write_html(str(path), include_plotlyjs="cdn")
        return path

    # -------------------------------------------------------------------
    # Render: basic (no measurement annotations)
    # -------------------------------------------------------------------

    def _render_basic(
        self, tran_data: Any, net_key: str, path: Path, ctx: PlotContext | None,
    ) -> Path:
        fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
            self._build_figure(tran_data, net_key, ctx)
        )
        title = self.get_title() or (ctx.req_name if ctx else net_key)
        subtitle = f"Signal: {net_key}"
        return self._finalize(fig, title, subtitle, time_scaled, path)

    # -------------------------------------------------------------------
    # Render: final_value
    # -------------------------------------------------------------------

    def _render_final_value(
        self, tran_data: Any, net_key: str, path: Path, ctx: PlotContext,
    ) -> Path:
        import plotly.graph_objects as go

        fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
            self._build_figure(tran_data, net_key, ctx)
        )

        min_val, max_val, actual = ctx.min_val, ctx.max_val, ctx.actual

        # Pass band shading
        fig.add_hrect(
            y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
            line_width=0,
        )

        self._add_limit_labels(fig, min_val, max_val, nut_unit)

        # Actual value line and marker
        marker_color = "#2ecc71" if ctx.passed else "#e74c3c"
        fig.add_hline(
            y=actual,
            line=dict(color=marker_color, dash="dash", width=1.5),
            opacity=0.7,
        )
        fig.add_trace(go.Scatter(
            x=[time_scaled[-1]], y=[actual],
            mode="markers+text",
            marker=dict(color=marker_color, size=10),
            text=[f"Actual = {format_eng(actual, nut_unit)}"],
            textposition="top left",
            textfont=dict(color=marker_color, size=11),
            showlegend=False,
        ))

        # Margin annotation
        margin_lo = abs(actual - min_val)
        margin_hi = abs(max_val - actual)
        nearest = min(margin_lo, margin_hi)
        span = max_val - min_val
        margin_pct = (nearest / span * 100) if span > 0 else 0
        fig.add_annotation(
            x=0.02, y=0.02, xref="paper", yref="paper",
            text=f"Margin: {margin_pct:.1f}% to nearest limit",
            showarrow=False, font=dict(color="gray", size=10),
            xanchor="left", yanchor="bottom",
        )

        title = self.get_title() or ctx.req_name
        subtitle = (
            f"Measurement: final_value | Actual: {format_eng(actual, nut_unit)}"
        )
        return self._finalize(fig, title, subtitle, time_scaled, path)

    # -------------------------------------------------------------------
    # Render: average
    # -------------------------------------------------------------------

    def _render_average(
        self, tran_data: Any, net_key: str, path: Path, ctx: PlotContext,
    ) -> Path:
        import plotly.graph_objects as go

        fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
            self._build_figure(tran_data, net_key, ctx)
        )

        min_val, max_val, avg = ctx.min_val, ctx.max_val, ctx.actual

        # Pass band shading
        fig.add_hrect(
            y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
            line_width=0,
        )
        self._add_limit_labels(fig, min_val, max_val, nut_unit)

        # Average line
        fig.add_hline(
            y=avg,
            line=dict(color="royalblue", dash="dash", width=1.5),
            opacity=0.7,
        )
        fig.add_annotation(
            x=time_scaled[len(time_scaled) // 2], y=avg,
            text=f"<b>Avg = {format_eng(avg, nut_unit)}</b>",
            showarrow=False, font=dict(color="royalblue", size=11),
            yshift=12,
        )

        # Deviation fill
        fig.add_trace(go.Scatter(
            x=time_scaled, y=[avg] * len(nut_signal),
            mode="lines", line=dict(width=0), showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=time_scaled, y=list(nut_signal),
            mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor="rgba(65,105,225,0.15)", showlegend=False,
        ))

        # Std dev info
        mean_sq_dev = sum((x - avg) ** 2 for x in nut_signal) / len(nut_signal)
        std_dev = math.sqrt(mean_sq_dev)
        fig.add_annotation(
            x=0.02, y=0.02, xref="paper", yref="paper",
            text=f"Std Dev: {format_eng(std_dev, nut_unit)}",
            showarrow=False, font=dict(color="gray", size=10),
            xanchor="left", yanchor="bottom",
        )

        title = self.get_title() or ctx.req_name
        subtitle = f"Measurement: average | Actual: {format_eng(avg, nut_unit)}"
        return self._finalize(fig, title, subtitle, time_scaled, path)

    # -------------------------------------------------------------------
    # Render: settling_time
    # -------------------------------------------------------------------

    def _render_settling_time(
        self, tran_data: Any, net_key: str, path: Path, ctx: PlotContext,
    ) -> Path:
        import plotly.graph_objects as go

        fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
            self._build_figure(tran_data, net_key, ctx)
        )

        min_val, max_val, actual = ctx.min_val, ctx.max_val, ctx.actual
        final = nut_signal[-1] if nut_signal else 0.0
        tol = ctx.settling_tolerance or 0.01
        band = abs(final * tol)

        # Final value reference line
        fig.add_hline(
            y=final, line=dict(color="gray", dash="dash", width=1.2), opacity=0.7,
        )
        fig.add_annotation(
            x=time_scaled[-1], y=final,
            text=f"Final = {format_eng(final, nut_unit)}",
            showarrow=True, arrowhead=0, ax=-80, ay=-15,
            font=dict(color="gray", size=11),
        )

        # Settling tolerance band
        fig.add_hline(
            y=final + band, line=dict(color="gray", dash="dot", width=1),
            opacity=0.5,
        )
        fig.add_hline(
            y=final - band, line=dict(color="gray", dash="dot", width=1),
            opacity=0.5,
        )
        fig.add_hrect(
            y0=final - band, y1=final + band, fillcolor="green",
            opacity=0.08, line_width=0,
        )
        fig.add_annotation(
            x=0.98, y=final + band, xref="paper", yref="y",
            text=f"+/-{tol * 100:.1f}% band",
            showarrow=False, font=dict(color="green", size=9),
            xanchor="left", yanchor="bottom",
        )

        # Vertical time limit lines
        self._add_time_limit_labels(fig, min_val, max_val, scale, t_unit)

        # Actual settling time vertical line
        actual_scaled = actual * scale
        settle_color = "#2ecc71" if ctx.passed else "#e74c3c"
        fig.add_vline(
            x=actual_scaled,
            line=dict(color=settle_color, dash="dash", width=2),
            opacity=0.8,
        )
        fig.add_annotation(
            x=actual_scaled, y=0.85, xref="x", yref="paper",
            text=f"<b>Settled @ {format_eng(actual, 's')}</b>",
            showarrow=False, font=dict(color=settle_color, size=11),
            textangle=-90, xanchor="right", yanchor="top",
        )

        # Settling milestones (90%, 95%, 99%)
        milestones = _compute_settling_milestones(
            nut_signal, [t / scale for t in time_scaled], final
        )
        milestone_colors = ["#f39c12", "#e67e22", "#8e44ad"]
        for idx, (m_time, m_pct, m_label) in enumerate(milestones):
            m_time_scaled = m_time * scale
            m_idx = 0
            for j, t in enumerate(time_scaled):
                if t >= m_time_scaled:
                    m_idx = j
                    break
            m_color = milestone_colors[idx % len(milestone_colors)]
            fig.add_trace(go.Scatter(
                x=[m_time_scaled], y=[nut_signal[m_idx]],
                mode="markers",
                marker=dict(color=m_color, size=9, symbol="diamond"),
                showlegend=False,
            ))
            fig.add_annotation(
                x=m_time_scaled, y=nut_signal[m_idx],
                text=f"<b>{m_label} @ {format_eng(m_time, 's')}</b>",
                showarrow=True, arrowhead=2, arrowcolor=m_color,
                ax=10, ay=-(10 + idx * 18),
                font=dict(color=m_color, size=9),
            )

        title = self.get_title() or ctx.req_name
        subtitle = f"Measurement: settling_time | Actual: {format_eng(actual, 's')}"
        return self._finalize(fig, title, subtitle, time_scaled, path)

    # -------------------------------------------------------------------
    # Render: peak_to_peak
    # -------------------------------------------------------------------

    def _render_peak_to_peak(
        self, tran_data: Any, net_key: str, path: Path, ctx: PlotContext,
    ) -> Path:
        import plotly.graph_objects as go

        fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
            self._build_figure(tran_data, net_key, ctx)
        )

        min_val, max_val, actual = ctx.min_val, ctx.max_val, ctx.actual
        peak_val = max(nut_signal)
        trough_val = min(nut_signal)
        peak_idx = nut_signal.index(peak_val)
        trough_idx = nut_signal.index(trough_val)

        # Peak and trough markers
        fig.add_trace(go.Scatter(
            x=[time_scaled[peak_idx]], y=[peak_val],
            mode="markers",
            marker=dict(color="#e74c3c", size=12, symbol="triangle-up"),
            name=f"Peak = {format_eng(peak_val, nut_unit)}",
        ))
        fig.add_trace(go.Scatter(
            x=[time_scaled[trough_idx]], y=[trough_val],
            mode="markers",
            marker=dict(color="#3498db", size=12, symbol="triangle-down"),
            name=f"Trough = {format_eng(trough_val, nut_unit)}",
        ))

        # Horizontal lines at peak and trough
        fig.add_hline(
            y=peak_val, line=dict(color="#e74c3c", dash="dot", width=1),
            opacity=0.4,
        )
        fig.add_hline(
            y=trough_val, line=dict(color="#3498db", dash="dot", width=1),
            opacity=0.4,
        )

        # P-P label at midpoint
        mid_y = (peak_val + trough_val) / 2
        arrow_x = time_scaled[-1] * 0.95
        fig.add_annotation(
            x=arrow_x, y=peak_val, ax=arrow_x, ay=trough_val,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=3, arrowsize=1.5, arrowwidth=2,
            arrowcolor="black", text="",
        )
        fig.add_annotation(
            x=arrow_x, y=mid_y,
            text=f"<b>P-P: {format_eng(actual, nut_unit)}</b>",
            showarrow=False, font=dict(size=11),
            xanchor="right",
            bgcolor="rgba(255,255,255,0.8)", bordercolor="gray", borderwidth=1,
        )

        # Peak/trough time annotations
        peak_time = time_scaled[peak_idx] / scale
        trough_time = time_scaled[trough_idx] / scale
        fig.add_annotation(
            x=time_scaled[peak_idx], y=peak_val,
            text=f"@ {format_eng(peak_time, 's')}",
            showarrow=True, arrowhead=0, ax=10, ay=-15,
            font=dict(color="#e74c3c", size=9),
        )
        fig.add_annotation(
            x=time_scaled[trough_idx], y=trough_val,
            text=f"@ {format_eng(trough_time, 's')}",
            showarrow=True, arrowhead=0, ax=10, ay=15,
            font=dict(color="#3498db", size=9),
        )

        # Info box
        margin_lo = abs(actual - min_val)
        margin_hi = abs(max_val - actual)
        nearest = min(margin_lo, margin_hi)
        span = max_val - min_val
        margin_pct = (nearest / span * 100) if span > 0 else 0
        info_text = (
            f"P-P: {format_eng(actual, nut_unit)}<br>"
            f"Limit: [{format_eng(min_val, nut_unit)}, "
            f"{format_eng(max_val, nut_unit)}]<br>"
            f"Margin: {margin_pct:.1f}%"
        )
        fig.add_annotation(
            x=0.02, y=0.02, xref="paper", yref="paper",
            text=info_text, showarrow=False,
            font=dict(color="gray", size=10, family="monospace"),
            xanchor="left", yanchor="bottom", align="left",
        )

        title = self.get_title() or ctx.req_name
        subtitle = (
            f"Measurement: peak_to_peak | Actual: {format_eng(actual, nut_unit)}"
        )
        return self._finalize(fig, title, subtitle, time_scaled, path)

    # -------------------------------------------------------------------
    # Render: overshoot
    # -------------------------------------------------------------------

    def _render_overshoot(
        self, tran_data: Any, net_key: str, path: Path, ctx: PlotContext,
    ) -> Path:
        import plotly.graph_objects as go

        fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
            self._build_figure(tran_data, net_key, ctx)
        )

        min_val, max_val, actual = ctx.min_val, ctx.max_val, ctx.actual
        final = nut_signal[-1] if nut_signal else 0.0
        peak_val = max(nut_signal)
        peak_idx = nut_signal.index(peak_val)

        # Final value line
        fig.add_hline(
            y=final, line=dict(color="gray", dash="dash", width=1.5), opacity=0.7,
        )
        fig.add_annotation(
            x=time_scaled[-1], y=final,
            text=f"Final = {format_eng(final, nut_unit)}",
            showarrow=True, arrowhead=0, ax=-80, ay=-15,
            font=dict(color="gray", size=11),
        )

        # Max allowed overshoot line
        if final != 0:
            max_os_voltage = final * (1 + max_val / 100.0)
            fig.add_hline(
                y=max_os_voltage,
                line=dict(color="red", dash="dash", width=1.2), opacity=0.6,
            )
            fig.add_annotation(
                x=0.02, y=max_os_voltage, xref="paper", yref="y",
                text=f"Max OS = {max_val:.1f}%",
                showarrow=False, font=dict(color="red", size=10),
                xanchor="left", yanchor="bottom",
            )

        # Peak marker
        fig.add_trace(go.Scatter(
            x=[time_scaled[peak_idx]], y=[peak_val],
            mode="markers",
            marker=dict(color="#e74c3c", size=10),
            showlegend=False,
        ))

        # Overshoot arrow from final to peak
        fig.add_annotation(
            x=time_scaled[peak_idx], y=peak_val,
            ax=time_scaled[peak_idx], ay=final,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=3, arrowsize=1.5, arrowwidth=1.5,
            arrowcolor="#e74c3c", text="",
        )
        fig.add_annotation(
            x=time_scaled[peak_idx], y=(peak_val + final) / 2,
            text=f"<b>OS = {actual:.2f}%</b>",
            showarrow=False, font=dict(color="#e74c3c", size=11),
            xanchor="left", xshift=8,
        )

        # Red fill where signal exceeds final
        fill_y_upper = [s if s > final else final for s in nut_signal]
        fig.add_trace(go.Scatter(
            x=time_scaled, y=[final] * len(nut_signal),
            mode="lines", line=dict(width=0), showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=time_scaled, y=fill_y_upper,
            mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor="rgba(231,76,60,0.15)", showlegend=False,
        ))

        # Info box
        info_text = (
            f"Overshoot: {actual:.2f}%<br>"
            f"Limit: [{min_val:.1f}%, {max_val:.1f}%]<br>"
            f"Peak: {format_eng(peak_val, nut_unit)}<br>"
            f"Final: {format_eng(final, nut_unit)}"
        )
        fig.add_annotation(
            x=0.02, y=0.02, xref="paper", yref="paper",
            text=info_text, showarrow=False,
            font=dict(color="gray", size=10, family="monospace"),
            xanchor="left", yanchor="bottom", align="left",
        )

        title = self.get_title() or ctx.req_name
        subtitle = f"Measurement: overshoot | Actual: {actual:.2f}%"
        return self._finalize(fig, title, subtitle, time_scaled, path)

    # -------------------------------------------------------------------
    # Render: rms
    # -------------------------------------------------------------------

    def _render_rms(
        self, tran_data: Any, net_key: str, path: Path, ctx: PlotContext,
    ) -> Path:
        import plotly.graph_objects as go  # noqa: F811

        fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
            self._build_figure(tran_data, net_key, ctx)
        )

        min_val, max_val = ctx.min_val, ctx.max_val
        rms = ctx.actual
        mean = sum(nut_signal) / len(nut_signal) if nut_signal else 0.0
        peak = max(abs(s) for s in nut_signal) if nut_signal else 0.0
        crest = peak / rms if rms > 0 else float("inf")

        # Pass band shading
        fig.add_hrect(
            y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
            line_width=0,
        )
        self._add_limit_labels(fig, min_val, max_val, nut_unit)

        # RMS line
        fig.add_hline(
            y=rms, line=dict(color="royalblue", dash="dash", width=1.5),
            opacity=0.7,
        )
        fig.add_annotation(
            x=time_scaled[len(time_scaled) // 2], y=rms,
            text=f"<b>RMS = {format_eng(rms, nut_unit)}</b>",
            showarrow=False, font=dict(color="royalblue", size=11),
            yshift=12,
        )

        # Mean line (muted)
        fig.add_hline(
            y=mean, line=dict(color="gray", dash="dot", width=1.2), opacity=0.6,
        )
        fig.add_annotation(
            x=time_scaled[len(time_scaled) // 3], y=mean,
            text=f"Mean = {format_eng(mean, nut_unit)}",
            showarrow=False, font=dict(color="gray", size=10),
            yshift=-12,
        )

        # Info box
        info_text = (
            f"RMS: {format_eng(rms, nut_unit)}<br>"
            f"Mean: {format_eng(mean, nut_unit)}<br>"
            f"Peak: {format_eng(peak, nut_unit)}<br>"
            f"Crest Factor: {crest:.2f}"
        )
        fig.add_annotation(
            x=0.02, y=0.02, xref="paper", yref="paper",
            text=info_text, showarrow=False,
            font=dict(color="gray", size=10, family="monospace"),
            xanchor="left", yanchor="bottom", align="left",
        )

        title = self.get_title() or ctx.req_name
        subtitle = f"Measurement: rms | Actual: {format_eng(rms, nut_unit)}"
        return self._finalize(fig, title, subtitle, time_scaled, path)

    # -------------------------------------------------------------------
    # Render: frequency
    # -------------------------------------------------------------------

    def _render_frequency(
        self, tran_data: Any, net_key: str, path: Path, ctx: PlotContext,
    ) -> Path:
        import plotly.graph_objects as go

        fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
            self._build_figure(tran_data, net_key, ctx)
        )

        min_val, max_val, actual = ctx.min_val, ctx.max_val, ctx.actual

        # Mark rising-edge crossings
        sig_min = min(nut_signal)
        sig_max = max(nut_signal)
        threshold = (sig_min + sig_max) / 2.0

        crossing_times: list[float] = []
        for i in range(len(nut_signal) - 1):
            if nut_signal[i] <= threshold < nut_signal[i + 1]:
                frac = (threshold - nut_signal[i]) / (
                    nut_signal[i + 1] - nut_signal[i]
                )
                t_cross = (
                    time_scaled[i]
                    + frac * (time_scaled[i + 1] - time_scaled[i])
                )
                crossing_times.append(t_cross)

        # Threshold line
        fig.add_hline(
            y=threshold, line=dict(color="gray", dash="dot", width=1),
            opacity=0.4,
        )

        marker_color = "#2ecc71" if ctx.passed else "#e74c3c"

        # Highlight one cycle
        if len(crossing_times) >= 2:
            mid = len(crossing_times) // 2
            t0 = crossing_times[mid - 1]
            t1 = crossing_times[mid]
            period = (t1 - t0) / scale

            fig.add_trace(go.Scatter(
                x=[t0, t1], y=[threshold, threshold],
                mode="markers",
                marker=dict(
                    color=marker_color, size=10, symbol="circle",
                    line=dict(color="white", width=2),
                ),
                name="Measured edges",
                showlegend=True,
            ))

            arrow_y = sig_max * 0.95
            fig.add_shape(
                type="line",
                x0=t0, x1=t1, y0=arrow_y, y1=arrow_y,
                line=dict(color="black", width=1.5),
            )
            fig.add_shape(
                type="line",
                x0=t0, x1=t0, y0=threshold, y1=arrow_y,
                line=dict(color="black", width=1, dash="dot"),
            )
            fig.add_shape(
                type="line",
                x0=t1, x1=t1, y0=threshold, y1=arrow_y,
                line=dict(color="black", width=1, dash="dot"),
            )

            fig.add_annotation(
                x=(t0 + t1) / 2, y=arrow_y,
                text=f"T = {format_eng(period, 's')}",
                showarrow=False, font=dict(color="black", size=11),
                yshift=12,
            )

        # Info box
        info_text = (
            f"Frequency: {format_eng(actual, 'Hz')}<br>"
            f"Limit: [{format_eng(min_val, 'Hz')}, "
            f"{format_eng(max_val, 'Hz')}]<br>"
            f"Cycles counted: {len(crossing_times)}"
        )
        fig.add_annotation(
            x=0.02, y=0.02, xref="paper", yref="paper",
            text=info_text, showarrow=False,
            font=dict(color=marker_color, size=11, family="monospace"),
            xanchor="left", yanchor="bottom", align="left",
            bgcolor="rgba(255,255,255,0.85)", bordercolor=marker_color,
            borderwidth=1, borderpad=4,
        )

        title = self.get_title() or ctx.req_name
        subtitle = f"Measurement: frequency | Actual: {format_eng(actual, 'Hz')}"
        return self._finalize(fig, title, subtitle, time_scaled, path)

    # -------------------------------------------------------------------
    # Render: sweep
    # -------------------------------------------------------------------

    def _render_sweep(
        self, tran_data: Any, net_key: str, path: Path, ctx: PlotContext,
    ) -> Path:
        import plotly.graph_objects as go

        nut_unit = signal_unit(net_key)
        nut_signal = list(tran_data[net_key])
        min_val, max_val, actual = ctx.min_val, ctx.max_val, ctx.actual

        # X-axis: first context signal (the swept variable)
        if not ctx.context_keys:
            return self._render_final_value(tran_data, net_key, path, ctx)

        sweep_key = ctx.context_keys[0]
        sweep_signal = list(tran_data[sweep_key])
        sweep_unit = signal_unit(sweep_key)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=sweep_signal, y=nut_signal,
            mode="lines",
            name=f"{net_key} vs {sweep_key}",
            line=dict(color="royalblue", width=2.5),
        ))

        fig.add_hrect(
            y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
            line_width=0,
        )
        self._add_limit_labels(fig, min_val, max_val, nut_unit)

        # Start/end markers
        fig.add_trace(go.Scatter(
            x=[sweep_signal[0]], y=[nut_signal[0]],
            mode="markers+text",
            marker=dict(color="gray", size=8, symbol="circle"),
            text=["Start"], textposition="top right",
            showlegend=False,
        ))

        marker_color = "#2ecc71" if ctx.passed else "#e74c3c"
        fig.add_trace(go.Scatter(
            x=[sweep_signal[-1]], y=[nut_signal[-1]],
            mode="markers+text",
            marker=dict(color=marker_color, size=10, symbol="circle"),
            text=[f"End = {format_eng(actual, nut_unit)}"],
            textposition="top left",
            textfont=dict(color=marker_color, size=11),
            showlegend=False,
        ))

        sweep_label = (
            f"Voltage ({sweep_unit})" if sweep_unit == "V"
            else f"Current ({sweep_unit})"
        )
        nut_label = (
            f"Voltage ({nut_unit})" if nut_unit == "V"
            else f"Current ({nut_unit})"
        )
        fig.update_xaxes(title_text=f"{sweep_key} — {sweep_label}")
        fig.update_yaxes(title_text=f"{net_key} — {nut_label}")

        title = self.get_title() or ctx.req_name
        subtitle = f"Measurement: sweep | Final: {format_eng(actual, nut_unit)}"

        fig.update_layout(
            title=dict(
                text=f"<b>{title}</b><br><span style='font-size:12px;color:gray'>"
                     f"{subtitle}</span>",
                x=0.5,
            ),
            width=900, height=600,
            template="plotly_white",
            showlegend=True,
            legend=dict(
                font=dict(size=10), x=0.01, y=0.99,
                xanchor="left", yanchor="top",
            ),
        )
        self._last_figs = [fig]
        fig.write_html(str(path), include_plotlyjs="cdn")
        return path


# ---------------------------------------------------------------------------
# BodePlotChart — frequency-domain plot with AC render methods
# ---------------------------------------------------------------------------


class BodePlotChart(fabll.Node):
    """Frequency-domain Bode plot — gain + phase (flat — no inheritance).

    Usage in ato::

        plot = new Plots.BodePlotChart
        plot.signal ~ output
        plot.reference ~ input
        plot.title = "Loop Gain"

    Rendering::

        plot.render(ac_data, "output_net", path, ctx=PlotContext(...),
                    ref_net="input_net")
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    title = F.Parameters.StringParameter.MakeChild()
    signal = F.Electrical.MakeChild()
    reference = F.Electrical.MakeChild()

    def get_title(self) -> str | None:
        try:
            return self.title.get().try_extract_singleton()
        except (AttributeError, Exception):
            return None

    # -------------------------------------------------------------------
    # Public render entry point
    # -------------------------------------------------------------------

    def render(
        self,
        ac_data: Any,
        net_key: str,
        path: str | Path,
        ctx: PlotContext | None = None,
        ref_net: str | None = None,
        measure_freq: float | None = None,
    ) -> Path | None:
        """Render this Bode chart to an HTML file."""
        try:
            import plotly  # noqa: F401
        except ImportError:
            return None

        path = Path(path)

        if ctx is not None:
            method = getattr(self, f"_render_{ctx.measurement}", None)
            if method:
                return method(ac_data, net_key, path, ctx, ref_net, measure_freq)

        return self._render_bode_plot(
            ac_data, net_key, path,
            ctx or PlotContext(
                actual=0, passed=True, min_val=0, max_val=0,
                measurement="bode_plot",
            ),
            ref_net, measure_freq,
        )

    # -------------------------------------------------------------------
    # Finalize helper
    # -------------------------------------------------------------------

    def _finalize_ac(
        self,
        fig: go.Figure,
        title: str,
        subtitle: str,
        path: Path,
    ) -> Path:
        """Apply layout and save an AC plot as HTML."""
        fig.update_layout(
            title=dict(
                text=f"<b>{title}</b><br><span style='font-size:12px;color:gray'>"
                     f"{subtitle}</span>",
                x=0.5,
            ),
            width=900, height=600,
            template="plotly_white",
            showlegend=True,
            legend=dict(
                font=dict(size=10), x=1.02, y=1,
                xanchor="left", yanchor="top",
            ),
        )
        self._last_figs = [fig]
        fig.write_html(str(path), include_plotlyjs="cdn")
        return path

    # -------------------------------------------------------------------
    # Render: gain_db
    # -------------------------------------------------------------------

    def _render_gain_db(
        self, ac_data: Any, net_key: str, path: Path, ctx: PlotContext,
        ref_net: str | None, measure_freq: float | None,
    ) -> Path:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        min_val, max_val = ctx.min_val, ctx.max_val

        # Compute differential signal if diff_ref is set
        diff_ref = ctx.diff_ref_key
        sig_key = ac_data.compute_diff(net_key, diff_ref) if diff_ref else net_key

        if ref_net:
            gain = ac_data.gain_db_relative(sig_key, ref_net)
            phase = ac_data.phase_deg_relative(sig_key, ref_net)
        else:
            gain = ac_data.gain_db(sig_key)
            phase = ac_data.phase_deg(sig_key)

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            subplot_titles=("Gain (dB)", "Phase (deg)"),
            vertical_spacing=0.08,
        )

        fig.add_trace(
            go.Scatter(
                x=ac_data.freq, y=gain, mode="lines",
                name="Gain", line=dict(color="royalblue", width=2),
            ),
            row=1, col=1,
        )

        fig.add_hrect(
            y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
            line_width=0, row=1, col=1,
        )
        fig.add_hline(
            y=min_val, line=dict(color="red", dash="dot", width=1.5),
            row=1, col=1,
        )
        fig.add_hline(
            y=max_val, line=dict(color="red", dash="dot", width=1.5),
            row=1, col=1,
        )

        if measure_freq:
            actual = ctx.actual
            marker_color = "#2ecc71" if ctx.passed else "#e74c3c"
            fig.add_trace(
                go.Scatter(
                    x=[measure_freq], y=[actual], mode="markers+text",
                    marker=dict(color=marker_color, size=10),
                    text=[f"{actual:.2f} dB @ {measure_freq:.3g} Hz"],
                    textposition="top right",
                    textfont=dict(color=marker_color, size=11),
                    showlegend=False,
                ),
                row=1, col=1,
            )
            fig.add_vline(
                x=measure_freq,
                line=dict(color="gray", dash="dashdot", width=1),
                opacity=0.5, row=1, col=1,
            )
            fig.add_vline(
                x=measure_freq,
                line=dict(color="gray", dash="dashdot", width=1),
                opacity=0.5, row=2, col=1,
            )

        fig.add_trace(
            go.Scatter(
                x=ac_data.freq, y=phase, mode="lines",
                name="Phase", line=dict(color="orange", width=2),
            ),
            row=2, col=1,
        )

        fig.update_xaxes(type="log", title_text="Frequency (Hz)", row=2, col=1)
        fig.update_xaxes(type="log", row=1, col=1)
        fig.update_yaxes(title_text="Gain (dB)", row=1, col=1)
        fig.update_yaxes(title_text="Phase (deg)", row=2, col=1)

        title = self.get_title() or ctx.req_name
        subtitle = f"Measurement: gain_db | Actual: {ctx.actual:.2f} dB"
        return self._finalize_ac(fig, title, subtitle, path)

    # -------------------------------------------------------------------
    # Render: phase_deg
    # -------------------------------------------------------------------

    def _render_phase_deg(
        self, ac_data: Any, net_key: str, path: Path, ctx: PlotContext,
        ref_net: str | None, measure_freq: float | None,
    ) -> Path:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        min_val, max_val = ctx.min_val, ctx.max_val

        diff_ref = ctx.diff_ref_key
        sig_key = ac_data.compute_diff(net_key, diff_ref) if diff_ref else net_key

        if ref_net:
            gain = ac_data.gain_db_relative(sig_key, ref_net)
            phase = ac_data.phase_deg_relative(sig_key, ref_net)
        else:
            gain = ac_data.gain_db(sig_key)
            phase = ac_data.phase_deg(sig_key)

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            subplot_titles=("Gain (dB)", "Phase (deg)"),
            vertical_spacing=0.08,
        )

        fig.add_trace(
            go.Scatter(
                x=ac_data.freq, y=gain, mode="lines",
                name="Gain", line=dict(color="royalblue", width=2),
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=ac_data.freq, y=phase, mode="lines",
                name="Phase", line=dict(color="orange", width=2),
            ),
            row=2, col=1,
        )

        fig.add_hrect(
            y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
            line_width=0, row=2, col=1,
        )
        fig.add_hline(
            y=min_val, line=dict(color="red", dash="dot", width=1.5),
            row=2, col=1,
        )
        fig.add_hline(
            y=max_val, line=dict(color="red", dash="dot", width=1.5),
            row=2, col=1,
        )

        if measure_freq:
            actual = ctx.actual
            marker_color = "#2ecc71" if ctx.passed else "#e74c3c"
            fig.add_trace(
                go.Scatter(
                    x=[measure_freq], y=[actual], mode="markers+text",
                    marker=dict(color=marker_color, size=10),
                    text=[f"{actual:.1f} deg @ {measure_freq:.3g} Hz"],
                    textposition="top right",
                    textfont=dict(color=marker_color, size=11),
                    showlegend=False,
                ),
                row=2, col=1,
            )
            fig.add_vline(
                x=measure_freq,
                line=dict(color="gray", dash="dashdot", width=1),
                opacity=0.5, row=1, col=1,
            )
            fig.add_vline(
                x=measure_freq,
                line=dict(color="gray", dash="dashdot", width=1),
                opacity=0.5, row=2, col=1,
            )

        fig.update_xaxes(type="log", title_text="Frequency (Hz)", row=2, col=1)
        fig.update_xaxes(type="log", row=1, col=1)
        fig.update_yaxes(title_text="Gain (dB)", row=1, col=1)
        fig.update_yaxes(title_text="Phase (deg)", row=2, col=1)

        title = self.get_title() or ctx.req_name
        subtitle = f"Measurement: phase_deg | Actual: {ctx.actual:.1f} deg"
        return self._finalize_ac(fig, title, subtitle, path)

    # -------------------------------------------------------------------
    # Render: bandwidth_3db
    # -------------------------------------------------------------------

    def _render_bandwidth_3db(
        self, ac_data: Any, net_key: str, path: Path, ctx: PlotContext,
        ref_net: str | None, measure_freq: float | None,
    ) -> Path:
        import plotly.graph_objects as go

        min_val, max_val = ctx.min_val, ctx.max_val

        diff_ref = ctx.diff_ref_key
        sig_key = ac_data.compute_diff(net_key, diff_ref) if diff_ref else net_key

        if ref_net:
            gain = ac_data.gain_db_relative(sig_key, ref_net)
        else:
            gain = ac_data.gain_db(sig_key)

        dc_gain = gain[0] if gain else 0.0
        max_gain = max(gain) if gain else 0.0
        is_highpass = (max_gain - dc_gain) > 3.0

        if is_highpass:
            ref_gain = max_gain
            threshold = max_gain - 3.0
            ref_label = "Passband Gain"
        else:
            ref_gain = dc_gain
            threshold = dc_gain - 3.0
            ref_label = "DC Gain"

        actual = ctx.actual

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=ac_data.freq, y=gain, mode="lines",
                name="Gain", line=dict(color="royalblue", width=2.5),
            )
        )

        fig.add_hline(
            y=ref_gain, line=dict(color="gray", dash="dash", width=1.2),
            opacity=0.5,
        )
        fig.add_annotation(
            x=0.02, y=ref_gain, xref="paper", yref="y",
            text=f"{ref_label} = {ref_gain:.2f} dB",
            showarrow=False, font=dict(color="gray", size=10),
            xanchor="left", yanchor="bottom",
        )

        fig.add_hline(
            y=threshold, line=dict(color="#e74c3c", dash="dot", width=1.5),
            opacity=0.6,
        )

        if not math.isnan(actual) and actual > 0:
            bw_gain = _interpolate_at_freq(ac_data.freq, gain, actual)
            marker_color = "#2ecc71" if ctx.passed else "#e74c3c"

            fig.add_trace(
                go.Scatter(
                    x=[actual], y=[bw_gain], mode="markers",
                    marker=dict(
                        color=marker_color, size=14, symbol="circle",
                        line=dict(color="white", width=2),
                    ),
                    name=f"-3 dB @ {actual:.3g} Hz",
                    showlegend=True,
                )
            )

            fig.add_annotation(
                x=actual, y=bw_gain,
                text=(
                    f"<b>-3 dB point</b><br>"
                    f"f = {actual:.3g} Hz<br>"
                    f"Gain = {bw_gain:.2f} dB"
                ),
                showarrow=True, arrowhead=2, arrowsize=1.2,
                arrowcolor=marker_color, arrowwidth=2,
                ax=60, ay=-50,
                font=dict(color=marker_color, size=11),
                align="left",
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor=marker_color, borderwidth=1, borderpad=4,
            )

            fig.add_shape(
                type="line",
                x0=actual, x1=actual, y0=bw_gain, y1=threshold,
                line=dict(color=marker_color, dash="dashdot", width=1.5),
                opacity=0.5,
            )

        if min_val > 0:
            fig.add_vline(
                x=min_val, line=dict(color="red", dash="dot", width=1.5),
            )
            fig.add_annotation(
                x=min_val, y=0.02, xref="x", yref="paper",
                text=f"LSL = {min_val:.3g} Hz",
                showarrow=False, font=dict(color="red", size=9),
                xanchor="left", yanchor="bottom", textangle=-90,
            )
        if max_val > 0:
            fig.add_vline(
                x=max_val, line=dict(color="red", dash="dot", width=1.5),
            )
            fig.add_annotation(
                x=max_val, y=0.02, xref="x", yref="paper",
                text=f"USL = {max_val:.3g} Hz",
                showarrow=False, font=dict(color="red", size=9),
                xanchor="left", yanchor="bottom", textangle=-90,
            )

        fig.update_xaxes(type="log", title_text="Frequency (Hz)")
        fig.update_yaxes(title_text="Gain (dB)")

        title = self.get_title() or ctx.req_name
        subtitle = f"Measurement: bandwidth_3db | -3dB BW = {actual:.3g} Hz"
        return self._finalize_ac(fig, title, subtitle, path)

    # -------------------------------------------------------------------
    # Render: bode_plot
    # -------------------------------------------------------------------

    def _render_bode_plot(
        self, ac_data: Any, net_key: str, path: Path, ctx: PlotContext,
        ref_net: str | None, measure_freq: float | None,
    ) -> Path:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        diff_ref = ctx.diff_ref_key
        sig_key = ac_data.compute_diff(net_key, diff_ref) if diff_ref else net_key

        if ref_net:
            gain = ac_data.gain_db_relative(sig_key, ref_net)
            phase = ac_data.phase_deg_relative(sig_key, ref_net)
        else:
            gain = ac_data.gain_db(sig_key)
            phase = ac_data.phase_deg(sig_key)

        dc_gain = gain[0] if gain else 0.0

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            vertical_spacing=0.08,
        )

        fig.add_trace(
            go.Scatter(
                x=ac_data.freq, y=gain, mode="lines",
                name="Gain (dB)", line=dict(color="royalblue", width=2),
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=ac_data.freq, y=phase, mode="lines",
                name="Phase (deg)", line=dict(color="orange", width=2),
            ),
            row=2, col=1,
        )

        # -3dB crossing point
        threshold = dc_gain - 3.0
        bw_freq = None
        for i in range(len(gain) - 1):
            if gain[i] >= threshold and gain[i + 1] < threshold:
                log_f0 = math.log10(ac_data.freq[i])
                log_f1 = math.log10(ac_data.freq[i + 1])
                if gain[i] != gain[i + 1]:
                    t = (threshold - gain[i]) / (gain[i + 1] - gain[i])
                    bw_freq = 10 ** (log_f0 + t * (log_f1 - log_f0))
                else:
                    bw_freq = ac_data.freq[i]
                break

        if bw_freq is not None:
            bw_gain_val = _interpolate_at_freq(ac_data.freq, gain, bw_freq)
            fig.add_trace(
                go.Scatter(
                    x=[bw_freq], y=[bw_gain_val], mode="markers",
                    marker=dict(
                        color="#e74c3c", size=10, symbol="circle",
                        line=dict(color="white", width=2),
                    ),
                    name=f"-3 dB @ {bw_freq:.3g} Hz",
                    showlegend=True,
                ),
                row=1, col=1,
            )
            fig.add_annotation(
                x=bw_freq, y=bw_gain_val, xref="x", yref="y",
                text=f"-3 dB | {bw_freq:.3g} Hz",
                showarrow=True, arrowhead=2, arrowcolor="#e74c3c",
                ax=50, ay=-30,
                font=dict(color="#e74c3c", size=11),
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#e74c3c", borderwidth=1, borderpad=3,
            )

        fig.update_xaxes(type="log", row=1, col=1)
        fig.update_xaxes(type="log", title_text="Frequency (Hz)", row=2, col=1)
        fig.update_yaxes(title_text="Gain (dB)", row=1, col=1)
        fig.update_yaxes(title_text="Phase (deg)", row=2, col=1)

        title = self.get_title() or ctx.req_name
        subtitle = f"DC Gain: {dc_gain:.2f} dB"
        if bw_freq is not None:
            subtitle += f" | -3 dB BW: {bw_freq:.3g} Hz"
        return self._finalize_ac(fig, title, subtitle, path)


# ---------------------------------------------------------------------------
# StackedChart — multi-panel time-aligned chart
# ---------------------------------------------------------------------------


class StackedChart(fabll.Node):
    """Multi-panel stacked chart with shared time axis (flat — no inheritance).

    Each panel shows one signal as a vertically stacked subplot.

    Usage in ato::

        chart = new Plots.StackedChart
        chart.title = "Switching Waveforms"
        chart.signals = "package_8,i(L1),package_COMP,package_5"
        chart.labels = "V(SW),I(L1),V(COMP),V(FB)"

    Rendering::

        chart.render(tran_data, path)
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    title = F.Parameters.StringParameter.MakeChild()
    signals = F.Parameters.StringParameter.MakeChild()  # comma-separated signal keys
    labels = F.Parameters.StringParameter.MakeChild()  # comma-separated panel labels

    def get_title(self) -> str | None:
        try:
            return self.title.get().try_extract_singleton()
        except (AttributeError, Exception):
            return None

    def get_signal_keys(self) -> list[str]:
        """Parse comma-separated signal keys into a list of SPICE signal keys."""
        raw = self.signals.get().try_extract_singleton()
        if raw is None:
            return []
        keys = []
        for s in raw.split(","):
            s = s.strip()
            if not s:
                continue
            # Auto-wrap bare net names with v() — leave i() and v() as-is
            if not s.startswith(("v(", "i(")):
                s = f"v({s})"
            keys.append(s)
        return keys

    def get_labels(self) -> list[str]:
        """Parse comma-separated panel labels."""
        raw = self.labels.get().try_extract_singleton()
        if raw is None:
            return []
        return [l.strip() for l in raw.split(",") if l.strip()]

    # -------------------------------------------------------------------
    # Public render entry point
    # -------------------------------------------------------------------

    def render(
        self,
        tran_data: Any,
        path: str | Path,
        signal_keys: list[str] | None = None,
        panel_labels: list[str] | None = None,
        ctx: PlotContext | None = None,
    ) -> Path | None:
        """Render N vertically stacked subplots with shared time axis.

        Args:
            tran_data: TransientResult with .time and signal data.
            path: Output HTML file path.
            signal_keys: Override signal keys (otherwise read from .signals field).
            panel_labels: Override panel labels (otherwise read from .labels field).
            ctx: Optional PlotContext for pass/fail annotations on first panel.
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            return None

        path = Path(path)
        keys = signal_keys or self.get_signal_keys()
        labels = panel_labels or self.get_labels()

        if not keys:
            return None

        # Filter to keys that exist in the data
        valid_keys = [k for k in keys if k in tran_data]
        if not valid_keys:
            return None

        n = len(valid_keys)

        # Pad labels if needed
        while len(labels) < n:
            labels.append(valid_keys[len(labels)])

        # Auto-scale time axis
        t_max = tran_data.time[-1] if tran_data.time else 1.0
        scale, t_unit = auto_scale_time(t_max)
        time_scaled = [t * scale for t in tran_data.time]

        # Panel colors
        panel_colors = [
            "royalblue", "#e74c3c", "#2ecc71", "#9b59b6",
            "#f39c12", "#1abc9c", "#e67e22", "#34495e",
        ]

        fig = make_subplots(
            rows=n, cols=1, shared_xaxes=True,
            vertical_spacing=0.04,
            subplot_titles=labels[:n],
        )

        for i, key in enumerate(valid_keys):
            row = i + 1
            color = panel_colors[i % len(panel_colors)]
            unit = signal_unit(key)

            fig.add_trace(
                go.Scatter(
                    x=time_scaled,
                    y=list(tran_data[key]),
                    mode="lines",
                    name=labels[i],
                    line=dict(color=color, width=1.8),
                    showlegend=False,
                ),
                row=row, col=1,
            )

            y_label = f"{'Voltage' if unit == 'V' else 'Current'} ({unit})"
            fig.update_yaxes(title_text=y_label, row=row, col=1)

            # Add signal stats annotation
            sig = list(tran_data[key])
            if sig:
                avg = sum(sig) / len(sig)
                pk = max(sig)
                tr = min(sig)
                pp = pk - tr
                fig.add_annotation(
                    x=0.99, y=0.95, xref="paper", yref=f"y{row if row > 1 else ''} domain",
                    text=(
                        f"Avg={format_eng(avg, unit)} | "
                        f"P-P={format_eng(pp, unit)}"
                    ),
                    showarrow=False,
                    font=dict(color=color, size=9, family="monospace"),
                    xanchor="right", yanchor="top",
                    bgcolor="rgba(255,255,255,0.7)",
                )

        # X-axis label on bottom panel only
        fig.update_xaxes(title_text=f"Time ({t_unit})", row=n, col=1)

        # Layout
        chart_title = self.get_title() or "Stacked Waveforms"
        subtitle = f"{n} signals | Time range: {format_eng(tran_data.time[0], 's')} to {format_eng(tran_data.time[-1], 's')}"

        fig.update_layout(
            title=dict(
                text=f"<b>{chart_title}</b><br><span style='font-size:12px;color:gray'>"
                     f"{subtitle}</span>",
                x=0.5,
            ),
            width=900,
            height=200 + 180 * n,  # scale height with panel count
            template="plotly_white",
            showlegend=False,
        )

        if time_scaled:
            t_span = time_scaled[-1] - time_scaled[0]
            t_margin = 0.05 * t_span
            for i in range(n):
                fig.update_xaxes(
                    range=[time_scaled[0] - t_margin, time_scaled[-1] + t_margin],
                    row=i + 1, col=1,
                )

        self._last_figs = [fig]
        fig.write_html(str(path), include_plotlyjs="cdn")
        return path


# ---------------------------------------------------------------------------
# SweepChart — XY plot of measurement results vs swept parameter
# ---------------------------------------------------------------------------


@dataclass
class SweepPoint:
    """A single data point from a parametric sweep."""

    param_value: float
    actual: float
    passed: bool


class SweepChart(fabll.Node):
    """XY chart for parametric sweep results (flat — no inheritance).

    Plots measurement results (Y) vs swept parameter values (X) with
    pass/fail bands from the requirement bounds.

    Usage in ato::

        chart = new Plots.SweepChart
        chart.title = "Line Regulation: Vout vs VIN"
        chart.x_label = "Input Voltage (V)"
        chart.y_label = "Output Voltage (V)"

    Rendering::

        points = [SweepPoint(6.0, 4.98, True), SweepPoint(12.0, 5.00, True), ...]
        chart.render(points, path, ctx=PlotContext(...))
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    title = F.Parameters.StringParameter.MakeChild()
    x_label = F.Parameters.StringParameter.MakeChild()
    y_label = F.Parameters.StringParameter.MakeChild()

    def get_title(self) -> str | None:
        try:
            return self.title.get().try_extract_singleton()
        except (AttributeError, Exception):
            return None

    def get_x_label(self) -> str | None:
        try:
            return self.x_label.get().try_extract_singleton()
        except (AttributeError, Exception):
            return None

    def get_y_label(self) -> str | None:
        try:
            return self.y_label.get().try_extract_singleton()
        except (AttributeError, Exception):
            return None

    # -------------------------------------------------------------------
    # Public render entry point
    # -------------------------------------------------------------------

    def render(
        self,
        points: list[SweepPoint],
        path: str | Path,
        ctx: PlotContext | None = None,
        series: dict[str, list[SweepPoint]] | None = None,
    ) -> Path | None:
        """Render XY plot of sweep results.

        Args:
            points: Primary sweep results (param_value vs actual).
            path: Output HTML file path.
            ctx: PlotContext with min/max bounds for pass band.
            series: Additional named series to overlay (e.g. multiple loads).
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            return None

        path = Path(path)

        if not points:
            return None

        fig = go.Figure()

        x_vals = [p.param_value for p in points]
        y_vals = [p.actual for p in points]
        colors = ["#2ecc71" if p.passed else "#e74c3c" for p in points]

        # Main series
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode="lines+markers",
            name="Measured",
            line=dict(color="royalblue", width=2.5),
            marker=dict(color=colors, size=10, line=dict(color="white", width=2)),
        ))

        # Additional series (e.g., multiple load conditions)
        series_colors = ["#e74c3c", "#2ecc71", "#f39c12", "#9b59b6"]
        if series:
            for i, (label, s_points) in enumerate(series.items()):
                sc = series_colors[i % len(series_colors)]
                fig.add_trace(go.Scatter(
                    x=[p.param_value for p in s_points],
                    y=[p.actual for p in s_points],
                    mode="lines+markers",
                    name=label,
                    line=dict(color=sc, width=2),
                    marker=dict(size=8),
                ))

        # Pass band shading
        if ctx is not None:
            min_val, max_val = ctx.min_val, ctx.max_val
            munit = ctx.measurement_unit or ""
            fig.add_hrect(
                y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
                line_width=0,
            )
            fig.add_hline(
                y=min_val, line=dict(color="red", dash="dot", width=1.5),
                annotation_text=f"LSL {format_eng(min_val, munit)}",
                annotation_position="bottom left",
                annotation_font_size=10,
                annotation_font_color="#999",
            )
            fig.add_hline(
                y=max_val, line=dict(color="red", dash="dot", width=1.5),
                annotation_text=f"USL {format_eng(max_val, munit)}",
                annotation_position="top left",
                annotation_font_size=10,
                annotation_font_color="#999",
            )

            # Typical/target line
            if ctx.min_val != ctx.max_val:
                target = (ctx.min_val + ctx.max_val) / 2
                fig.add_hline(
                    y=target, line=dict(color="gray", dash="dash", width=1),
                    opacity=0.5,
                    annotation_text=f"Target {format_eng(target, munit)}",
                    annotation_position="bottom right",
                    annotation_font_size=9,
                    annotation_font_color="#bbb",
                )

        # Per-point value labels (alternate above/below to avoid overlap)
        unit = ctx.measurement_unit if ctx else ""
        for i, p in enumerate(points):
            label = format_eng(p.actual, unit)
            y_shift = 14 if i % 2 == 0 else -14
            y_anchor = "bottom" if i % 2 == 0 else "top"
            fig.add_annotation(
                x=p.param_value, y=p.actual,
                text=label,
                showarrow=False,
                font=dict(size=9, color="#555"),
                yanchor=y_anchor, yshift=y_shift,
            )

        # Pass/fail count
        n_pass = sum(1 for p in points if p.passed)
        n_fail = len(points) - n_pass
        status = "ALL PASS" if n_fail == 0 else f"{n_fail} FAIL"
        status_color = "#2ecc71" if n_fail == 0 else "#e74c3c"

        fig.add_annotation(
            x=0.02, y=0.98, xref="paper", yref="paper",
            text=f"<b>{status}</b> ({n_pass}/{len(points)} points)",
            showarrow=False,
            font=dict(color=status_color, size=12),
            xanchor="left", yanchor="top",
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor=status_color, borderwidth=1, borderpad=4,
        )

        # Labels — prefer sweep param info from PlotContext
        if ctx and ctx.sweep_param_name:
            default_x = f"{ctx.sweep_param_name}"
            if ctx.sweep_param_unit:
                default_x += f" ({ctx.sweep_param_unit})"
        else:
            default_x = ctx.display_net if ctx else "Parameter"
        if ctx and ctx.measurement_unit:
            default_y = f"{ctx.measurement.replace('_', ' ')} ({ctx.measurement_unit})"
        else:
            default_y = "Measured Value"
        x_label = self.get_x_label() or default_x
        y_label = self.get_y_label() or default_y
        fig.update_xaxes(title_text=x_label)
        fig.update_yaxes(title_text=y_label)

        chart_title = self.get_title() or (ctx.req_name if ctx else "Sweep Results")
        subtitle = f"{len(points)} sweep points | {status}"

        fig.update_layout(
            title=dict(
                text=f"<b>{chart_title}</b><br><span style='font-size:12px;color:gray'>"
                     f"{subtitle}</span>",
                x=0.5,
            ),
            width=900, height=500,
            template="plotly_white",
            showlegend=True,
            legend=dict(
                font=dict(size=10), x=1.02, y=1,
                xanchor="left", yanchor="top",
            ),
        )

        self._last_figs = [fig]
        fig.write_html(str(path), include_plotlyjs="cdn")
        return path


# ---------------------------------------------------------------------------
# EfficiencySweepChart — multi-panel efficiency + power breakdown chart
# ---------------------------------------------------------------------------


class EfficiencySweepChart(fabll.Node):
    """3-panel chart for efficiency sweep requirements.

    Panel 1: Efficiency vs Load Current (line+markers, pass/fail)
    Panel 2: Power Breakdown (stacked area: Pout + Ploss = Pin)
    Panel 3: Summary Table (Load, Pin, Pout, Ploss, Eff%)

    Usage::

        chart = EfficiencySweepChart.__new__(EfficiencySweepChart)
        chart.render(points, path, ctx=PlotContext(...), extras=[...])
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    title = F.Parameters.StringParameter.MakeChild()

    def get_title(self) -> str | None:
        try:
            return self.title.get().try_extract_singleton()
        except (AttributeError, Exception):
            return None

    def render(
        self,
        points: list[SweepPoint],
        path: str | Path,
        ctx: PlotContext | None = None,
        extras: list | None = None,
    ) -> Path | None:
        """Render efficiency charts as 3 independent HTML files.

        Args:
            points: Sweep results (param_value, actual efficiency%, passed).
            path: Output HTML file path (primary efficiency chart).
            ctx: PlotContext with min/max bounds.
            extras: List of SweepPointExtra with per-point power data.
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            return None

        path = Path(path)

        if not points or not extras or len(extras) != len(points):
            # Fall back to regular sweep chart if no extras
            fallback = SweepChart.__new__(SweepChart)
            return fallback.render(points, path, ctx=ctx)

        x_vals = [p.param_value for p in points]
        eff_vals = [p.actual for p in points]
        colors_list = ["#2ecc71" if p.passed else "#e74c3c" for p in points]

        pin_vals = [e.pin for e in extras]
        pout_vals = [e.pout for e in extras]
        ploss_vals = [e.ploss for e in extras]

        n_pass = sum(1 for p in points if p.passed)
        n_fail = len(points) - n_pass
        status = "ALL PASS" if n_fail == 0 else f"{n_fail} FAIL"
        status_color = "#2ecc71" if n_fail == 0 else "#e74c3c"

        x_label = "Load Current (A)"
        if ctx and ctx.sweep_param_name:
            x_label = ctx.sweep_param_name
            if ctx.sweep_param_unit:
                x_label += f" ({ctx.sweep_param_unit})"

        chart_title = self.get_title() or (ctx.req_name if ctx else "Efficiency Sweep")
        subtitle = f"{len(points)} sweep points | {status}"

        # =================================================================
        # Figure 1: Efficiency line chart (primary — has pass/fail limits)
        # =================================================================
        fig_eff = go.Figure()

        fig_eff.add_trace(
            go.Scatter(
                x=x_vals, y=eff_vals,
                mode="lines+markers",
                name="Efficiency",
                line=dict(color="royalblue", width=2.5),
                marker=dict(
                    color=colors_list, size=10,
                    line=dict(color="white", width=2),
                ),
            ),
        )

        # Pass band + limit lines
        if ctx is not None:
            min_val, max_val = ctx.min_val, ctx.max_val
            fig_eff.add_hrect(
                y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
                line_width=0,
            )
            fig_eff.add_hline(
                y=min_val, line=dict(color="red", dash="dot", width=1.5),
            )
            fig_eff.add_hline(
                y=max_val, line=dict(color="red", dash="dot", width=1.5),
            )
            fig_eff.add_annotation(
                x=x_vals[0], y=min_val, xref="x", yref="y",
                text=f"LSL {min_val:.1f}%",
                showarrow=False, font=dict(color="red", size=9),
                xanchor="left", yanchor="bottom",
            )
            fig_eff.add_annotation(
                x=x_vals[0], y=max_val, xref="x", yref="y",
                text=f"USL {max_val:.1f}%",
                showarrow=False, font=dict(color="red", size=9),
                xanchor="left", yanchor="top",
            )

        # Per-point labels
        for i, p in enumerate(points):
            y_shift = 14 if i % 2 == 0 else -14
            y_anchor = "bottom" if i % 2 == 0 else "top"
            fig_eff.add_annotation(
                x=p.param_value, y=p.actual,
                text=f"{p.actual:.1f}%",
                showarrow=False, font=dict(size=9, color="#555"),
                yanchor=y_anchor, yshift=y_shift,
            )

        # Peak efficiency annotation
        peak_idx = max(range(len(eff_vals)), key=lambda i: eff_vals[i])
        fig_eff.add_annotation(
            x=x_vals[peak_idx], y=eff_vals[peak_idx],
            text=f"Peak: {eff_vals[peak_idx]:.1f}%",
            showarrow=True, arrowhead=2, arrowcolor="#2ecc71",
            ax=30, ay=-25,
            font=dict(color="#2ecc71", size=10),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#2ecc71", borderwidth=1, borderpad=3,
        )

        # Pass/fail status badge
        fig_eff.add_annotation(
            x=0.98, y=0.98, xref="paper", yref="paper",
            text=f"<b>{status}</b> ({n_pass}/{len(points)})",
            showarrow=False, font=dict(color=status_color, size=11),
            xanchor="right", yanchor="top",
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor=status_color, borderwidth=1, borderpad=4,
        )

        fig_eff.update_layout(
            title=dict(
                text=f"<b>{chart_title}</b><br>"
                     f"<span style='font-size:12px;color:gray'>{subtitle}</span>",
                x=0.5,
            ),
            xaxis_title=x_label,
            yaxis_title="Efficiency (%)",
            width=900, height=500,
            template="plotly_white",
            showlegend=True,
            legend=dict(
                font=dict(size=10), x=1.02, y=1,
                xanchor="left", yanchor="top",
            ),
        )
        fig_eff.write_html(str(path), include_plotlyjs="cdn")

        # =================================================================
        # Figure 2: Power Breakdown
        # =================================================================
        fig_power = go.Figure()

        # Pout filled area
        fig_power.add_trace(
            go.Scatter(
                x=x_vals, y=pout_vals,
                mode="lines",
                name="P_out",
                line=dict(color="royalblue", width=1.5),
                fill="tozeroy",
                fillcolor="rgba(65,105,225,0.3)",
            ),
        )
        # Pin total line
        fig_power.add_trace(
            go.Scatter(
                x=x_vals, y=pin_vals,
                mode="lines",
                name="P_in (total)",
                line=dict(color="black", width=2),
            ),
        )
        # Ploss fill between Pout and Pin
        fig_power.add_trace(
            go.Scatter(
                x=x_vals, y=pout_vals,
                mode="lines", line=dict(width=0),
                showlegend=False,
            ),
        )
        fig_power.add_trace(
            go.Scatter(
                x=x_vals, y=pin_vals,
                mode="lines", line=dict(width=0),
                name="P_loss",
                fill="tonexty",
                fillcolor="rgba(231,76,60,0.25)",
            ),
        )

        fig_power.update_layout(
            title=dict(
                text="<b>Power Breakdown</b>",
                x=0.5,
            ),
            xaxis_title=x_label,
            yaxis_title="Power (W)",
            width=900, height=400,
            template="plotly_white",
            showlegend=True,
            legend=dict(
                font=dict(size=10), x=1.02, y=1,
                xanchor="left", yanchor="top",
            ),
        )
        path_power = path.with_stem(path.stem + "_power")
        fig_power.write_html(str(path_power), include_plotlyjs="cdn")

        # =================================================================
        # Figure 3: Summary Table
        # =================================================================
        x_unit = ctx.sweep_param_unit if ctx else "A"
        header_vals = ["Load", "P_in", "P_out", "P_loss", "Eff (%)"]
        cell_vals = [
            [format_eng(x, x_unit) for x in x_vals],
            [format_eng(p, "W") for p in pin_vals],
            [format_eng(p, "W") for p in pout_vals],
            [format_eng(p, "W") for p in ploss_vals],
            [f"{e:.1f}" for e in eff_vals],
        ]

        eff_colors = ["#c6efce" if p.passed else "#ffc7ce" for p in points]
        white_row = ["white"] * len(points)
        cell_fill = [white_row, white_row, white_row, white_row, eff_colors]

        fig_table = go.Figure(
            go.Table(
                header=dict(
                    values=header_vals,
                    fill_color="#f0f0f0",
                    font=dict(size=11, color="#333"),
                    align="center",
                ),
                cells=dict(
                    values=cell_vals,
                    fill_color=cell_fill,
                    font=dict(size=10, color="#333"),
                    align="center",
                ),
            ),
        )

        fig_table.update_layout(
            title=dict(
                text="<b>Efficiency Summary</b>",
                x=0.5,
            ),
            width=900, height=300,
            template="plotly_white",
        )
        path_table = path.with_stem(path.stem + "_table")
        fig_table.write_html(str(path_table), include_plotlyjs="cdn")

        self._last_figs = [fig_eff, fig_power, fig_table]
        return path


# ---------------------------------------------------------------------------
# CombinedSweepChart — 2-panel: waveform overlay + measurement vs parameter
# ---------------------------------------------------------------------------


def _viridis_colors(n: int) -> list[str]:
    """Return *n* colours sampled evenly from the Viridis colorscale."""
    import plotly.colors

    if n <= 1:
        return ["rgb(68, 1, 84)"]
    return plotly.colors.sample_colorscale(
        "Viridis", [i / (n - 1) for i in range(n)]
    )


class CombinedSweepChart(fabll.Node):
    """2-panel chart: waveform overlay (top) + measurement vs parameter (bottom).

    Top panel shows the time-domain signal for each sweep point overlaid
    with viridis colouring.  Bottom panel is the same as SweepChart (scalar
    measurement vs swept parameter with pass band and limit lines).

    For ``settling_time`` measurements the bottom panel also shows 95% and 99%
    milestone series.

    Usage::

        chart = CombinedSweepChart.__new__(CombinedSweepChart)
        chart.render(points, path, ctx=PlotContext(...), sweep_raw={...})
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    title = F.Parameters.StringParameter.MakeChild()

    def get_title(self) -> str | None:
        try:
            return self.title.get().try_extract_singleton()
        except (AttributeError, Exception):
            return None

    # -------------------------------------------------------------------
    # Public render entry point
    # -------------------------------------------------------------------

    def render(
        self,
        points: list[SweepPoint],
        path: str | Path,
        ctx: PlotContext | None = None,
        sweep_raw: dict[float, Any] | None = None,
    ) -> Path | None:
        """Render sweep charts as 2 independent HTML files.

        Args:
            points: Primary sweep results (param_value vs actual).
            path: Output HTML file path (primary measurement chart).
            ctx: PlotContext with bounds, signal_key, sweep param info.
            sweep_raw: dict mapping param_value → TransientResult.
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            return None

        path = Path(path)

        if not points or not sweep_raw or not ctx or not ctx.signal_key:
            # Fall back to regular SweepChart if insufficient data
            fallback = SweepChart.__new__(SweepChart)
            return fallback.render(points, path, ctx=ctx)

        sorted_raw = sorted(sweep_raw.items())
        n_pts = len(sorted_raw)
        colors = _viridis_colors(n_pts)

        param_name = ctx.sweep_param_name or "Parameter"
        param_unit = ctx.sweep_param_unit or ""
        sig_key = ctx.signal_key
        sig_unit = signal_unit(sig_key)
        munit = ctx.measurement_unit or ""

        n_pass = sum(1 for p in points if p.passed)
        n_fail = len(points) - n_pass
        status = "ALL PASS" if n_fail == 0 else f"{n_fail} FAIL"
        status_color = "#2ecc71" if n_fail == 0 else "#e74c3c"

        chart_title = (
            self.get_title() or (ctx.req_name if ctx else "Sweep Results")
        )
        subtitle = f"{n_pts} sweep points | {status}"

        if param_unit:
            x_label_bottom = f"{param_name} ({param_unit})"
        else:
            x_label_bottom = param_name
        if munit:
            y_label_bottom = (
                f"{ctx.measurement.replace('_', ' ')} ({munit})"
            )
        else:
            y_label_bottom = ctx.measurement.replace("_", " ")

        # =================================================================
        # Figure 1: Measurement vs Parameter (primary — has pass/fail limits)
        # =================================================================
        fig_meas = go.Figure()

        x_vals = [p.param_value for p in points]
        y_vals = [p.actual for p in points]
        marker_colors = [
            "#2ecc71" if p.passed else "#e74c3c" for p in points
        ]

        fig_meas.add_trace(
            go.Scatter(
                x=x_vals, y=y_vals,
                mode="lines+markers",
                name="Measured",
                line=dict(color="royalblue", width=2.5),
                marker=dict(
                    color=marker_colors, size=10,
                    line=dict(color="white", width=2),
                ),
            ),
        )

        # Pass band + limit lines
        min_val, max_val = ctx.min_val, ctx.max_val
        fig_meas.add_hrect(
            y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
            line_width=0,
        )
        fig_meas.add_hline(
            y=min_val, line=dict(color="red", dash="dot", width=1.5),
        )
        fig_meas.add_hline(
            y=max_val, line=dict(color="red", dash="dot", width=1.5),
        )
        fig_meas.add_annotation(
            x=x_vals[0], y=min_val, xref="x", yref="y",
            text=f"LSL {format_eng(min_val, munit)}",
            showarrow=False, font=dict(color="#999", size=10),
            xanchor="left", yanchor="bottom",
        )
        fig_meas.add_annotation(
            x=x_vals[0], y=max_val, xref="x", yref="y",
            text=f"USL {format_eng(max_val, munit)}",
            showarrow=False, font=dict(color="#999", size=10),
            xanchor="left", yanchor="top",
        )

        # Target line
        if min_val != max_val:
            target = (min_val + max_val) / 2
            fig_meas.add_hline(
                y=target, line=dict(color="gray", dash="dash", width=1),
                opacity=0.5,
            )

        # Per-point value labels
        for i, p in enumerate(points):
            label = format_eng(p.actual, munit)
            y_shift = 14 if i % 2 == 0 else -14
            y_anchor = "bottom" if i % 2 == 0 else "top"
            fig_meas.add_annotation(
                x=p.param_value, y=p.actual,
                text=label,
                showarrow=False,
                font=dict(size=9, color="#555"),
                yanchor=y_anchor, yshift=y_shift,
            )

        # Settling milestones (95% / 99%) for settling_time measurement
        if ctx.measurement == "settling_time":
            ms_95: list[tuple[float, float]] = []
            ms_99: list[tuple[float, float]] = []
            for pval, tran in sorted_raw:
                if not hasattr(tran, "time"):
                    continue
                try:
                    sig_data = list(tran[sig_key])
                except KeyError:
                    continue
                final = sig_data[-1] if sig_data else 0.0
                milestones = _compute_settling_milestones(
                    sig_data, tran.time, final,
                )
                for m_time, m_pct, _ in milestones:
                    if m_pct == 95:
                        ms_95.append((pval, m_time))
                    elif m_pct == 99:
                        ms_99.append((pval, m_time))

            if ms_95:
                fig_meas.add_trace(
                    go.Scatter(
                        x=[p[0] for p in ms_95],
                        y=[p[1] for p in ms_95],
                        mode="lines+markers",
                        name="95% settled",
                        line=dict(color="#e67e22", width=1.5, dash="dash"),
                        marker=dict(size=7, symbol="diamond"),
                    ),
                )
            if ms_99:
                fig_meas.add_trace(
                    go.Scatter(
                        x=[p[0] for p in ms_99],
                        y=[p[1] for p in ms_99],
                        mode="lines+markers",
                        name="99% settled",
                        line=dict(color="#8e44ad", width=1.5, dash="dash"),
                        marker=dict(size=7, symbol="diamond"),
                    ),
                )

        # Pass/fail status badge
        fig_meas.add_annotation(
            x=0.98, y=0.02, xref="paper", yref="paper",
            text=f"<b>{status}</b> ({n_pass}/{len(points)} points)",
            showarrow=False,
            font=dict(color=status_color, size=12),
            xanchor="right", yanchor="bottom",
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor=status_color, borderwidth=1, borderpad=4,
        )

        fig_meas.update_layout(
            title=dict(
                text=(
                    f"<b>{chart_title}</b><br>"
                    f"<span style='font-size:12px;color:gray'>"
                    f"{subtitle}</span>"
                ),
                x=0.5,
            ),
            xaxis_title=x_label_bottom,
            yaxis_title=y_label_bottom,
            width=900, height=500,
            template="plotly_white",
            showlegend=True,
            legend=dict(
                font=dict(size=10), x=1.02, y=1,
                xanchor="left", yanchor="top",
            ),
        )
        fig_meas.write_html(str(path), include_plotlyjs="cdn")

        # =================================================================
        # Figure 2: Transient Waveform Overlay
        # =================================================================
        fig_wave = go.Figure()

        for i, (pval, tran) in enumerate(sorted_raw):
            if not hasattr(tran, "time"):
                continue
            try:
                sig_data = list(tran[sig_key])
            except KeyError:
                continue

            t_max = tran.time[-1] if tran.time else 1.0
            scale, t_unit = auto_scale_time(t_max)
            time_scaled = [t * scale for t in tran.time]

            label = f"{param_name} = {format_eng(pval, param_unit)}"
            fig_wave.add_trace(
                go.Scatter(
                    x=time_scaled,
                    y=sig_data,
                    mode="lines",
                    name=label,
                    line=dict(color=colors[i], width=2),
                ),
            )

        # Time axis label (use last sweep point's scale)
        if sorted_raw:
            last_tran = sorted_raw[-1][1]
            if hasattr(last_tran, "time") and last_tran.time:
                _, t_unit = auto_scale_time(last_tran.time[-1])
            else:
                t_unit = "s"
        else:
            t_unit = "s"

        y_label_top = (
            f"Voltage ({sig_unit})" if sig_unit == "V"
            else f"Current ({sig_unit})"
        )

        fig_wave.update_layout(
            title=dict(
                text="<b>Transient Waveform Overlay</b>",
                x=0.5,
            ),
            xaxis_title=f"Time ({t_unit})",
            yaxis_title=y_label_top,
            width=900, height=500,
            template="plotly_white",
            showlegend=True,
            legend=dict(
                font=dict(size=10), x=1.02, y=1,
                xanchor="left", yanchor="top",
            ),
        )
        path_wave = path.with_stem(path.stem + "_waveforms")
        fig_wave.write_html(str(path_wave), include_plotlyjs="cdn")

        self._last_figs = [fig_meas, fig_wave]
        return path
