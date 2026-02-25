"""Domain logic for updating requirement fields in .ato source files."""

from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

# Only these fields may be edited from the UI
ALLOWED_FIELDS = frozenset({
    # Requirement fields
    "min_val", "max_val", "measurement",
    "tran_start", "tran_stop", "tran_step",
    "settling_tolerance", "net", "capture",
    "ac_start_freq", "ac_stop_freq", "ac_points_per_dec",
    "ac_source_name", "ac_measure_freq", "ac_ref_net",
    # Limit assertion (replaces the whole "assert X.limit within ..." line)
    "limit_expr",
    # Simulation fields
    "spice", "spice_template",
    # Plot (LineChart/BarChart) fields
    "title", "x", "y", "y_secondary", "color",
    "simulation", "plot_limits",
    # Plot type change (replaces "new LineChart" / "new BarChart")
    "plot_type",
    # Requirement → plot link
    "required_plot", "supplementary_plot",
    # Requirement name
    "req_name",
})

VALID_PLOT_TYPES = frozenset({"LineChart", "BarChart"})


def handle_update_requirement(
    source_file: str,
    var_name: str,
    updates: dict[str, str],
) -> dict[str, str]:
    """Apply field updates to a requirement variable in an .ato source file.

    Returns a dict of field -> new_value for each successfully applied update.
    """
    path = Path(source_file)
    if not path.is_file():
        raise FileNotFoundError(f"Source file not found: {source_file}")
    if not path.suffix == ".ato":
        raise ValueError(f"Not an .ato file: {source_file}")

    # Validate fields
    bad_fields = set(updates.keys()) - ALLOWED_FIELDS
    if bad_fields:
        raise ValueError(f"Disallowed fields: {', '.join(sorted(bad_fields))}")

    content = path.read_text(encoding="utf-8")
    applied: dict[str, str] = {}

    for field, new_value in updates.items():
        if field == "limit_expr":
            # Special: replace the assertion expression after "within"
            content, did_replace = _replace_limit_expr(
                content, var_name, new_value
            )
            if did_replace:
                applied[field] = new_value
            else:
                log.warning(
                    "Could not find assert %s.limit in %s", var_name, path
                )
            continue

        if field == "plot_type":
            # Special: replace "new LineChart" / "new BarChart" on the declaration line
            if new_value not in VALID_PLOT_TYPES:
                log.warning("Invalid plot type: %s", new_value)
                continue
            content, did_replace = _replace_plot_type(
                content, var_name, new_value
            )
            if did_replace:
                applied[field] = new_value
            else:
                log.warning(
                    "Could not find %s = new ... in %s", var_name, path
                )
            continue

        content, did_replace = _replace_field(content, var_name, field, new_value)
        if did_replace:
            applied[field] = new_value
        else:
            # Field not found — try inserting after the last known line for var_name
            content, did_insert = _insert_field(content, var_name, field, new_value)
            if did_insert:
                applied[field] = new_value
            else:
                log.warning(
                    "Could not find or insert %s.%s in %s", var_name, field, path
                )

    if applied:
        _atomic_write(path, content)
        log.info("Updated %s in %s: %s", var_name, path.name, applied)

    return applied


def _replace_limit_expr(
    content: str, var_name: str, new_expr: str,
) -> tuple[str, bool]:
    """Replace the expression after 'within' in ``assert var.limit within <expr>``."""
    pattern = re.compile(
        rf'^(\s*assert\s+{re.escape(var_name)}\.limit\s+within\s+).+$',
        re.MULTILINE,
    )
    result, count = pattern.subn(rf'\g<1>{new_expr}', content)
    return result, count > 0


def _replace_plot_type(
    content: str, var_name: str, new_type: str,
) -> tuple[str, bool]:
    """Replace ``var = new LineChart`` with ``var = new BarChart`` (or vice versa)."""
    pattern = re.compile(
        rf'^(\s*{re.escape(var_name)}\s*=\s*new\s+)\w+',
        re.MULTILINE,
    )
    result, count = pattern.subn(rf'\g<1>{new_type}', content)
    return result, count > 0


