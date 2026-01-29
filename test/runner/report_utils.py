"""
Report formatting and utility functions.

Functions for formatting test data, converting between formats, and generating
report sections.
"""

import datetime
import io
import os
import re
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.text import Text

# Configuration (read from environment variables)
PERF_THRESHOLD_PERCENT = float(os.getenv("FBRK_TEST_PERF_THRESHOLD_PERCENT", "0.30"))
PERF_MIN_TIME_DIFF_S = float(os.getenv("FBRK_TEST_PERF_MIN_TIME_DIFF_S", "1.0"))
PERF_MIN_MEMORY_DIFF_MB = float(os.getenv("FBRK_TEST_PERF_MIN_MEMORY_DIFF_MB", "50.0"))
OUTPUT_MAX_BYTES = int(os.getenv("FBRK_TEST_OUTPUT_MAX_BYTES", "0"))
OUTPUT_TRUNCATE_MODE = os.getenv("FBRK_TEST_OUTPUT_TRUNCATE_MODE", "tail")
REPORT_JSON_PATH = Path("artifacts/test-report.json")


def ansi_to_html(text: str) -> str:
    """Convert ANSI escape codes to HTML with inline styles."""
    # Use Rich to parse ANSI and export to HTML
    console = Console(file=io.StringIO(), force_terminal=True, record=True)
    rich_text = Text.from_ansi(text)
    console.print(rich_text, soft_wrap=True)
    # Export with inline styles, extract just the code content
    html_output = console.export_html(inline_styles=True, code_format="{code}")
    return html_output


def extract_params(s: str) -> tuple[str, str]:
    """Extract parameters from a test name."""
    if s.endswith("]") and "[" in s:
        # Find the last '['
        idx = s.rfind("[")
        return s[:idx], s[idx + 1 : -1]
    return s, ""


def split_nodeid(nodeid: str) -> tuple[str, str, str, str]:
    """Split a pytest nodeid into file, class, function, and params."""
    parts = nodeid.split("::")
    file_path = parts[0]
    rest = parts[1:]
    class_name = ""
    function_name = ""
    params = ""
    if len(rest) > 0:
        if len(rest) > 1:
            class_name = "::".join(rest[:-1])
            function_name, params = extract_params(rest[-1])
        else:
            function_name, params = extract_params(rest[0])
    return file_path, class_name, function_name, params


def safe_iso(dt: datetime.datetime | None) -> str | None:
    """Convert datetime to ISO format string."""
    if dt is None:
        return None
    return dt.isoformat(sep=" ", timespec="seconds")


_ANSI_PATTERN = re.compile(r"(?:\x1B\[[0-?]*[ -/]*[@-~])|(?:\x1B\].*?(?:\x07|\x1b\\))")


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    if not text:
        return text
    return _ANSI_PATTERN.sub("", text)


def sanitize_output(output: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove ANSI codes from output dict."""
    if not output:
        return output
    cleaned: dict[str, Any] = {}
    for key, value in output.items():
        cleaned[key] = strip_ansi(value) if isinstance(value, str) else value
    return cleaned


def truncate_text(text: str, max_bytes: int, mode: str) -> tuple[str, dict[str, Any]]:
    """Truncate text to max_bytes."""
    raw = text.encode("utf-8", errors="replace")
    total = len(raw)
    meta = {
        "bytes_total": total,
        "bytes_kept": total,
        "truncated": False,
        "limit": max_bytes,
        "mode": mode,
    }
    if max_bytes <= 0 or total <= max_bytes:
        return text, meta

    kept = raw
    if mode == "head":
        kept = raw[:max_bytes]
        marker = f"\n...[truncated {total - max_bytes} bytes]...\n"
        text_out = kept.decode("utf-8", errors="replace") + marker
    else:
        kept = raw[-max_bytes:]
        marker = f"\n...[truncated {total - max_bytes} bytes]...\n"
        text_out = marker + kept.decode("utf-8", errors="replace")

    meta["bytes_kept"] = len(kept)
    meta["truncated"] = True
    return text_out, meta


def apply_output_limits(
    output: dict[str, str] | None,
    max_bytes: int = OUTPUT_MAX_BYTES,
    mode: str = OUTPUT_TRUNCATE_MODE,
) -> tuple[dict[str, str] | None, dict[str, dict[str, Any]] | None]:
    """Apply output size limits to test output."""
    if not output:
        return None, None
    limited = {}
    meta = {}
    for key, value in output.items():
        if value is None:
            continue
        limited_value, info = truncate_text(value, max_bytes, mode)
        limited[key] = limited_value
        meta[key] = info
    return limited, meta


def percentiles(values: list[float], percentiles_list: list[int]) -> dict[str, float]:
    """Calculate percentiles of a list of values."""
    if not values:
        return {}
    values = sorted(values)
    out: dict[str, float] = {}
    for p in percentiles_list:
        if len(values) == 1:
            out[f"p{p}"] = values[0]
            continue
        k = (len(values) - 1) * (p / 100)
        f = int(k)
        c = min(f + 1, len(values) - 1)
        if f == c:
            out[f"p{p}"] = values[f]
        else:
            d = k - f
            out[f"p{p}"] = values[f] + (values[c] - values[f]) * d
    return out


def outcome_to_str(outcome: Any) -> str | None:
    """Convert outcome enum/string to lowercase string."""
    if outcome is None:
        return None
    if hasattr(outcome, "name"):
        return outcome.name.lower()
    return str(outcome).lower()


def compare_to_str(compare: Any) -> str | None:
    """Convert compare status enum/string to lowercase string."""
    if compare is None:
        return None
    if hasattr(compare, "name"):
        return compare.name.lower()
    return str(compare).lower()


def baseline_record(
    baseline_map: dict[str, dict[str, Any]], nodeid: str
) -> dict[str, Any] | None:
    """Get baseline record for a test."""
    if not baseline_map:
        return None
    record = baseline_map.get(nodeid)
    if not record:
        return None
    if isinstance(record, str):
        return {"outcome": record}
    return record


def compare_status(current: str | None, baseline: str | None) -> str | None:
    """Determine comparison status between current and baseline."""
    if baseline is None:
        return "new"
    if current is None:
        return None
    valid = {"passed", "failed", "error", "crashed", "skipped"}
    if current not in valid:
        return None
    if current == baseline:
        return "same"
    if baseline == "passed" and current in ("failed", "error", "crashed"):
        return "regression"
    if baseline in ("failed", "error", "crashed") and current == "passed":
        return "fixed"
    return "same"


def perf_change(
    current: float | None,
    baseline: float | None,
    min_diff: float = PERF_MIN_TIME_DIFF_S,
    threshold_percent: float = PERF_THRESHOLD_PERCENT,
) -> tuple[float | None, float | None, bool]:
    """Calculate performance change and significance."""
    if not current or not baseline or baseline <= 0 or current <= 0:
        return None, None, False
    diff = current - baseline
    pct = diff / baseline
    significant = abs(diff) >= min_diff and abs(pct) >= threshold_percent
    return diff, pct, significant




def split_error_message(error_message: str | None) -> tuple[str | None, str | None]:
    """Split error message into type and summary."""
    if not error_message:
        return None, None
    msg = error_message.strip()
    if ": " in msg:
        left, right = msg.split(": ", 1)
        if left and " " not in left and len(left) < 64:
            return left, right
    return None, msg


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 1.0:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60.0:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
