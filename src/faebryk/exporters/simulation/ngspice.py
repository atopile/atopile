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
    ) -> TransientResult:
        """Run transient analysis.

        Args:
            step: Timestep in seconds.
            stop: Stop time in seconds.
            signals: Signal names to record. If None, records all node voltages.
            start: Start time for recording (default 0).
            uic: Use Initial Conditions — skip DC operating point, start from
                 zero (or .ic values). Helps convergence for behavioral models.
        """
        if signals is None:
            signals = self._detect_node_voltages()

        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = Path(tmpdir) / "tran_data.txt"
            spice_file = Path(tmpdir) / "circuit.spice"

            net = SpiceNetlist(title=self._netlist.title)
            net._lines = list(self._netlist._lines)
            net._subcircuit_defs = list(self._netlist._subcircuit_defs)

            tran_cmd = (
                f"tran {format_spice_value(step)} {format_spice_value(stop)}"
                + (f" {format_spice_value(start)}" if start > 0 else "")
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
            spice_file.write_text(net.to_string())

            proc = _run_ngspice_subprocess(str(spice_file), timeout=300)
            return _parse_wrdata(data_file, signals)

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
            signals: Signal names to record. If None, records all node voltages.
        """
        if signals is None:
            signals = self._detect_node_voltages()

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

    def _detect_node_voltages(self) -> list[str]:
        """Auto-detect node names from the netlist and return as v(name) signals."""
        nodes: set[str] = set()
        all_lines = self._netlist._subcircuit_defs + self._netlist._lines
        for line in all_lines:
            parts = line.split()
            if len(parts) < 3:
                continue
            first_char = parts[0][0].upper()
            if first_char in "RVCLDIB":
                # Element line: NAME NODE1 NODE2 ...
                for node in parts[1:3]:
                    if node != "0":
                        nodes.add(node)
            elif first_char == "X":
                # X line: XNAME PIN1 PIN2 ... SUBCKT_NAME [params...]
                # Pins are between name and subcircuit name (last non-param token)
                for token in parts[1:]:
                    if "=" in token:
                        break  # Hit parameters
                    if token.startswith("."):
                        break  # Hit directive
                    # Skip the subcircuit name (last token before params)
                    # We'll add all tokens except the last non-param one
                if len(parts) >= 3:
                    # Find where params start
                    pin_end = len(parts)
                    for i in range(1, len(parts)):
                        if "=" in parts[i]:
                            pin_end = i
                            break
                    # pins are parts[1:pin_end-1], parts[pin_end-1] is subckt name
                    for node in parts[1 : pin_end - 1]:
                        if node != "0":
                            nodes.add(node)
        return sorted(f"v({n})" for n in nodes)


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

    AC wrdata format: each signal produces TWO columns (real, imaginary).
    Line format: freq  re(sig1) im(sig1)  re(sig2) im(sig2) ...
    """
    freq: list[float] = []
    normalized = [name.lower() for name in signal_names]
    signals_real: dict[str, list[float]] = {name: [] for name in normalized}
    signals_imag: dict[str, list[float]] = {name: [] for name in normalized}
    n = len(signal_names)

    text = path.read_text()
    for line in text.strip().splitlines():
        parts = line.split()
        # Need: 1 (freq) + 2*n (real+imag per signal) columns minimum
        if len(parts) < 1 + 2 * n:
            continue
        try:
            f = float(parts[0])
        except ValueError:
            continue
        freq.append(f)
        for i, name in enumerate(normalized):
            signals_real[name].append(float(parts[2 * i + 1]))
            signals_imag[name].append(float(parts[2 * i + 2]))

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
    proc = _run_ngspice_subprocess(tmp.name)
    return proc.stdout


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
    """Sanitize a node name for SPICE compatibility."""
    result = re.sub(r"[\.\[\]\s]+", "_", name)
    result = result.strip("_")
    return result or "unnamed"


def _get_nominal_value(param_node) -> float | None:
    """Extract the nominal (center) value of a numeric parameter.

    Uses the NumericParameter.try_extract_superset() method (same pattern
    as the power_tree exporter). Returns the midpoint of [min, max] range,
    or None if the parameter is unconstrained or infinite.

    Args:
        param_node: A NumericParameter node (e.g. resistor.resistance.get()).
    """
    try:
        numbers = param_node.try_extract_superset()
        if numbers is None:
            return None
        min_val = numbers.get_min_value()
        max_val = numbers.get_max_value()
        if math.isinf(min_val) or math.isinf(max_val):
            return None
        return (min_val + max_val) / 2.0
    except Exception as e:
        logger.debug(f"Failed to extract parameter value: {e}")
        return None


def generate_spice_netlist(app, solver, scope=None) -> SpiceNetlist:
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
        A SpiceNetlist containing circuit elements only (no .control section).
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
        return netlist

    # 2. Group into buses (connected nets)
    buses = fabll.is_interface.group_into_buses(electricals)
    logger.info(f"Grouped into {len(buses)} buses")

    # 3. Build mapping: each Electrical node -> its net name
    electrical_to_net: dict = {}

    net_counter = 0
    for _, members in buses.items():
        net_name = None
        for member in members:
            full_name = member.get_full_name(include_uuid=False)
            if full_name:
                candidate = _sanitize_net_name(full_name)
                if net_name is None or len(candidate) < len(net_name):
                    net_name = candidate

        if net_name is None:
            net_name = f"net_{net_counter}"

        net_counter += 1

        for member in members:
            electrical_to_net[member] = net_name

    def _net(electrical) -> str:
        return electrical_to_net.get(electrical, "?")

    # 4. Find ElectricPower interfaces with voltage constraints -> voltage sources
    #    If any ElectricPower has the is_source trait, only those get V sources.
    #    Otherwise fall back to all constrained ElectricPower (backward compat).
    ground_net_name: str | None = None
    power_interfaces: list[tuple[str, float, str, str]] = []

    v_counter = 1
    power_rails = root.get_children(
        direct_only=False,
        types=F.ElectricPower,
    )

    # Check if any power rail has is_source
    source_rails = [
        p for p in power_rails if p.has_trait(F.is_source)
    ]
    use_source_filter = len(source_rails) > 0
    candidate_rails = source_rails if use_source_filter else power_rails

    for power in candidate_rails:
        voltage_param = power.voltage.get()
        voltage = _get_nominal_value(voltage_param)
        if voltage is None or voltage == 0:
            continue

        hv = power.hv.get()
        lv = power.lv.get()
        hv_net = _net(hv)
        lv_net = _net(lv)

        if hv_net == "?" or lv_net == "?":
            continue

        if ground_net_name is None:
            ground_net_name = lv_net

        power_interfaces.append((f"V{v_counter}", voltage, hv_net, lv_net))
        v_counter += 1

    # If no source rails found ground from any constrained power rail
    if ground_net_name is None and use_source_filter:
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
                       "SPICE netlist will have no sources")

    # Remap ground net to "0"
    if ground_net_name is not None:
        for node_key in list(electrical_to_net.keys()):
            if electrical_to_net[node_key] == ground_net_name:
                electrical_to_net[node_key] = "0"

    # 5. Add voltage sources
    for vs_name, voltage, hv_net, lv_net in power_interfaces:
        actual_hv = "0" if hv_net == ground_net_name else hv_net
        actual_lv = "0" if lv_net == ground_net_name else lv_net
        netlist.add_voltage_source(vs_name, actual_hv, actual_lv, voltage)

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
        netlist.add_resistor(f"R{r_counter}", _net(pin0), _net(pin1), resistance)
        r_counter += 1

    # 7. Find and add Capacitors
    c_counter = 1
    for capacitor in root.get_children(direct_only=False, types=F.Capacitor):
        capacitance = _get_nominal_value(capacitor.capacitance.get())
        if capacitance is None:
            logger.warning(f"Skipping capacitor {capacitor.get_full_name(include_uuid=False)}: "
                           "no capacitance value")
            continue

        pins = capacitor.unnamed
        if len(pins) < 2:
            continue

        pin0 = pins[0].get()
        pin1 = pins[1].get()
        netlist.add_capacitor(f"C{c_counter}", _net(pin0), _net(pin1), capacitance)
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
        netlist.add_inductor(f"L{l_counter}", _net(pin0), _net(pin1), inductance)
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

        x_line = f"X{x_counter} {' '.join(pin_nets)} {subckt_name}{param_str}"
        netlist.add_raw(x_line)
        logger.info(
            f"Added subcircuit instance X{x_counter} "
            f"({subckt_name}) for {node.get_full_name(include_uuid=False)}"
        )
        x_counter += 1

    return netlist
