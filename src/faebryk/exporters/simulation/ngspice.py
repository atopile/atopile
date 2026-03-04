"""Ngspice simulation API.

User-facing API:
    Circuit     — load a .spice file, run .op(), .tran(), and .ac() analyses
    OpResult    — dict-like DC operating point results
    TransientResult — signal access + .plot()
    ACResult    — frequency-domain results with gain/phase helpers
    dc(), pulse() — source specification helpers

Build-step API:
    generate_spice_netlist() — auto-generate from atopile graph

Requires ngspice to be installed separately:
    macOS:  brew install ngspice
    Linux:  apt install ngspice
"""

from __future__ import annotations

import logging
import math
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def format_spice_value(value: float) -> str:
    """Convert an SI float to SPICE notation.

    Examples:
        1e-12  -> "1p"
        100e-9 -> "100n"
        4.7e-6 -> "4.7u"
        1e-3   -> "1m"
        10000  -> "10k"
        1e6    -> "1Meg"
        1e9    -> "1G"
    """
    suffixes = [
        (1e12, "T"),
        (1e9, "G"),
        (1e6, "Meg"),
        (1e3, "k"),
        (1, ""),
        (1e-3, "m"),
        (1e-6, "u"),
        (1e-9, "n"),
        (1e-12, "p"),
        (1e-15, "f"),
    ]
    if value == 0:
        return "0"
    abs_val = abs(value)
    for threshold, suffix in suffixes:
        if abs_val >= threshold:
            scaled = value / threshold
            if scaled == int(scaled):
                return f"{int(scaled)}{suffix}"
            return f"{scaled:.6g}{suffix}"
    return f"{value:.6g}"


# ---------------------------------------------------------------------------
# Source helpers
# ---------------------------------------------------------------------------

def dc(voltage: float) -> str:
    """Return a SPICE DC source specification.

    >>> dc(10)
    'DC 10'
    """
    return f"DC {format_spice_value(voltage)}"


def pulse(
    v1: float,
    v2: float,
    delay: float = 0,
    rise: float = 100e-6,
    fall: float = 100e-6,
    width: float = 10,
    period: float = 10,
) -> str:
    """Return a SPICE PULSE source specification.

    Default rise/fall of 100us is realistic for power supply ramps and
    avoids numerical instability in average-model simulations.

    >>> pulse(0, 10, delay=0.5)
    'PULSE(0 10 500m 100u 100u 10 10)'
    """
    vals = [v1, v2, delay, rise, fall, width, period]
    return "PULSE(" + " ".join(format_spice_value(v) for v in vals) + ")"


# ---------------------------------------------------------------------------
# SpiceNetlist (internal builder)
# ---------------------------------------------------------------------------

