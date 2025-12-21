import sys


def test_collect_speed():
    """
    Find all python files in the project
    Run on each of them `pytest --collect-only -q --no-header`
    Measure the time it takes to collect the tests
    Print in rich table
    """
    import os
    import re
    import subprocess
    import time
    from pathlib import Path

    from rich.console import Console
    from rich.progress import Progress
    from rich.table import Table

    project_root = Path(__file__).parent.parent
    roots = [project_root / "src", project_root / "test"]
    python_files = []
    for root in roots:
        python_files.extend(list(root.rglob("*.py")))
    table = Table(title="Collect Speed")
    table.add_column("File", justify="left")
    table.add_column("Time", justify="right")

    max_workers = os.cpu_count() or 4
    pending = list(python_files)
    running = list[tuple[Path, subprocess.Popen]]()
    results = dict[Path, float]()

    def start_process(python_file: Path) -> subprocess.Popen:
        return subprocess.Popen(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "--no-header",
                str(python_file),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    with Progress() as progress:
        task = progress.add_task("Collecting tests...", total=len(python_files))

        while pending or running:
            # Start new processes up to max_workers
            while pending and len(running) < max_workers:
                python_file = pending.pop(0)
                running.append((python_file, start_process(python_file)))

            # Poll running processes
            still_running = list[tuple[Path, subprocess.Popen]]()
            for python_file, proc in running:
                if proc.poll() is not None:
                    stdout, _ = proc.communicate()
                    time_taken = re.search(r"tests collected in (\d+\.\d+)s", stdout)
                    progress.advance(task)
                    if time_taken is not None:
                        results[python_file] = float(time_taken.group(1))
                else:
                    still_running.append((python_file, proc))
            running = still_running

            if running:
                time.sleep(0.01)  # Avoid busy-waiting

    for python_file, time_taken in sorted(results.items(), key=lambda x: x[1]):
        table.add_row(python_file.name, f"{time_taken} seconds")
    console = Console()
    console.print(table)

    THRESHOLD = 20
    slow_tests = {
        python_file.name: time_taken
        for python_file, time_taken in results.items()
        if time_taken > THRESHOLD
    }

    assert not slow_tests, f"Slow tests: {slow_tests}"


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()
    typer.run(test_collect_speed)
