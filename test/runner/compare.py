import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
from test.runner.common import Report  # noqa: E402

NEW_REPORT = ROOT / "artifacts" / "test-report.json"

OUTCOME_STYLES = {
    "passed": "green",
    "failed": "red",
    "error": "red bold",
    "skipped": "yellow",
    "crashed": "red bold",
}

# Performance comparison thresholds
PERF_THRESHOLD_PERCENT = 0.30  # 30% change
PERF_MIN_TIME_DIFF_S = 1.0  # minimum 1 second difference to report
PERF_MIN_MEMORY_DIFF_MB = 50.0  # minimum 50MB difference to report

# TODO just integrate this into the html


def style_outcome(outcome: str) -> str:
    style = OUTCOME_STYLES.get(outcome, "white")
    return f"[{style}]{outcome}[/{style}]"


def get_perf_pct(before_val: float, after_val: float) -> float:
    diff = after_val - before_val
    if before_val > 0:
        return (diff / before_val) * 100
    return 100.0 if diff > 0 else 0.0


def format_perf_change(before_val: float, after_val: float, unit: str) -> str:
    """Format a performance change with percentage and absolute values."""
    diff = after_val - before_val
    pct = get_perf_pct(before_val, after_val)

    sign = "+" if diff >= 0 else ""
    color = "red" if diff > 0 else "green"
    return f"[{color}]{sign}{pct:.1f}%[/{color}] ({before_val:.1f} → {after_val:.1f} {unit})"


def check_perf_regression(before_val: float, after_val: float, min_diff: float) -> bool:
    """
    Check if performance changed significantly.
    Returns True if the difference is > 30% AND exceeds the minimum threshold.
    """
    diff = abs(after_val - before_val)
    if diff < min_diff:
        return False
    if before_val > 0:
        pct_change = diff / before_val
        return pct_change > PERF_THRESHOLD_PERCENT
    return after_val > min_diff


def main(
    before_report: Path,
    show_perf: Annotated[
        bool,
        typer.Option(
            "--perf", "-p", help="Show performance changes (time/memory > 30%)"
        ),
    ] = False,
    black_filter: Annotated[
        str | None,
        typer.Option("--black-filter", "-b", help="Filter out blacklisted tests"),
    ] = None,
):
    before = Report.from_json(before_report.read_text())
    after = Report.from_json(NEW_REPORT.read_text())

    before_tests = {
        t.fullnodeid: t
        for t in before.tests
        if not black_filter or black_filter not in t.fullnodeid
    }
    after_tests = {
        t.fullnodeid: t
        for t in after.tests
        if not black_filter or black_filter not in t.fullnodeid
    }

    console = Console()

    # Build rows for the table
    rows: list[tuple[str, str, str, str]] = []

    def sanitize_node_id(node_id: str) -> str:
        return node_id.replace("[", " ").replace("]", "")

    # New tests (in after but not in before)
    for k in after_tests:
        if k not in before_tests:
            t = after_tests[k]
            rows.append(
                (
                    sanitize_node_id(t.fullnodeid),
                    "[cyan]NEW[/cyan]",
                    "-",
                    style_outcome(t.outcome),
                )
            )

        # Changed tests (outcome changed)
        elif before_tests[k].outcome != after_tests[k].outcome:
            rows.append(
                (
                    sanitize_node_id(k),
                    "[yellow]CHANGED[/yellow]",
                    style_outcome(before_tests[k].outcome),
                    style_outcome(after_tests[k].outcome),
                )
            )

    # Lost tests (in before but not in after)
    for k in before_tests:
        if k not in after_tests:
            t = before_tests[k]
            rows.append(
                (
                    sanitize_node_id(t.fullnodeid),
                    "[magenta]REMOVED[/magenta]",
                    style_outcome(t.outcome),
                    "-",
                )
            )

    # Performance changes (only if --perf flag is set)
    perf_rows: list[tuple[str, str, str]] = []
    perf_rows_with_sort_key: list[tuple[float, tuple[str, str, str]]] = []

    if show_perf:
        for k in after_tests:
            if k not in before_tests:
                continue  # Skip new tests for perf comparison

            before_t = before_tests[k]
            after_t = after_tests[k]

            if after_t.outcome != "passed":
                continue

            time_changed = check_perf_regression(
                before_t.duration, after_t.duration, PERF_MIN_TIME_DIFF_S
            )
            # Use memory_peak_mb for comparison (more representative of actual usage)
            mem_changed = check_perf_regression(
                before_t.memory_usage_mb,
                after_t.memory_usage_mb,
                PERF_MIN_MEMORY_DIFF_MB,
            )

            if time_changed or mem_changed:
                time_pct = (
                    get_perf_pct(before_t.duration, after_t.duration)
                    if time_changed
                    else 0.0
                )
                mem_pct = (
                    get_perf_pct(before_t.memory_usage_mb, after_t.memory_usage_mb)
                    if mem_changed
                    else 0.0
                )
                # Sort by max absolute percentage change
                max_pct = time_pct if time_changed else mem_pct

                time_str = (
                    format_perf_change(before_t.duration, after_t.duration, "s")
                    if time_changed
                    else "-"
                )
                mem_str = (
                    format_perf_change(
                        before_t.memory_usage_mb, after_t.memory_usage_mb, "MB"
                    )
                    if mem_changed
                    else "-"
                )
                perf_rows_with_sort_key.append(
                    (max_pct, (sanitize_node_id(k), time_str, mem_str))
                )

        # Sort descending by max percentage change
        perf_rows_with_sort_key.sort(key=lambda x: x[0], reverse=True)
        perf_rows = [row for _, row in perf_rows_with_sort_key]

    if not rows and not perf_rows:
        console.print("[green]No test changes detected.[/green]")
        return

    # Create and populate the test changes table
    if rows:
        table = Table(title="Test Changes", show_lines=True)
        table.add_column("Test", style="dim", no_wrap=False)
        table.add_column("Status", justify="center")
        table.add_column("Before", justify="center")
        table.add_column("After", justify="center")

        for row in rows:
            table.add_row(*row)

        console.print(table)

        # Summary
        new_count = sum(1 for r in rows if "NEW" in r[1])
        changed_count = sum(1 for r in rows if "CHANGED" in r[1])
        removed_count = sum(1 for r in rows if "REMOVED" in r[1])
        console.print(
            f"\n[bold]Summary:[/bold] {new_count} new, {changed_count} changed,"
            f" {removed_count} removed"
        )

    # Create and populate the performance changes table
    if perf_rows:
        console.print()  # Add spacing
        perf_table = Table(title="Performance Changes (>30%)", show_lines=True)
        perf_table.add_column("Test", style="dim", no_wrap=False)
        perf_table.add_column("Time", justify="center")
        perf_table.add_column("Memory", justify="center")

        for row in perf_rows:
            perf_table.add_row(*row)

        console.print(perf_table)
        console.print(
            f"\n[bold]Performance:[/bold] {len(perf_rows)} tests with significant "
            f"changes (>{PERF_THRESHOLD_PERCENT * 100:.0f}%, min {PERF_MIN_TIME_DIFF_S}s/"
            f"{PERF_MIN_MEMORY_DIFF_MB}MB)"
        )

        print(
            f"Total duration changed: {before.summary.total_duration:.1f}s → {after.summary.total_duration:.1f}s",
        )
        print(
            f"Total memory changed: {before.summary.total_memory_mb:.1f}MB → {after.summary.total_memory_mb:.1f}MB",
        )


if __name__ == "__main__":
    typer.run(main)
