# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import io
import time
from collections import defaultdict
from contextlib import contextmanager
from enum import Enum, auto

from rich.console import Console
from rich.table import Table

from faebryk.libs.units import P, Quantity, to_si


class Times:
    class MultiSampleStrategy(Enum):
        AVG = auto()
        ACC = auto()
        MIN = auto()
        MAX = auto()
        MED = auto()
        P80 = auto()
        # Multistrats
        AVG_ACC = auto()
        ALL = auto()

        @property
        def strats(self):
            if self == Times.MultiSampleStrategy.ALL:
                out = list(Times.MultiSampleStrategy)
                out.remove(Times.MultiSampleStrategy.ALL)
                out.remove(Times.MultiSampleStrategy.AVG_ACC)
                return out
            if self == Times.MultiSampleStrategy.AVG_ACC:
                return [Times.MultiSampleStrategy.AVG, Times.MultiSampleStrategy.ACC]
            return [self]

    def __init__(
        self,
        name: str | None = None,
        cnt: int = 1,
        multi_sample_strategy: MultiSampleStrategy = MultiSampleStrategy.ACC,
    ) -> None:
        self.times: dict[str, list[float]] = defaultdict(list)
        self.last_time = time.perf_counter()
        self.name = name

        self.cnt = cnt
        self.strat = multi_sample_strategy

    def add(self, name: str, subcategory: str | None = None):
        if subcategory is not None:
            name = f"{name}:{subcategory}"
        now = time.perf_counter()
        self._add(name, now - self.last_time)
        self.last_time = now

    def _add(self, name: str, val: float):
        self.times[name].append(val)
        if Times._in_measurement:
            if self is Times._in_measurement[0]:
                return
            index = (
                Times._in_measurement.index(self) - 1
                if self in Times._in_measurement
                else -1
            )
            self_name = self.name or hex(id(self))[:4]
            Times._in_measurement[index]._add(f"{self_name}:{name}", val)

    def _format_val(self, val: float):
        _val = (val / self.cnt) * P.s
        assert isinstance(_val, Quantity)
        return to_si(_val, "s", num_decimals=2)

    def get(self, name: str, strat: MultiSampleStrategy | None = None):
        if strat is None:
            strat = self.strat
        if strat == Times.MultiSampleStrategy.ALL:
            raise ValueError("Can't request all samples via get()")
        if strat == Times.MultiSampleStrategy.AVG_ACC:
            raise ValueError("Can't request avg_acc via get()")

        vs = self.times[name]
        match strat:
            case Times.MultiSampleStrategy.AVG:
                v = sum(vs) / len(vs)
            case Times.MultiSampleStrategy.ACC:
                v = sum(vs)
            case Times.MultiSampleStrategy.MIN:
                v = min(vs)
            case Times.MultiSampleStrategy.MAX:
                v = max(vs)
            case Times.MultiSampleStrategy.MED:
                v = sorted(vs)[len(vs) // 2]
            case Times.MultiSampleStrategy.P80:
                v = sorted(vs)[int(0.8 * len(vs))]
        return v

    def get_formatted(self, name: str, strat: MultiSampleStrategy | None = None):
        m, u = self._format_val(self.get(name, strat))
        return f"{m}{u}"

    def __getitem__(self, name: str):
        return self.get(name)

    def __repr__(self):
        has_multisamples = any(len(vs) > 1 for vs in self.times.values())

        strats = self.strat.strats
        if not has_multisamples:
            strats = [Times.MultiSampleStrategy.AVG]

        table = Table(title="Timings" + (f" (cnt={self.cnt})" if self.cnt > 1 else ""))
        table.add_column("Category", style="cyan")
        if has_multisamples:
            table.add_column("Samples", justify="right")
        for strat in strats:
            table.add_column(
                strat.name if has_multisamples else "Value",
                justify="right",
                style="green",
            )
            table.add_column("Unit", style="yellow")

        for k, vs in self.times.items():
            if k.startswith("_"):
                continue

            values = []
            for strat in strats:
                v = self.get(k, strat)
                value, unit = self._format_val(v)
                values.extend([value, unit])

            categories = [k]
            samples = [str(len(vs))] if has_multisamples else []
            table.add_row(*categories, *samples, *values)

        console = Console(record=True, file=io.StringIO())
        console.print(table)
        return console.export_text(styles=True)

    @contextmanager
    def context(self, name: str):
        self.add("_" + name)
        start = time.perf_counter()
        try:
            yield
        finally:
            self._add(name, time.perf_counter() - start)

    _in_measurement: list["Times"] = []

    @contextmanager
    def as_global(self, name: str | None = None, context: bool = False):
        Times._in_measurement.append(self)
        start = time.perf_counter()
        try:
            yield
        finally:
            Times._in_measurement.remove(self)
            if name is not None:
                if context:
                    self._add(name, time.perf_counter() - start)
                self.add(name)
