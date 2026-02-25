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
    # Plot (LineChart) fields
    "title", "x", "y", "y_secondary", "color",
    "simulation", "plot_limits",
    # Requirement → plot link
    "required_plot", "supplementary_plot",
})


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
            {"buildId": bt.build_id, "target": bt.target, "status": bt.status}
            for bt in (response.build_targets or [])
        ],
    }


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
