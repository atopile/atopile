"""Ngspice simulation API.

User-facing API:
    Circuit     — load a .spice file, run .op() and .tran() analyses
    OpResult    — dict-like DC operating point results
    TransientResult — signal access + .plot()
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
    rise: float = 1e-9,
    fall: float = 1e-9,
    width: float = 10,
    period: float = 10,
) -> str:
    """Return a SPICE PULSE source specification.

    >>> pulse(0, 10, delay=0.5)
    'PULSE(0 10 500m 1n 1n 10 10)'
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

    def to_string(self) -> str:
        """Render the complete SPICE netlist as a string."""
        lines = [f"* {self.title}"]
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
    ) -> TransientResult:
        """Run transient analysis.

        Args:
            step: Timestep in seconds.
            stop: Stop time in seconds.
            signals: Signal names to record. If None, records all node voltages.
            start: Start time for recording (default 0).
        """
        if signals is None:
            signals = self._detect_node_voltages()

        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = Path(tmpdir) / "tran_data.txt"
            spice_file = Path(tmpdir) / "circuit.spice"

            net = SpiceNetlist(title=self._netlist.title)
            net._lines = list(self._netlist._lines)
            net.add_control(
                f"tran {format_spice_value(step)} {format_spice_value(stop)}"
                + (f" {format_spice_value(start)}" if start > 0 else ""),
                f"wrdata {data_file} {' '.join(signals)}",
            )
            spice_file.write_text(net.to_string())

            proc = _run_ngspice_subprocess(str(spice_file), timeout=60)
            return _parse_wrdata(data_file, signals)

    def _detect_node_voltages(self) -> list[str]:
        """Auto-detect node names from the netlist and return as v(name) signals."""
        nodes: set[str] = set()
        for line in self._netlist._lines:
            parts = line.split()
            if len(parts) < 3:
                continue
            first_char = parts[0][0].upper()
            if first_char in "RVCLDI":
                # Element line: NAME NODE1 NODE2 ...
                for node in parts[1:3]:
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
    signals: dict[str, list[float]] = {name: [] for name in signal_names}
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
        for i, name in enumerate(signal_names):
            signals[name].append(float(parts[2 * i + 1]))

    return TransientResult(time=time, signals=signals)


def _run_ngspice_subprocess(spice_path: str, timeout: int = 30) -> subprocess.CompletedProcess:
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
    """Load a .spice file into a SpiceNetlist (circuit lines only, no .control)."""
    path = Path(path)
    text = path.read_text()
    netlist = SpiceNetlist()
    in_control = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("*"):
            if netlist.title == "Untitled":
                netlist.title = stripped.lstrip("* ").strip() or "Untitled"
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


def generate_spice_netlist(app, solver) -> SpiceNetlist:
    """Auto-generate a SPICE netlist from the atopile instance graph.

    Walks the graph to find:
    - Resistors, Capacitors, Inductors -> SPICE elements
    - ElectricPower with voltage constraints -> voltage sources
    - Connected Electrical interfaces -> SPICE nets

    Args:
        app: The application root node (fabll.Node).
        solver: The solver used for parameter resolution.

    Returns:
        A SpiceNetlist containing circuit elements only (no .control section).
    """
    import faebryk.core.node as fabll
    import faebryk.library._F as F

    title = app.get_full_name(include_uuid=False) or "Circuit"
    netlist = SpiceNetlist(title=title)

    # 0. Run solver for all parameters under this app so extract_superset works
    all_params: list[F.Parameters.can_be_operand] = []
    for param in app.get_children(
        direct_only=False,
        types=fabll.Node,
        include_root=True,
        required_trait=F.Parameters.is_parameter,
    ):
        param_trait = param.get_trait(F.Parameters.is_parameter)
        all_params.append(param_trait.as_operand.get())

    if all_params:
        solver.simplify_for(*all_params)
        logger.info(f"Simplified {len(all_params)} parameters for SPICE extraction")

    # 1. Collect all Electrical interfaces in the design
    electricals = app.get_children(
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
    ground_net_name: str | None = None
    power_interfaces: list[tuple[str, float, str, str]] = []

    v_counter = 1
    power_rails = app.get_children(
        direct_only=False,
        types=F.ElectricPower,
    )

    for power in power_rails:
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
    for resistor in app.get_children(direct_only=False, types=F.Resistor):
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
    for capacitor in app.get_children(direct_only=False, types=F.Capacitor):
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
    for inductor in app.get_children(direct_only=False, types=F.Inductor):
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

    return netlist
