import tempfile
from pathlib import Path
from textwrap import dedent

import psutil
import pytest
from rich.console import Console
from rich.table import Table

import faebryk.library._F as F
from atopile import config
from atopile.build_steps import muster
from atopile.datatypes import TypeRef
from atopile.front_end import Bob
from atopile.parse import parse_text_as_file
from faebryk.core.solver.nullsolver import NullSolver
from faebryk.libs.kicad.fileformats import kicad
from faebryk.libs.library import L
from faebryk.libs.util import cast_assert


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.slow
def test_memory_usage():
    """
    python ./tools/profile.py memray -- $(which pytest) -o addopts='' -s
    --log-cli-level=INFO -k test_memory_usage
    """
    bob = Bob()
    layout_path = Path(tempfile.mkdtemp()) / "layout.kicad_pcb"
    pcb_file = kicad.pcb.PcbFile(
        kicad_pcb=kicad.pcb.KicadPcb(
            version=0,
            generator="faebryk",
            generator_version="latest",
        )  # type: ignore
    )
    kicad.dumps(pcb_file, layout_path)
    # bullshit config setup
    gcfg = config.config
    ctx = gcfg.select_build("default")
    ctx.__enter__()

    mem_measurement = {}

    def measure_memory(name: str, before: int) -> int:
        mem_new = psutil.Process().memory_info().rss
        mem_gain = mem_new - before
        print(f"{name}: {mem_gain / 1024 / 1024:.2f} MB")
        mem_measurement[name] = mem_gain
        return mem_new

    # solver = DefaultSolver()
    solver = NullSolver()
    mem = psutil.Process().memory_info().rss

    COUNT = 1000

    text = dedent(
        f"""
        import Resistor

        module App:
            r = new Resistor[{COUNT}]
        """
    )

    tree = parse_text_as_file(text)
    mem = measure_memory("Parse", mem)

    node = cast_assert(L.Module, bob.build_ast(tree, TypeRef(["App"])))
    mem = measure_memory("AST", mem)

    pcb = F.PCB(layout_path)
    for target in muster.select({"default"}):
        target(node, solver, pcb)
        mem = measure_memory(f"Build {target.name}", mem)

    # Create a rich table for memory usage display
    console = Console()
    table = Table(title="Memory Usage by Build Step")

    table.add_column("Build Step", style="cyan", no_wrap=True)
    table.add_column("Memory (MB)", justify="right", style="green")
    table.add_column("% of Total", justify="right", style="yellow")

    total_memory = sum(mem_measurement.values())

    for step_name, memory_bytes in mem_measurement.items():
        memory_mb = memory_bytes / 1024 / 1024
        percentage = (memory_bytes / total_memory * 100) if total_memory > 0 else 0

        table.add_row(step_name, f"{memory_mb:.2f}", f"{percentage:.1f}%")

    # Add total row
    total_mb = total_memory / 1024 / 1024
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_mb:.2f}[/bold]",
        "[bold]100.0%[/bold]",
        style="bold",
    )

    console.print(table)

    for k, v in mem_measurement.items():
        assert v < 500 * 1024 * 1024, f"{k} used {v / 1024 / 1024:.2f} MB"