@dataclass
class SpiceNetlist:
    """Builder for SPICE netlists."""

    title: str = "Untitled"
    _lines: list[str] = field(default_factory=list)
    _control: list[str] = field(default_factory=list)
    _subcircuit_defs: list[str] = field(default_factory=list)
    component_map: dict[str, str] = field(default_factory=dict)
    """Maps ato relative component path → SPICE designator (e.g. ``r_load`` → ``R5``)."""

    def add_resistor(self, name: str, node_p: str, node_n: str, value: float | str) -> None:
        """Add a resistor element.

        Args:
            name: Element name (e.g. "R1"). Must start with 'R'.
            node_p: Positive node name.
            node_n: Negative node name.
            value: Resistance in ohms (float) or SPICE string (e.g. "10k").
        """
        val_str = format_spice_value(value) if isinstance(value, (int, float)) else value
        self._lines.append(f"{name} {node_p} {node_n} {val_str}")

    def add_voltage_source(
        self, name: str, node_p: str, node_n: str, dc_value: float | str
    ) -> None:
        """Add a DC voltage source.

        Args:
            name: Element name (e.g. "V1"). Must start with 'V'.
            node_p: Positive node name.
            node_n: Negative node name.
            dc_value: DC voltage in volts (float) or SPICE string.
        """
        val_str = format_spice_value(dc_value) if isinstance(dc_value, (int, float)) else dc_value
        self._lines.append(f"{name} {node_p} {node_n} DC {val_str}")

    def add_capacitor(self, name: str, node_p: str, node_n: str, value: float | str) -> None:
        """Add a capacitor element."""
        val_str = format_spice_value(value) if isinstance(value, (int, float)) else value
        self._lines.append(f"{name} {node_p} {node_n} {val_str}")

    def add_inductor(self, name: str, node_p: str, node_n: str, value: float | str) -> None:
        """Add an inductor element."""
        val_str = format_spice_value(value) if isinstance(value, (int, float)) else value
        self._lines.append(f"{name} {node_p} {node_n} {val_str}")

    def add_raw(self, line: str) -> None:
        """Add an arbitrary SPICE line."""
        self._lines.append(line)

    def add_op_analysis(self) -> None:
        """Add operating point analysis with 'print all'."""
        self._control.extend(["op", "print all"])

    def add_control(self, *commands: str) -> None:
        """Add arbitrary control commands."""
        self._control.extend(commands)

    def add_subcircuit_definitions(self, defs: str) -> None:
        """Add subcircuit/model definitions (emitted between title and elements)."""
        self._subcircuit_defs.append(defs)

    def to_string(self) -> str:
        """Render the complete SPICE netlist as a string."""
        lines = [f"* {self.title}"]
        # Embed component map as comments for round-trip through file
        if self.component_map:
            lines.append("* @component_map: " + ",".join(
                f"{path}={designator}"
                for path, designator in sorted(self.component_map.items())
            ))
        # Subcircuit definitions go first (before element lines)
        for block in self._subcircuit_defs:
            lines.append(block)
        lines.extend(self._lines)
        if self._control:
            lines.append(".control")
            lines.extend(self._control)
            lines.append("quit")
            lines.append(".endc")
        lines.append(".end")
        lines.append("")  # trailing newline
        return "\n".join(lines)

    def write(self, path: Path | str) -> Path:
        """Write the netlist to a file, creating parent directories."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_string())
        return path


# ---------------------------------------------------------------------------
# Result classes
# ---------------------------------------------------------------------------

class OpResult:
    """DC operating point results with dict-like access.

    Access voltages by node name — bare names auto-wrap in ``v()``:
        >>> result["v(output)"]   # exact key
        >>> result["output"]      # looks up v(output)
    """

    def __init__(self, voltages: dict[str, float], currents: dict[str, float]):
        self.voltages = voltages
        self.currents = currents

    def _resolve(self, key: str) -> tuple[str, float]:
        key_lc = key.lower()
        # exact match in voltages or currents
        for store in (self.voltages, self.currents):
            if key_lc in store:
                return key_lc, store[key_lc]
        # try wrapping bare name
        for prefix, store in [("v", self.voltages), ("i", self.currents)]:
            wrapped = f"{prefix}({key_lc})"
            if wrapped in store:
                return wrapped, store[wrapped]
        raise KeyError(key)

    def __getitem__(self, key: str) -> float:
        return self._resolve(key)[1]

    def __contains__(self, key: str) -> bool:
        try:
            self._resolve(key)
            return True
        except KeyError:
            return False

    def __repr__(self) -> str:
        return f"OpResult(voltages={self.voltages}, currents={self.currents})"

    def __str__(self) -> str:
        parts = []
        if self.voltages:
            parts.append("Voltages:")
            for name in sorted(self.voltages):
                parts.append(f"  {name} = {self.voltages[name]:.6f} V")
        if self.currents:
            parts.append("Currents:")
            for name in sorted(self.currents):
                parts.append(f"  {name} = {self.currents[name]:.6e} A")
        return "\n".join(parts) if parts else "(no results)"


class TransientResult:
    """Transient analysis results with signal access and plotting.

    Access signals by name — bare names auto-wrap in ``v()``:
        >>> result["v(output)"]   # exact key → list[float]
        >>> result["output"]      # looks up v(output)
        >>> result.time           # → list[float]
    """

    def __init__(self, time: list[float], signals: dict[str, list[float]]):
        self.time = time
        self.signals = signals

    def _resolve(self, key: str) -> tuple[str, list[float]]:
        key_lc = key.lower()
        if key_lc in self.signals:
            return key_lc, self.signals[key_lc]
        wrapped = f"v({key_lc})"
        if wrapped in self.signals:
            return wrapped, self.signals[wrapped]
        raise KeyError(key)

    def __getitem__(self, key: str) -> list[float]:
        return self._resolve(key)[1]

    def __contains__(self, key: str) -> bool:
        try:
            self._resolve(key)
            return True
        except KeyError:
            return False

    def __repr__(self) -> str:
        n = len(self.time)
        sigs = list(self.signals.keys())
        return f"TransientResult({n} points, signals={sigs})"

    def plot(
        self,
        path: str | Path,
        signals: list[str] | None = None,
        title: str | None = None,
    ) -> Path | None:
        """Save a plot of signals vs time.

        Returns the path on success, or None if matplotlib is unavailable.
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            logger.info("matplotlib not installed — skipping plot")
            return None

        path = Path(path)
        sig_keys = signals or list(self.signals.keys())

        fig, ax = plt.subplots(figsize=(10, 5))
        for key in sig_keys:
            data = self[key]
            ax.plot(self.time, data, linewidth=1.5, label=key)

        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Voltage / Current")
        ax.set_title(title or "Transient Analysis")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 5% margins
        if self.time:
            t_span = self.time[-1] - self.time[0]
            ax.set_xlim(
                self.time[0] - 0.05 * t_span,
                self.time[-1] + 0.05 * t_span,
            )

        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path


