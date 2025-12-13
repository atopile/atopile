import sys
from pathlib import Path

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

# TODO just integrate this into the html


def style_outcome(outcome: str) -> str:
    style = OUTCOME_STYLES.get(outcome, "white")
    return f"[{style}]{outcome}[/{style}]"


def main(before_report: Path):
    before = Report.from_json(before_report.read_text())
    after = Report.from_json(NEW_REPORT.read_text())

    before_tests = {t.fullnodeid: t for t in before.tests}
    after_tests = {t.fullnodeid: t for t in after.tests}

    console = Console()

    # Build rows for the table
    rows: list[tuple[str, str, str, str]] = []

    # New tests (in after but not in before)
    for k in after_tests:
        if k not in before_tests:
            t = after_tests[k]
            rows.append(
                (t.fullnodeid, "[cyan]NEW[/cyan]", "-", style_outcome(t.outcome))
            )

        # Changed tests (outcome changed)
        elif before_tests[k].outcome != after_tests[k].outcome:
            rows.append(
                (
                    k,
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
                    t.fullnodeid,
                    "[magenta]REMOVED[/magenta]",
                    style_outcome(t.outcome),
                    "-",
                )
            )

    if not rows:
        console.print("[green]No test changes detected.[/green]")
        return

    # Create and populate the table
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


if __name__ == "__main__":
    typer.run(main)