def _replace_field(
    content: str, var_name: str, field: str, new_value: str,
) -> tuple[str, bool]:
    """Regex-replace an existing assignment like ``var.field = "value"``."""
    # Match both quoted and unquoted values:
    #   req_001.min_val = "11.5"
    #   req_001.min_val = 11.5
    pattern = re.compile(
        rf'^(\s*{re.escape(var_name)}\.{re.escape(field)}\s*=\s*)"([^"]*)"',
        re.MULTILINE,
    )
    result, count = pattern.subn(rf'\1"{new_value}"', content)
    if count > 0:
        return result, True

    # Try unquoted numeric value
    pattern_unquoted = re.compile(
        rf'^(\s*{re.escape(var_name)}\.{re.escape(field)}\s*=\s*)([^\s#\n]+)',
        re.MULTILINE,
    )
    result, count = pattern_unquoted.subn(rf'\1"{new_value}"', content)
    return result, count > 0


def _insert_field(
    content: str, var_name: str, field: str, new_value: str,
) -> tuple[str, bool]:
    """Insert a new field assignment after the last existing line for var_name."""
    # Find all lines matching  var_name.xxx = ...
    pattern = re.compile(
        rf'^(\s*){re.escape(var_name)}\.\w+\s*=.*$', re.MULTILINE
    )
    matches = list(pattern.finditer(content))
    if not matches:
        return content, False

    last_match = matches[-1]
    indent = last_match.group(1)
    new_line = f'{indent}{var_name}.{field} = "{new_value}"'
    insert_pos = last_match.end()
    content = content[:insert_pos] + "\n" + new_line + content[insert_pos:]
    return content, True


def handle_create_plot(
    source_file: str,
    req_var_name: str,
    plot_var_name: str,
    fields: dict[str, str],
    plot_type: str = "LineChart",
) -> dict[str, str]:
    """Create a new plot and link it to a requirement in .ato source.

    Inserts:
        plot_var_name = new <plot_type>
        plot_var_name.title = "..."
        plot_var_name.x = "..."
        ...
        req_var_name.required_plot = "plot_var_name"
    after the last line referencing req_var_name.
    """
    path = Path(source_file)
    if not path.is_file():
        raise FileNotFoundError(f"Source file not found: {source_file}")

    content = path.read_text(encoding="utf-8")

    # Find the last line of the requirement to insert after
    pattern = re.compile(
        rf'^(\s*){re.escape(req_var_name)}\.\w+\s*=.*$', re.MULTILINE
    )
    matches = list(pattern.finditer(content))
    if not matches:
        raise ValueError(f"Requirement variable '{req_var_name}' not found in {path}")

    last_match = matches[-1]
    indent = last_match.group(1)
    insert_pos = last_match.end()

    # Build the new plot block
    lines = [f"\n{indent}{plot_var_name} = new {plot_type}"]
    for fld, val in fields.items():
        lines.append(f'{indent}{plot_var_name}.{fld} = "{val}"')
    # Link to requirement
    lines.append(f'{indent}{req_var_name}.required_plot = "{plot_var_name}"')

    block = "\n".join(lines)
    content = content[:insert_pos] + block + content[insert_pos:]

    _atomic_write(path, content)
    log.info("Created plot %s linked to %s in %s", plot_var_name, req_var_name, path.name)
    return {"plotVarName": plot_var_name, **fields}


def handle_rerun_simulation(
    project_root: str,
    target: str,
) -> dict:
    """Trigger a build (simulation rerun) for the given project and target.

    Uses the existing build infrastructure via ``handle_start_build``.
    Returns the build response dict.
    """
    from atopile.dataclasses import BuildRequest
    from atopile.model import builds as builds_domain

    request = BuildRequest(
        project_root=project_root,
        targets=[target],
    )
    response = builds_domain.handle_start_build(request)
    return {
        "success": response.success,
        "message": response.message,
        "buildTargets": [
            {"buildId": bt.build_id, "target": bt.target}
            for bt in (response.build_targets or [])
        ],
    }