class ACResult:
    """AC small-signal analysis results with frequency-domain access.

    Stores complex-valued signals (real + imaginary) indexed by frequency.
    Provides magnitude, phase, gain (dB), and relative transfer-function helpers.

    Access signals by name — bare names auto-wrap in ``v()``:
        >>> result.gain_db("output")     # dB magnitude at each frequency
        >>> result.freq                  # list[float]
    """

    def __init__(
        self,
        freq: list[float],
        signals_real: dict[str, list[float]],
        signals_imag: dict[str, list[float]],
    ):
        self.freq = freq
        self.signals_real = signals_real
        self.signals_imag = signals_imag

    def _resolve_key(self, key: str) -> str:
        key_lc = key.lower()
        if key_lc in self.signals_real:
            return key_lc
        wrapped = f"v({key_lc})"
        if wrapped in self.signals_real:
            return wrapped
        raise KeyError(key)

    def magnitude(self, key: str) -> list[float]:
        k = self._resolve_key(key)
        r = self.signals_real[k]
        im = self.signals_imag[k]
        return [math.sqrt(rv * rv + iv * iv) for rv, iv in zip(r, im)]

    def phase_deg(self, key: str) -> list[float]:
        k = self._resolve_key(key)
        r = self.signals_real[k]
        im = self.signals_imag[k]
        return [math.degrees(math.atan2(iv, rv)) for rv, iv in zip(r, im)]

    def gain_db(self, key: str) -> list[float]:
        mag = self.magnitude(key)
        return [20 * math.log10(m) if m > 0 else -200.0 for m in mag]

    def gain_db_relative(self, out_key: str, in_key: str) -> list[float]:
        mag_out = self.magnitude(out_key)
        mag_in = self.magnitude(in_key)
        return [
            20 * math.log10(mo / mi) if mi > 0 and mo > 0 else -200.0
            for mo, mi in zip(mag_out, mag_in)
        ]

    def phase_deg_relative(self, out_key: str, in_key: str) -> list[float]:
        p_out = self.phase_deg(out_key)
        p_in = self.phase_deg(in_key)
        return [po - pi for po, pi in zip(p_out, p_in)]

    def compute_diff(self, pos_key: str, neg_key: str) -> str:
        """Compute V(pos) - V(neg) and store as a virtual signal. Returns the key."""
        pk = self._resolve_key(pos_key)
        nk = self._resolve_key(neg_key)
        diff_key = f"v_diff({pk},{nk})"
        if diff_key not in self.signals_real:
            self.signals_real[diff_key] = [
                a - b for a, b in zip(self.signals_real[pk], self.signals_real[nk])
            ]
            self.signals_imag[diff_key] = [
                a - b for a, b in zip(self.signals_imag[pk], self.signals_imag[nk])
            ]
        return diff_key

    def __contains__(self, key: str) -> bool:
        try:
            self._resolve_key(key)
            return True
        except KeyError:
            return False

    def __repr__(self) -> str:
        n = len(self.freq)
        sigs = list(self.signals_real.keys())
        return f"ACResult({n} points, signals={sigs})"


# ---------------------------------------------------------------------------
# Circuit — main user-facing class
# ---------------------------------------------------------------------------

