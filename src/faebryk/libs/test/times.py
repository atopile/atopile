# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import io
import time

from rich.console import Console
from rich.table import Table

from faebryk.libs.units import P


class Times:
    def __init__(self, cnt: int = 1, unit: str = "ms") -> None:
        self.times: dict[str, float] = {}
        self.last_time = time.perf_counter()

        self.unit = unit
        self.cnt = cnt

    def add(self, name: str):
        now = time.perf_counter()
        if name not in self.times:
            self.times[name] = now - self.last_time
        self.last_time = now

    def _format_val(self, val: float):
        return f"{((val / self.cnt)*P.s).to(self.unit).m:.2f}", self.unit

    def __repr__(self):
        table = Table(title="Timings")
        table.add_column("Category", style="cyan")
        table.add_column("Subcategory", style="magenta")
        table.add_column("Value", justify="right", style="green")
        table.add_column("Unit", style="yellow")

        for k, v in self.times.items():
            if not k.startswith("_"):
                value, unit = self._format_val(v)
                categories = k.split(":", 1)
                if len(categories) == 1:
                    categories.append("")
                table.add_row(categories[0].strip(), categories[1].strip(), value, unit)

        console = Console(record=True, file=io.StringIO())
        console.print(table)
        return console.export_text(styles=True)

    class Context:
        def __init__(self, name: str, times: "Times"):
            self.name = name
            self.times = times

        def __enter__(self):
            self.times.add("_" + self.name)
            self.start = time.perf_counter()

        def __exit__(self, exc_type, exc_value, traceback):
            self.times.times[self.name] = time.perf_counter() - self.start

    def context(self, name: str):
        return Times.Context(name, self)
