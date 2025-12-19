# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import random
import time
from collections import defaultdict
from contextlib import contextmanager
from enum import Enum, auto
from typing import Callable

from rich.table import Table

from faebryk.libs.logging import rich_to_string
from faebryk.libs.util import is_numeric_str


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
        self._units: dict[str, str] = {}

    @staticmethod
    def _select_unit(unit: str | None) -> str:
        if unit is None:
            return "ms"
        if unit not in {"s", "ms", "us"}:
            raise ValueError(f"Unsupported unit '{unit}', use one of: s, ms, us")
        return unit

    _UNIT_SCALE = {"s": 1.0, "ms": 1_000.0, "us": 1_000_000.0}

    def add(self, name: str, subcategory: str | None = None, unit: str | None = None):
        if subcategory is not None:
            name = f"{name}:{subcategory}"
        now = time.perf_counter()
        self._add(name, now - self.last_time, unit=unit)
        self.last_time = now

    def _add(self, name: str, val: float, unit: str | None = None):
        self.times[name].append(val)
        if unit is not None:
            self._units[name] = self._select_unit(unit)
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

    def _format_val(
        self,
        val: float,
        *,
        unit: str | None = None,
    ) -> tuple[str, str]:
        selected_unit = self._select_unit(unit)
        val_scaled = (val / self.cnt) * self._UNIT_SCALE[selected_unit]
        return f"{val_scaled:.3f}", selected_unit

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

    def get_formatted(
        self,
        name: str,
        strat: MultiSampleStrategy | None = None,
        unit: str | None = None,
    ):
        m, u = self._format_val(
            self.get(name, strat),
            unit=self._units.get(name, unit),
        )
        return f"{m}{u}"

    def __getitem__(self, name: str):
        return self.get(name)

    def to_str(self):
        return rich_to_string(self.to_table())

    def to_table(self):
        has_multisamples = any(len(vs) > 1 for vs in self.times.values())
        strats = self.strat.strats
        if not has_multisamples:
            strats = [Times.MultiSampleStrategy.AVG]

        table = Table(title="Timings" + (f" (cnt={self.cnt})" if self.cnt > 1 else ""))
        table.add_column("Category", style="cyan")
        if has_multisamples:
            table.add_column("Samples", justify="right")
        for strat in strats:
            c_name = strat.name if has_multisamples else "Value"
            table.add_column(
                c_name,
                justify="right",
                style="green",
            )
            table.add_column("Unit", style="yellow")

        rows = []
        raw_rows: list[
            list[float | None]
        ] = []  # same shape as rows; raw seconds for numeric cells
        seps = []
        for k, vs in self.times.items():
            if k.startswith("_separator"):
                seps.append(len(rows))
                continue
            if any(_k.startswith("_") for _k in k.split(":")):
                continue

            values = []
            raw_values: list[float | None] = []
            for strat in strats:
                v = self.get(k, strat)
                val_str, unit = self._format_val(
                    v,
                    unit=self._units.get(k),
                )
                values.append(val_str)
                raw_values.append(v / self.cnt)
                values.append(unit)
                raw_values.append(None)  # unit column is non-numeric

            categories = [k]
            samples = [str(len(vs))] if has_multisamples else []
            row = categories + samples + values
            rows.append(row)
            raw_rows.append([None] * len(categories + samples) + raw_values)

        # color gradient
        if not rows:
            return table

        for col_i in range(len(rows[0])):
            col_raw = [r[col_i] for r in raw_rows]
            col_display = [row[col_i] for row in rows]
            # numeric columns have raw seconds populated
            numeric_vals = [v for v in col_raw if isinstance(v, float)]
            if not numeric_vals:
                continue

            min_val = min(numeric_vals)
            max_val = max(numeric_vals)

            # Skip if all values are the same
            if min_val == max_val:
                continue

            # Apply color gradient based on quartiles
            # Calculate quartiles
            values_sorted = sorted(numeric_vals)
            q1_idx = int(len(values_sorted) * 0.25)
            q3_idx = int(len(values_sorted) * 0.75)

            q1 = values_sorted[q1_idx]
            q3 = values_sorted[q3_idx]

            for row_i, val in enumerate(col_raw):
                if val is None:
                    continue
                # Color based on quartiles: green for below Q1, yellow for Q1-Q3,
                # red for above Q3
                if val <= q1:
                    color = "green"
                elif val <= q3:
                    color = "yellow"
                else:
                    color = "red"

                # Apply rich formatting
                rows[row_i][col_i] = f"[{color}]{col_display[row_i]}[/{color}]"

        for i, row in enumerate(rows):
            if i in seps:
                table.add_section()
            table.add_row(*row)

        return table

    def __repr__(self):
        return self.to_str()

    def __rich_repr__(self):
        yield self.to_table()

    @contextmanager
    def context(self, name: str, unit: str | None = None):
        self.add("_" + name)
        start = time.perf_counter()
        try:
            yield
        finally:
            self._add(name, time.perf_counter() - start, unit=unit)

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
                else:
                    self.add(name)

    def make_group(self, group_name: str, include_filter: Callable[[str], bool]):
        group = [v for k, vs in self.times.items() if include_filter(k) for v in vs]
        if not group:
            return
        self.times[group_name] = group

    def add_seperator(self):
        self.times["_separator" + hex(random.randint(0, 100000))] = []