class Circuit:
    """Load a SPICE netlist and run simulations.

    Usage::

        circuit = Circuit.load("build/builds/default/default.spice")
        op = circuit.op()
        print(op)

        circuit.set_source("V1", pulse(0, 10, delay=0.5))
        tran = circuit.tran(step=1e-3, stop=2.0)
        tran.plot("output.png")
    """

    def __init__(self, netlist: SpiceNetlist):
        self._netlist = netlist

    @classmethod
    def load(cls, path: str | Path) -> Circuit:
        """Load a .spice file generated by ``ato build``."""
        return cls(_load_spice_circuit(path))

    def copy(self) -> Circuit:
        """Create an independent copy of this circuit for parallel execution."""
        new_netlist = SpiceNetlist(title=self._netlist.title)
        new_netlist._lines = list(self._netlist._lines)
        new_netlist._subcircuit_defs = list(self._netlist._subcircuit_defs)
        new_netlist.component_map = dict(self._netlist.component_map)
        return Circuit(new_netlist)

    def set_source(self, name: str, source_spec: str) -> None:
        """Override a voltage/current source definition.

        Args:
            name: Source name (e.g. "V1").
            source_spec: New source spec, e.g. ``pulse(0, 10, delay=0.5)``.
        """
        prefix = name.upper() + " "
        new_lines = []
        for line in self._netlist._lines:
            if line.upper().startswith(prefix):
                # Line format: NAME NODE+ NODE- <spec...>
                parts = line.split(None, 3)  # [name, node+, node-, old_spec]
                new_lines.append(f"{parts[0]} {parts[1]} {parts[2]} {source_spec}")
            else:
                new_lines.append(line)
        self._netlist._lines = new_lines

    def op(self) -> OpResult:
        """Run DC operating point analysis."""
        net = SpiceNetlist(title=self._netlist.title)
        net._lines = list(self._netlist._lines)
        net._subcircuit_defs = list(self._netlist._subcircuit_defs)
        net.add_op_analysis()

        output = _run_ngspice_batch(net)
        parsed = _parse_ngspice_output(output)
        return OpResult(voltages=parsed.node_voltages, currents=parsed.branch_currents)

    def tran(
        self,
        step: float,
        stop: float,
        signals: list[str] | None = None,
        start: float = 0,
        uic: bool = False,
        tmax: float | None = None,
    ) -> TransientResult:
        """Run transient analysis.

        Args:
            step: Timestep in seconds.
            stop: Stop time in seconds.
            signals: Signal names to record. If None, records all signals
                (node voltages + inductor/source branch currents).
            start: Start time for recording (default 0).
            uic: Use Initial Conditions — skip DC operating point, start from
                 zero (or .ic values). Helps convergence for behavioral models.
            tmax: Maximum internal timestep (helps convergence for switching circuits).
        """
        if signals is None:
            signals = self._detect_signals()

        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = Path(tmpdir) / "tran_data.txt"
            spice_file = Path(tmpdir) / "circuit.spice"

            net = SpiceNetlist(title=self._netlist.title)
            net._lines = list(self._netlist._lines)
            net._subcircuit_defs = list(self._netlist._subcircuit_defs)

            tran_cmd = (
                f"tran {format_spice_value(step)} {format_spice_value(stop)}"
                + (f" {format_spice_value(start)}" if start > 0 else "")
                + (f" {format_spice_value(tmax)}" if tmax and start <= 0 else "")
                + (" uic" if uic else "")
            )
            # When both start and tmax are specified, ngspice syntax is:
            # tran step stop start tmax [uic]
            if tmax and start > 0:
                tran_cmd = (
                    f"tran {format_spice_value(step)} {format_spice_value(stop)}"
                    f" {format_spice_value(start)} {format_spice_value(tmax)}"
                    + (" uic" if uic else "")
                )
            # Convergence-friendly options for behavioral/average models
            options_line = (
                ".options reltol=0.005 abstol=1e-9 vntol=1e-4"
                " gmin=1e-10 itl1=500 itl4=500 method=gear"
            )
            net._lines.append(options_line)

            net.add_control(
                tran_cmd,
                f"wrdata {data_file} {' '.join(signals)}",
            )
            spice_content = net.to_string()
            spice_file.write_text(spice_content)

            proc = _run_ngspice_subprocess(str(spice_file), timeout=300)
            if not data_file.exists():
                raise RuntimeError(
                    f"ngspice produced no output data file.\n"
                    f"stderr: {proc.stderr[-2000:] if proc.stderr else '(empty)'}\n"
                    f"stdout (last 2000): {proc.stdout[-2000:] if proc.stdout else '(empty)'}"
                )
            return _parse_wrdata(data_file, signals)

    def add_element(self, line: str) -> None:
        """Add a new element line to the netlist."""
        self._netlist._lines.append(line)

    def remove_element(self, name: str) -> None:
        """Remove an element by name or ato component path from the netlist.

        If *name* matches an ato component path in the component map,
        all corresponding SPICE designators are removed.  A bare path
        like ``c_out`` also matches array entries (``c_out.0``, etc.).
        Falls back to direct SPICE designator matching (e.g. ``R5``).
        """
        cmap = self._netlist.component_map

        # Collect SPICE designators to remove
        designators: list[str] = []

        if name in cmap:
            # Exact match: e.g. "r_load" → "R5"
            designators.append(cmap[name])
        else:
            # Prefix match for arrays: e.g. "c_out" matches "c_out.0", "c_out.1", ...
            prefix_with_dot = name + "."
            for path, desig in cmap.items():
                if path.startswith(prefix_with_dot):
                    designators.append(desig)

        if not designators:
            # No component_map match — treat as raw SPICE designator (backward compat)
            designators.append(name)

        for desig in designators:
            prefix = desig.upper() + " "
            self._netlist._lines = [
                l for l in self._netlist._lines
                if not l.upper().startswith(prefix)
            ]

    def modify_instance_param(self, param_name: str, value: float) -> None:
        """Modify a parameter on subcircuit instances (X elements).

        Finds X instance lines with ``param_name=<old_value>`` and replaces
        the value.  Used by sweep runners to override subcircuit parameters
        (e.g. ``FS=400000.0`` → ``FS=800000.0``).
        """
        pattern = re.compile(
            rf'\b{re.escape(param_name)}=[^\s]+',
            re.IGNORECASE,
        )
        new_value_str = format_spice_value(value)
        new_lines = []
        for line in self._netlist._lines:
            if line.upper().startswith("X"):
                new_lines.append(
                    pattern.sub(f"{param_name}={new_value_str}", line)
                )
            else:
                new_lines.append(line)
        self._netlist._lines = new_lines

    def save_state(self) -> list[str]:
        """Save the current netlist lines. Returns state for restore_state."""
        return list(self._netlist._lines)

    def restore_state(self, state: list[str]) -> None:
        """Restore netlist lines from a previous save_state call."""
        self._netlist._lines = list(state)

    def get_source_spec(self, name: str) -> str | None:
        """Read the existing source specification from the netlist.

        Returns the spec portion (everything after the two node names),
        or None if the source is not found.
        """
        prefix = name.upper() + " "
        for line in self._netlist._lines:
            if line.upper().startswith(prefix):
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    return parts[3]
        return None

    def ac(
        self,
        start_freq: float,
        stop_freq: float,
        points_per_decade: int = 100,
        signals: list[str] | None = None,
    ) -> ACResult:
        """Run AC small-signal analysis.

        Args:
            start_freq: Start frequency in Hz.
            stop_freq: Stop frequency in Hz.
            points_per_decade: Number of frequency points per decade.
            signals: Signal names to record. If None, records all signals.
        """
        if signals is None:
            signals = self._detect_signals()

        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = Path(tmpdir) / "ac_data.txt"
            spice_file = Path(tmpdir) / "circuit.spice"

            net = SpiceNetlist(title=self._netlist.title)
            net._lines = list(self._netlist._lines)
            net._subcircuit_defs = list(self._netlist._subcircuit_defs)

            ac_cmd = (
                f"ac dec {points_per_decade} "
                f"{format_spice_value(start_freq)} "
                f"{format_spice_value(stop_freq)}"
            )
            net.add_control(
                ac_cmd,
                f"wrdata {data_file} {' '.join(signals)}",
            )
            spice_file.write_text(net.to_string())

            _run_ngspice_subprocess(str(spice_file), timeout=300)
            return _parse_wrdata_ac(data_file, signals)

    def _detect_signals(self) -> list[str]:
        """Auto-detect signals from the netlist.

        Returns node voltages as v(name) and branch currents through
        inductors and voltage sources as i(name).  Only top-level elements
        are included (subcircuit-internal nodes/branches are excluded).
        Note: ngspice does not support i() probes for current sources (I*).
        """
        nodes: set[str] = set()
        branch_elements: set[str] = set()
        # Only scan top-level lines (not subcircuit definitions)
        for line in self._netlist._lines:
            parts = line.split()
            if len(parts) < 3:
                continue
            first_char = parts[0][0].upper()
            if first_char in "RVCLDIB":
                # Element line: NAME NODE1 NODE2 ...
                for node in parts[1:3]:
                    if node != "0":
                        nodes.add(node)
                # Record branch currents for inductors and voltage sources
                # Note: current sources (I*) are NOT supported by ngspice i()
                if first_char in "LV":
                    branch_elements.add(parts[0])
            elif first_char == "X":
                if len(parts) >= 3:
                    pin_end = len(parts)
                    for i in range(1, len(parts)):
                        if "=" in parts[i]:
                            pin_end = i
                            break
                    for node in parts[1 : pin_end - 1]:
                        if node != "0":
                            nodes.add(node)
        signals = sorted(f"v({n})" for n in nodes)
        signals.extend(sorted(f"i({e})" for e in branch_elements))
        return signals