def handle_rerun_single(
    netlist_path: str,
    spice_sources: str,
    sim_type: str,
    net: str,
    measurement: str,
    tran_start: float = 0,
    tran_stop: float = 100e-6,
    tran_step: float = 1e-9,
    settling_tolerance: float | None = None,
    context_nets: list[str] | None = None,
    min_val: float | None = None,
    max_val: float | None = None,
) -> dict:
    """Rerun a single simulation using an existing netlist and return fresh results.

    This skips the full build pipeline (graph, solver, netlist generation) and
    directly invokes ngspice on the saved netlist with the specified sources.
    """
    import math

    from faebryk.exporters.simulation.ngspice import Circuit
    from faebryk.exporters.simulation.requirement import _measure_tran
    from faebryk.exporters.simulation.simulation_runner import (
        _apply_spice_source,
        _resolve_net_aliases,
    )

    spice_path = Path(netlist_path)
    if not spice_path.is_file():
        raise FileNotFoundError(f"Netlist not found: {netlist_path}")

    # Load net aliases from companion file
    alias_path = spice_path.with_suffix(".aliases.txt")
    net_aliases = _parse_alias_file(alias_path) if alias_path.is_file() else {}

    # Load circuit and apply sources
    circuit = Circuit.load(spice_path)
    if spice_sources:
        resolved = _resolve_net_aliases(spice_sources, net_aliases)
        _apply_spice_source(circuit, resolved)

    # Resolve the net name to its canonical SPICE name
    net_key = f"v({net})" if not net.startswith(("v(", "i(")) else net
    resolved_net = net_key
    # Try alias resolution on the inner net name
    inner = net_key[2:-1] if net_key.startswith(("v(", "i(")) else net_key
    if inner in net_aliases:
        prefix = net_key[:2]
        resolved_net = f"{prefix}{net_aliases[inner]})"

    # Run simulation
    if sim_type == "transient":
        tmax = tran_step * 25 if tran_step else None
        result = circuit.tran(
            step=tran_step,
            stop=tran_stop,
            start=0,
            uic=True,
            tmax=tmax,
        )

        # Slice from tran_start
        if tran_start and tran_start > 0:
            start_idx = 0
            for i, t in enumerate(result.time):
                if t >= tran_start:
                    start_idx = i
                    break
            result_time = result.time[start_idx:]
            result_signals = {
                k: v[start_idx:] for k, v in result.signals.items()
            }
        else:
            result_time = result.time
            result_signals = result.signals

        # Find the signal data
        signal_data = result_signals.get(resolved_net)
        if signal_data is None:
            # Try without alias
            signal_data = result_signals.get(net_key)

        # Measure
        actual = float("nan")
        if signal_data:
            actual = _measure_tran(
                measurement, list(signal_data), list(result_time),
                settling_tolerance=settling_tolerance,
                min_val=min_val, max_val=max_val,
            )

        # Pass/fail
        passed = False
        if math.isfinite(actual) and min_val is not None and max_val is not None:
            passed = min_val <= actual <= max_val

        # Build time series for the UI (downsampled)
        MAX_POINTS = 2000
        time_list = list(result_time)
        signals_out: dict[str, list[float]] = {}
        # Include primary net + context nets
        all_nets = [net_key]
        for cn in (context_nets or []):
            cnk = f"v({cn})" if not cn.startswith(("v(", "i(")) else cn
            all_nets.append(cnk)

        for nk in all_nets:
            # Try resolved alias
            inner_n = nk[2:-1] if nk.startswith(("v(", "i(")) else nk
            resolved_nk = nk
            if inner_n in net_aliases:
                resolved_nk = f"{nk[:2]}{net_aliases[inner_n]})"
            sd = result_signals.get(resolved_nk) or result_signals.get(nk)
            if sd:
                signals_out[nk] = list(sd)

        # Simple downsampling
        if len(time_list) > MAX_POINTS:
            step_ds = len(time_list) // MAX_POINTS
            time_list = time_list[::step_ds]
            signals_out = {k: v[::step_ds] for k, v in signals_out.items()}

        return {
            "actual": actual if math.isfinite(actual) else None,
            "passed": passed,
            "timeSeries": {
                "time": time_list,
                "signals": signals_out,
            },
        }

    raise ValueError(f"Unsupported simulation type: {sim_type}")


def _parse_alias_file(path: Path) -> dict[str, str]:
    """Parse a .aliases.txt file into a dict of alias → canonical name."""
    aliases: dict[str, str] = {}
    in_aliases = False
    for line in path.read_text().splitlines():
        line = line.strip()
        if line == "=== Net Aliases ===":
            in_aliases = True
            continue
        if in_aliases and "->" in line:
            parts = line.split("->", 1)
            alias = parts[0].strip()
            canon = parts[1].strip()
            aliases[alias] = canon
    return aliases


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically using tempfile + os.replace."""
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".ato.tmp", prefix=".tmp_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
