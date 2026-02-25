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
    "spice", "spice_template", "param_values",
    "time_start", "time_stop", "time_step",
    "duts", "remove_elements",
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
    dut_name: str | None = None,
    dut_params: dict[str, float] | None = None,
    remove_elements: str | None = None,
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
        _resolve_dut_references,
        _resolve_net_aliases,
    )

    spice_path = Path(netlist_path)
    if not spice_path.is_file():
        raise FileNotFoundError(f"Netlist not found: {netlist_path}")

    # Load net aliases from companion file
    alias_path = spice_path.with_suffix(".aliases.txt")
    net_aliases = _parse_alias_file(alias_path) if alias_path.is_file() else {}
    # Always use alias-file dut_name for SPICE net resolution — the JSON
    # dutName is the ato-level name (e.g. "dut_400k") which differs from
    # the SPICE netlist name (e.g. "dut48").
    spice_dut_name = _parse_dut_name(alias_path) if alias_path.is_file() else None

    # Load circuit and apply sources
    circuit = Circuit.load(spice_path)

    # Remove elements specified by the simulation (e.g. load resistors
    # replaced by explicit current sources in the SPICE definition).
    if remove_elements:
        for elem in remove_elements.split(","):
            elem = elem.strip()
            if elem:
                circuit.remove_element(elem)

    if spice_sources:
        resolved = spice_sources
        # Resolve dut.X.Y dot-notation → spice_dut_name_X_Y underscore format
        if spice_dut_name:
            resolved = _resolve_dut_references(
                resolved, spice_dut_name, dut_params or {}
            )
        resolved = _resolve_net_aliases(resolved, net_aliases)
        # Remove auto-generated DC bias sources (V1, V2, V3 — numeric suffix)
        # from the saved netlist.  KEEP behavioral model sources (V_ss, V_slope,
        # V_clk, V_minon) which are critical for the switching controller.
        _v_bias_pattern = re.compile(r'^V\d+$', re.IGNORECASE)
        for line in list(circuit._netlist._lines):
            name = line.split()[0] if line.strip() else ""
            if name and _v_bias_pattern.match(name):
                circuit.remove_element(name)
        # Also remove specific elements named in the new sources to avoid
        # "device already exists" errors (e.g. V1, Vsense, Iload).
        for part in resolved.split("|"):
            part = part.strip()
            if part:
                elem_name = part.split()[0]
                circuit.remove_element(elem_name)
        _apply_spice_source(circuit, resolved)

    # --- Resolve net name to canonical SPICE name ---
    # The requirement JSON stores generic names like "dut_power_out_hv".
    # The SPICE netlist uses DUT-specific names like "dut48_power_out_hv".
    has_wrapper = net.startswith(("v(", "i("))
    if has_wrapper:
        wrapper_prefix = net[:2]  # "v(" or "i("
        inner = net[2:-1]         # strip v(...) / i(...)
    else:
        wrapper_prefix = "v("
        inner = net

    # Step 1: Prepend SPICE DUT name (dut_ → dut48_)
    if spice_dut_name and inner.startswith("dut_"):
        inner = f"{spice_dut_name}_{inner[4:]}"
    inner = inner.replace(".", "_")
    # Step 2: Resolve through aliases
    inner = net_aliases.get(inner, inner)

    net_key = f"{wrapper_prefix}{net[2:-1] if has_wrapper else net})"
    resolved_net = f"{wrapper_prefix}{inner})"

    log.info(
        "Single rerun: net=%s → resolved=%s (spice_dut=%s)",
        net, resolved_net, spice_dut_name,
    )

    # Run simulation
    if sim_type == "transient":
        # Use the same TMAX as the main simulation runner (50ns).
        # This is the maximum internal timestep for convergence — NOT the
        # output step.  Using tran_step * 25 was far too small and caused
        # ngspice to produce millions of data points → OOM / SIGKILL.
        TMAX = 50e-9
        result = circuit.tran(
            step=tran_step,
            stop=tran_stop,
            start=0,
            uic=True,
            tmax=TMAX,
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

        # Find the signal data — try multiple name variants
        signal_data = (
            result_signals.get(resolved_net)
            or result_signals.get(net_key)
        )
        if signal_data is None:
            # Fuzzy fallback: search for a signal containing the resolved name
            target = inner.lower()
            for sk, sv in result_signals.items():
                if target in sk.lower():
                    signal_data = sv
                    log.info("Fuzzy signal match: %s → %s", resolved_net, sk)
                    break

        if signal_data is None:
            log.warning(
                "Signal not found: tried %s, %s. Available: %s",
                resolved_net, net_key, list(result_signals.keys())[:20],
            )

        # Measure
        actual = float("nan")
        if signal_data is not None:
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

        def _resolve_net_to_signal(n: str) -> str:
            """Resolve a generic net name to the DUT-specific SPICE signal key."""
            has_wrap = n.startswith(("v(", "i("))
            prefix = n[:2] if has_wrap else "v("
            raw = n[2:-1] if has_wrap else n
            if spice_dut_name and raw.startswith("dut_"):
                raw = f"{spice_dut_name}_{raw[4:]}"
            raw = raw.replace(".", "_")
            raw = net_aliases.get(raw, raw)
            return f"{prefix}{raw})"

        # Include primary net + context nets
        all_nets = [net_key]
        for cn in (context_nets or []):
            cnk = f"v({cn})" if not cn.startswith(("v(", "i(")) else cn
            all_nets.append(cnk)

        for nk in all_nets:
            resolved_nk = _resolve_net_to_signal(nk)
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


def _parse_dut_name(path: Path) -> str | None:
    """Extract the ``dut_name:`` header from a .aliases.txt file."""
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("dut_name:"):
            return line.split(":", 1)[1].strip()
        if line == "=== Net Aliases ===":
            break
    return None


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