# ---------------------------------------------------------------------------
# Internal parsers & runners
# ---------------------------------------------------------------------------

@dataclass
class _SimulationResult:
    """Internal: parsed results from ngspice stdout."""
    node_voltages: dict[str, float] = field(default_factory=dict)
    branch_currents: dict[str, float] = field(default_factory=dict)


def _parse_ngspice_output(output: str) -> _SimulationResult:
    """Parse ngspice batch-mode stdout into structured results."""
    result = _SimulationResult()

    pattern = re.compile(r"^\s*(\S+)\s*=\s*([+-]?\d+\.?\d*(?:e[+-]?\d+)?)", re.MULTILINE)
    for match in pattern.finditer(output):
        name = match.group(1).lower()
        value = float(match.group(2))
        if name.startswith("v(") or name.startswith("i("):
            if name.startswith("v("):
                result.node_voltages[name] = value
            else:
                result.branch_currents[name] = value
        elif "#branch" in name:
            source = name.split("#branch")[0]
            result.branch_currents[f"i({source})"] = value
        else:
            result.node_voltages[f"v({name})"] = value

    return result


def _parse_wrdata(path: Path, signal_names: list[str]) -> TransientResult:
    """Parse an ngspice wrdata output file."""
    time: list[float] = []
    # Normalize signal names to lowercase for consistent lookup
    # (TransientResult._resolve always lowercases keys)
    normalized = [name.lower() for name in signal_names]
    signals: dict[str, list[float]] = {name: [] for name in normalized}
    n = len(signal_names)

    text = path.read_text()
    for line in text.strip().splitlines():
        parts = line.split()
        if len(parts) < 2 * n:
            continue
        try:
            t = float(parts[0])
        except ValueError:
            continue
        time.append(t)
        for i, name in enumerate(normalized):
            signals[name].append(float(parts[2 * i + 1]))

    return TransientResult(time=time, signals=signals)


def _parse_wrdata_ac(path: Path, signal_names: list[str]) -> ACResult:
    """Parse an ngspice wrdata output file from AC analysis.

    AC wrdata format: each signal produces THREE columns (freq, real, imaginary).
    ngspice repeats the frequency column for every signal.
    Line format: freq re(sig1) im(sig1)  freq re(sig2) im(sig2) ...
    """
    freq: list[float] = []
    normalized = [name.lower() for name in signal_names]
    signals_real: dict[str, list[float]] = {name: [] for name in normalized}
    signals_imag: dict[str, list[float]] = {name: [] for name in normalized}
    n = len(signal_names)

    text = path.read_text()
    for line in text.strip().splitlines():
        parts = line.split()
        # Need: 3 columns per signal (freq, real, imag) — freq is repeated
        if len(parts) < 3 * n:
            continue
        try:
            f = float(parts[0])
        except ValueError:
            continue
        freq.append(f)
        for i, name in enumerate(normalized):
            signals_real[name].append(float(parts[3 * i + 1]))
            signals_imag[name].append(float(parts[3 * i + 2]))

    return ACResult(freq=freq, signals_real=signals_real, signals_imag=signals_imag)


def _run_ngspice_subprocess(spice_path: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run ngspice in batch mode on a .spice file."""
    try:
        proc = subprocess.run(
            ["ngspice", "-b", spice_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            "ngspice not found. Install it with:\n"
            "  macOS:  brew install ngspice\n"
            "  Linux:  apt install ngspice"
        )

    if proc.returncode != 0:
        raise RuntimeError(
            f"ngspice exited with code {proc.returncode}\n"
            f"stderr: {proc.stderr}\n"
            f"stdout: {proc.stdout}"
        )
    return proc


def _run_ngspice_batch(netlist: SpiceNetlist) -> str:
    """Write a SpiceNetlist to a temp file, run ngspice, return stdout."""
    tmp = tempfile.NamedTemporaryFile(suffix=".spice", mode="w", delete=False)
    tmp.write(netlist.to_string())
    tmp.close()
    try:
        proc = _run_ngspice_subprocess(tmp.name)
        return proc.stdout
    finally:
        os.unlink(tmp.name)


def _load_spice_circuit(path: Path | str) -> SpiceNetlist:
    """Load a .spice file into a SpiceNetlist.

    Separates .SUBCKT/.ENDS blocks and .model lines into _subcircuit_defs,
    keeping element lines in _lines.
    """
    path = Path(path)
    text = path.read_text()
    netlist = SpiceNetlist()
    in_control = False
    in_subckt = False
    subckt_block: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("*"):
            if netlist.title == "Untitled":
                netlist.title = stripped.lstrip("* ").strip() or "Untitled"
            # Parse embedded component map
            if "* @component_map:" in stripped:
                map_str = stripped.split("@component_map:", 1)[1].strip()
                for entry in map_str.split(","):
                    entry = entry.strip()
                    if "=" in entry:
                        path, designator = entry.split("=", 1)
                        netlist.component_map[path.strip()] = designator.strip()
            if in_subckt:
                subckt_block.append(stripped)
            continue
        if stripped.lower() == ".control":
            in_control = True
            continue
        if stripped.lower() == ".endc":
            in_control = False
            continue
        if in_control:
            continue
        if stripped.lower() == ".end" or not stripped:
            continue

        # Handle .SUBCKT/.ENDS blocks
        if re.match(r"\.SUBCKT\b", stripped, re.IGNORECASE):
            in_subckt = True
            subckt_block = [stripped]
            continue
        if re.match(r"\.ENDS\b", stripped, re.IGNORECASE):
            subckt_block.append(stripped)
            netlist._subcircuit_defs.append("\n".join(subckt_block))
            in_subckt = False
            subckt_block = []
            continue
        if in_subckt:
            subckt_block.append(stripped)
            continue

        # Handle standalone .model lines
        if re.match(r"\.model\b", stripped, re.IGNORECASE):
            netlist._subcircuit_defs.append(stripped)
            continue

        netlist._lines.append(stripped)
    return netlist


# Backwards-compatible alias used by build_steps.py
load_spice_circuit = _load_spice_circuit


# ---------------------------------------------------------------------------
# Build-step internals (generate_spice_netlist)
# ---------------------------------------------------------------------------

def _sanitize_net_name(name: str) -> str:
    """Sanitize a node name for SPICE compatibility.

    Lowercases the result since SPICE is case-insensitive and ngspice
    normalises all identifiers to lowercase internally.
    """
    result = re.sub(r"[\.\[\]\s]+", "_", name)
    result = result.strip("_")
    return (result or "unnamed").lower()


def _get_nominal_value(param_node) -> float | None:
    """Extract the nominal (center) value of a numeric parameter.

    Tries multiple extraction paths to handle different solver states:

    1. ``try_extract_superset()`` — works when solver has resolved constraints
       to a finite [min, max] range (e.g. direct assignments like ``10uF +/- 20%``).
    2. ``has_part_picked.get_attribute()`` — uses the picked part's stored
       attribute value when the solver hasn't resolved constraints (e.g.
       for-loop-constrained parameters like MultiCapacitor children).

    Args:
        param_node: A NumericParameter node (e.g. resistor.capacitance.get()).
    """
    import faebryk.core.node as fabll
    import faebryk.library._F as F

    # Path 1: direct superset extraction (works for most resolved parameters)
    try:
        numbers = param_node.try_extract_superset()
        if numbers is not None:
            min_val = numbers.get_min_value()
            max_val = numbers.get_max_value()
            if not math.isinf(min_val) and not math.isinf(max_val):
                return (min_val + max_val) / 2.0
    except Exception as e:
        logger.debug(f"_get_nominal_value path 1 (try_extract_superset) failed: {e}")

    # Path 2: from picked part attribute on the direct parent module
    try:
        parent_info = param_node.get_parent()
        if parent_info:
            parent_module = parent_info[0]
            param_name = parent_info[1]
            part_picked = parent_module.get_trait(F.Pickable.has_part_picked)
            attr_lit = part_picked.get_attribute(param_name)
            if attr_lit is not None:
                # attr_lit is an is_literal trait on a Numbers node;
                # get the Numbers node it's attached to and cast properly
                numbers_node = fabll.Traits(attr_lit).get_obj_raw()
                numbers_typed = numbers_node.cast(F.Literals.Numbers)
                min_val = numbers_typed.get_min_value()
                max_val = numbers_typed.get_max_value()
                if not math.isinf(min_val) and not math.isinf(max_val):
                    return (min_val + max_val) / 2.0
    except Exception as e:
        logger.debug(f"_get_nominal_value path 2 (has_part_picked) failed: {e}")

    return None


def _resolve_param_bindings(
    node, bindings: dict[str, str]
) -> dict[str, str]:
    """Resolve param_bindings by looking up NumericParameter values on node or ancestors.

    For each binding (e.g. ``{"FS": "switching_frequency"}``), walks up from
    *node* through its ancestors looking for a ``NumericParameter`` child whose
    attribute name matches the ato param name.  Returns a dict of resolved
    SPICE parameter overrides (e.g. ``{"FS": "400000.0"}``).
    """
    import faebryk.library._F as F

    resolved: dict[str, str] = {}
    for spice_param, ato_param_name in bindings.items():
        current = node
        while current is not None:
            for child in current.get_children(
                direct_only=True, types=F.Parameters.NumericParameter
            ):
                child_name = (
                    child.get_full_name(include_uuid=False).rsplit(".", 1)[-1]
                )
                if child_name == ato_param_name:
                    val = _get_nominal_value(child)
                    if val is not None:
                        resolved[spice_param] = str(val)
                    break
            if spice_param in resolved:
                break
            parent_info = current.get_parent()
            current = parent_info[0] if parent_info else None
    return resolved


def generate_spice_netlist(
    app, solver, scope=None,
) -> tuple[SpiceNetlist, dict[str, str]]:
    """Auto-generate a SPICE netlist from the atopile instance graph.

    Walks the graph to find:
    - Resistors, Capacitors, Inductors -> SPICE elements
    - ElectricPower with voltage constraints -> voltage sources
    - Connected Electrical interfaces -> SPICE nets

    Args:
        app: The application root node (fabll.Node).
        solver: The solver used for parameter resolution.
        scope: Optional subtree root to limit netlist generation to.
               When provided, only components within this scope are included.
               Defaults to app (full circuit).

    Returns:
        (netlist, net_aliases) — the SpiceNetlist and a dict mapping
        alternative sanitized net names to the canonical SPICE net name.
    """
    import faebryk.core.node as fabll
    import faebryk.library._F as F

    root = scope or app
    title = root.get_full_name(include_uuid=False) or "Circuit"
    netlist = SpiceNetlist(title=title)

    # 0. Run solver for numeric parameters so extract_superset works.
    #    This is best-effort: the main build step should have already
    #    simplified parameters.  If the solver encounters unsupported
    #    expression types (e.g. StringParameters from traits), log a
    #    warning and continue with whatever values are already resolved.
    all_params: list[F.Parameters.can_be_operand] = []
    for param in root.get_children(
        direct_only=False,
        types=F.Parameters.NumericParameter,
        include_root=True,
    ):
        param_trait = param.get_trait(F.Parameters.is_parameter)
        all_params.append(param_trait.as_operand.get())

    if all_params:
        try:
            solver.simplify_for(*all_params)
            logger.info(
                f"Simplified {len(all_params)} parameters for SPICE extraction"
            )
        except Exception:
            logger.warning(
                "Solver simplification failed for SPICE extraction — "
                "using pre-existing parameter values",
                exc_info=True,
            )

    # 1. Collect all Electrical interfaces in the design
    electricals = root.get_children(
        direct_only=False,
        types=F.Electrical,
    )
    logger.info(f"Found {len(electricals)} Electrical interfaces")

    if not electricals:
        return netlist, {}

    # 2. Group into buses (connected nets)
    buses = fabll.is_interface.group_into_buses(electricals)
    logger.info(f"Grouped into {len(buses)} buses")

    # 3. Build mapping: each Electrical node -> its net name
    electrical_to_net: dict = {}
    # Also build an alias map: every sanitized member name -> canonical net name
    # This lets requirements reference nets by any of their ato-level names
    net_aliases: dict[str, str] = {}

    net_counter = 0
    for _, members in buses.items():
        net_name = None
        all_candidates: list[str] = []
        for member in members:
            full_name = member.get_full_name(include_uuid=False)
            if full_name:
                candidate = _sanitize_net_name(full_name)
                all_candidates.append(candidate)
                if net_name is None or len(candidate) < len(net_name):
                    net_name = candidate

        if net_name is None:
            net_name = f"net_{net_counter}"

        net_counter += 1

        for member in members:
            electrical_to_net[member] = net_name

        # Register all candidate names as aliases to the canonical name
        for alias in all_candidates:
            if alias != net_name:
                net_aliases[alias] = net_name

    def _net(electrical) -> str:
        return electrical_to_net.get(electrical, "?")

    # 4. Detect ground net from ElectricPower interfaces with voltage constraints.
    #    Users define all voltage sources explicitly via the simulation `spice` field,
    #    so we only need to identify which net is ground and remap it to "0".
    ground_net_name: str | None = None

    power_rails = root.get_children(
        direct_only=False,
        types=F.ElectricPower,
    )

    for power in power_rails:
        voltage_param = power.voltage.get()
        voltage = _get_nominal_value(voltage_param)
        if voltage is None or voltage == 0:
            continue

        lv = power.lv.get()
        lv_net = _net(lv)
        if lv_net != "?":
            ground_net_name = lv_net
            break

    if ground_net_name is None:
        logger.warning("No ElectricPower with voltage constraint found; "
                       "cannot determine ground net")

    # Remap ground net to "0"
    if ground_net_name is not None:
        for node_key in list(electrical_to_net.keys()):
            if electrical_to_net[node_key] == ground_net_name:
                electrical_to_net[node_key] = "0"

    # Helper: compute relative component path from root for the component map
    root_full_name = root.get_full_name(include_uuid=False) or ""

    def _rel_path(component) -> str | None:
        """Relative path of *component* from the netlist scope root."""
        full = component.get_full_name(include_uuid=False)
        if not full:
            return None
        if root_full_name and full.startswith(root_full_name + "."):
            return full[len(root_full_name) + 1:]
        return full

    # 6. Find and add Resistors
    r_counter = 1
    for resistor in root.get_children(direct_only=False, types=F.Resistor):
        resistance = _get_nominal_value(resistor.resistance.get())
        if resistance is None:
            logger.warning(f"Skipping resistor {resistor.get_full_name(include_uuid=False)}: "
                           "no resistance value")
            continue

        pins = resistor.unnamed
        if len(pins) < 2:
            continue

        pin0 = pins[0].get()
        pin1 = pins[1].get()
        designator = f"R{r_counter}"
        netlist.add_resistor(designator, _net(pin0), _net(pin1), resistance)
        rel = _rel_path(resistor)
        if rel:
            netlist.component_map[rel] = designator
        r_counter += 1

    # 7. Find and add Capacitors
    c_counter = 1
    for capacitor in root.get_children(direct_only=False, types=F.Capacitor):
        capacitance = _get_nominal_value(capacitor.capacitance.get())
        if capacitance is None:
            logger.warning(
                f"Skipping capacitor"
                f" {capacitor.get_full_name(include_uuid=False)}:"
                f" no capacitance value"
            )
            continue

        pins = capacitor.unnamed
        if len(pins) < 2:
            continue

        pin0 = pins[0].get()
        pin1 = pins[1].get()
        designator = f"C{c_counter}"
        netlist.add_capacitor(designator, _net(pin0), _net(pin1), capacitance)
        rel = _rel_path(capacitor)
        if rel:
            netlist.component_map[rel] = designator
        c_counter += 1

    # 8. Find and add Inductors
    l_counter = 1
    for inductor in root.get_children(direct_only=False, types=F.Inductor):
        inductance = _get_nominal_value(inductor.inductance.get())
        if inductance is None:
            logger.warning(f"Skipping inductor {inductor.get_full_name(include_uuid=False)}: "
                           "no inductance value")
            continue

        pins = inductor.unnamed
        if len(pins) < 2:
            continue

        pin0 = pins[0].get()
        pin1 = pins[1].get()
        designator = f"L{l_counter}"
        netlist.add_inductor(designator, _net(pin0), _net(pin1), inductance)
        rel = _rel_path(inductor)
        if rel:
            netlist.component_map[rel] = designator
        l_counter += 1

    # 9. Find and add subcircuit instances for nodes with has_spice_model trait
    from faebryk.exporters.simulation.spice_converter import (
        convert_pspice_to_ngspice,
        extract_all_subcircuits_and_models,
        parse_subcircuit_pins,
    )

    x_counter = 1
    included_model_files: set[str] = set()

    for node in root.get_children(
        direct_only=False,
        types=fabll.Node,
        include_root=False,
        required_trait=F.has_spice_model,
    ):
        trait = node.get_trait(F.has_spice_model)

        try:
            model_file_path = trait.get_model_file_path()
            subckt_name = trait.get_subcircuit_name()
            pin_map = trait.get_pin_map()
            param_overrides = trait.get_params()
            # Resolve dynamic param_bindings (e.g. FS -> switching_frequency)
            # 1. Check has_spice_model's own param_bindings (backwards compat)
            bindings = trait.get_param_bindings()
            # 2. If empty, walk ancestors for has_spice_param_bindings trait
            if not bindings:
                current = node
                while current is not None:
                    try:
                        ancestor_trait = current.get_trait(
                            F.has_spice_param_bindings
                        )
                        bindings = ancestor_trait.get_bindings()
                        if bindings:
                            break
                    except Exception:
                        pass
                    parent_info = current.get_parent()
                    current = parent_info[0] if parent_info else None
            if bindings:
                resolved = _resolve_param_bindings(node, bindings)
                param_overrides.update(resolved)
        except Exception as e:
            logger.warning(
                f"Skipping has_spice_model node "
                f"{node.get_full_name(include_uuid=False)}: {e}"
            )
            continue

        # Load & convert model file (include defs once per unique file)
        model_key = str(model_file_path)
        if model_key not in included_model_files:
            try:
                raw_model = model_file_path.read_text()
                converted = convert_pspice_to_ngspice(raw_model)
                subckt_defs = extract_all_subcircuits_and_models(converted)
                if subckt_defs.strip():
                    netlist.add_subcircuit_definitions(subckt_defs)
                included_model_files.add(model_key)
                logger.info(f"Included SPICE model definitions from {model_file_path}")
            except FileNotFoundError:
                logger.warning(f"SPICE model file not found: {model_file_path}")
                continue
            except Exception as e:
                logger.warning(f"Failed to load SPICE model {model_file_path}: {e}")
                continue

        # Get subcircuit pin order from the original model file
        raw_model = model_file_path.read_text()
        subckt_pins = parse_subcircuit_pins(raw_model, subckt_name)
        if not subckt_pins:
            logger.warning(
                f"No pins found for subcircuit {subckt_name} in {model_file_path}"
            )
            continue

        # Build X instance line: X<n> <pin_nets...> <subckt_name> [params...]
        pin_nets: list[str] = []
        for subckt_pin in subckt_pins:
            ato_iface_name = pin_map.get(subckt_pin)
            if ato_iface_name is None:
                # Try case-insensitive match
                for k, v in pin_map.items():
                    if k.upper() == subckt_pin.upper():
                        ato_iface_name = v
                        break

            if ato_iface_name is None:
                logger.warning(
                    f"No pin mapping for subcircuit pin '{subckt_pin}' "
                    f"in {node.get_full_name(include_uuid=False)}"
                )
                pin_nets.append("?")
                continue

            # Resolve the interface on the node to its net name
            try:
                import faebryk.core.faebrykpy as fbrk

                child_bn = fbrk.EdgeComposition.get_child_by_identifier(
                    bound_node=node.instance,
                    child_identifier=ato_iface_name,
                )
                if child_bn is not None:
                    electrical = fabll.Node(child_bn)
                    net_name = _net(electrical)
                    pin_nets.append(net_name)
                else:
                    logger.warning(
                        f"Child '{ato_iface_name}' not found "
                        f"on {node.get_full_name(include_uuid=False)}"
                    )
                    pin_nets.append("?")
            except Exception as e:
                logger.warning(
                    f"Failed to resolve interface '{ato_iface_name}' "
                    f"on {node.get_full_name(include_uuid=False)}: {e}"
                )
                pin_nets.append("?")

        # Build param string
        param_str = ""
        if param_overrides:
            param_str = " " + " ".join(
                f"{k}={v}" for k, v in param_overrides.items()
            )

        designator = f"X{x_counter}"
        x_line = f"{designator} {' '.join(pin_nets)} {subckt_name}{param_str}"
        netlist.add_raw(x_line)
        rel = _rel_path(node)
        if rel:
            netlist.component_map[rel] = designator
        logger.info(
            f"Added subcircuit instance {designator} "
            f"({subckt_name}) for {node.get_full_name(include_uuid=False)}"
        )
        x_counter += 1

    if netlist.component_map:
        logger.info(
            "Component map: "
            + ", ".join(f"{p}={d}" for p, d in sorted(netlist.component_map.items()))
        )

    return netlist, net_aliases
