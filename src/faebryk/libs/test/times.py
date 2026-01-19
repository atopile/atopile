# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import random
import time
from collections import defaultdict
from contextlib import contextmanager
from enum import Enum, auto
from typing import Callable, Iterator

from rich.table import Table

from atopile.logging import rich_to_string


class Times:
    """
    Simple timing utility for measuring code blocks and presenting results.

    Supports:
    - Sequential timing with add()
    - Block timing with measure() context manager
    - Automatic nested measurements (Times created inside measure() auto-nest)
    - Multiple aggregation strategies (sum, avg, min, max, median, p80)
    - Rich table output

    Example:
        t = Times(name="build")
        t.add("setup", duration=0.5)

        with t.measure("compile"):
            do_compilation()

        # Automatic nesting - level2 auto-links to t
        with t.measure("tests"):
            level2 = Times(name="unit")
            level2.add("test1", duration=0.1)
            # t now has "unit:test1" automatically

        print(t.to_table())
    """

    # Class-level stack for automatic parent detection
    _active_stack: list[Times] = []

    class Strategy(Enum):
        """Aggregation strategy for multiple samples of the same measurement."""

        AVG = auto()  # Average of all samples
        SUM = auto()  # Sum of all samples (accumulate)
        MIN = auto()  # Minimum value
        MAX = auto()  # Maximum value
        MEDIAN = auto()  # Median value
        P80 = auto()  # 80th percentile

        # Multi-strategies (for display)
        AVG_SUM = auto()  # Show both AVG and SUM
        ALL = auto()  # Show all strategies

        @property
        def display_strats(self) -> list[Times.Strategy]:
            """Get the list of strategies to display for this strategy."""
            if self == Times.Strategy.ALL:
                return [
                    Times.Strategy.AVG,
                    Times.Strategy.SUM,
                    Times.Strategy.MIN,
                    Times.Strategy.MAX,
                    Times.Strategy.MEDIAN,
                    Times.Strategy.P80,
                ]
            if self == Times.Strategy.AVG_SUM:
                return [Times.Strategy.AVG, Times.Strategy.SUM]
            return [self]

    # Unit scaling factors
    _UNIT_SCALE = {"s": 1.0, "ms": 1_000.0, "us": 1_000_000.0}

    def __init__(
        self,
        name: str | None = None,
        strategy: Strategy = Strategy.SUM,
    ) -> None:
        """
        Create a new Times instance.

        If created inside a measure() context, automatically becomes a child
        of the active Times, propagating measurements upward.

        Args:
            name: Optional name for this timer (used in nested output)
            strategy: Default aggregation strategy for get() calls
        """
        self.name = name
        self.strategy = strategy
        self.times: dict[str, list[float]] = defaultdict(list)
        self._last_time = time.perf_counter()
        self._units: dict[str, str] = {}
        self._parent: Times | None = None

        # Auto-link to active parent if inside a measure() context
        if Times._active_stack:
            self._parent = Times._active_stack[-1]

    def add(
        self,
        name: str,
        *,
        duration: float | None = None,
        unit: str | None = None,
    ) -> None:
        """
        Add a timing measurement.

        If duration is None, measures time elapsed since the last add() call.
        If duration is provided, uses that value directly (in seconds).

        Args:
            name: Name of this measurement
            duration: Optional explicit duration in seconds
            unit: Optional unit for display (s, ms, us). Defaults to ms.
        """
        now = time.perf_counter()
        if duration is None:
            duration = now - self._last_time
        self._last_time = now

        self._record(name, duration, unit=unit)

    def _record(self, name: str, duration: float, unit: str | None = None) -> None:
        """Internal method to record a measurement and propagate to parent."""
        self.times[name].append(duration)

        if unit is not None:
            self._units[name] = self._validate_unit(unit)

        # Propagate to parent with prefixed name
        if self._parent is not None:
            prefix = self.name or hex(id(self))[-4:]
            self._parent._record(f"{prefix}:{name}", duration, unit=unit)

    @staticmethod
    def _validate_unit(unit: str | None) -> str:
        """Validate and return a unit string."""
        if unit is None:
            return "ms"
        if unit not in {"s", "ms", "us"}:
            raise ValueError(f"Unsupported unit '{unit}', use one of: s, ms, us")
        return unit

    @contextmanager
    def measure(self, name: str, unit: str | None = None) -> Iterator[None]:
        """
        Context manager to measure execution time of a code block.

        Any Times instances created inside this context will automatically
        become children and propagate their measurements to this Times.

        Args:
            name: Name of this measurement
            unit: Optional unit for display (s, ms, us)

        Example:
            with times.measure("compilation"):
                compile_project()

            # Automatic nesting
            with times.measure("tests"):
                inner = Times(name="unit")  # auto-links to times
                inner.add("test1", duration=0.1)
                # times now has "unit:test1"
        """
        # Record a hidden marker to reset the last_time
        self.add("_" + name)

        # Push self onto the active stack for auto-nesting
        Times._active_stack.append(self)
        start = time.perf_counter()
        try:
            yield
        finally:
            # Pop from stack
            Times._active_stack.pop()
            self._record(name, time.perf_counter() - start, unit=unit)

    def child(self, name: str) -> Times:
        """
        Explicitly create a child Times instance for nested measurements.

        Measurements in the child will automatically be recorded in this
        parent with a prefixed name (child_name:measurement_name).

        Note: If you create a Times inside a measure() context, it will
        auto-link. Use child() when you need explicit control.

        Args:
            name: Name for the child timer

        Returns:
            A new Times instance that reports to this parent
        """
        child = Times(name=name, strategy=self.strategy)
        # Override auto-detection to explicitly link to self
        child._parent = self
        return child

    def get(self, name: str, strategy: Strategy | None = None) -> float:
        """
        Get the aggregated timing value for a measurement.

        Args:
            name: Name of the measurement
            strategy: Aggregation strategy (defaults to instance strategy)

        Returns:
            Aggregated time value in seconds

        Raises:
            KeyError: If no measurement with this name exists
        """
        if strategy is None:
            strategy = self.strategy

        if strategy in (Times.Strategy.ALL, Times.Strategy.AVG_SUM):
            raise ValueError(
                f"Cannot use {strategy.name} with get(), use a specific strategy"
            )

        if name not in self.times:
            raise KeyError(f"No measurement named '{name}'")

        samples = self.times[name]

        match strategy:
            case Times.Strategy.AVG:
                return sum(samples) / len(samples)
            case Times.Strategy.SUM:
                return sum(samples)
            case Times.Strategy.MIN:
                return min(samples)
            case Times.Strategy.MAX:
                return max(samples)
            case Times.Strategy.MEDIAN:
                sorted_samples = sorted(samples)
                return sorted_samples[len(sorted_samples) // 2]
            case Times.Strategy.P80:
                sorted_samples = sorted(samples)
                return sorted_samples[int(0.8 * len(sorted_samples))]
            case _:
                raise ValueError(f"Unknown strategy: {strategy}")

    def __getitem__(self, name: str) -> float:
        """Shorthand for get(name)."""
        return self.get(name)

    def _format_value(self, value: float, unit: str | None = None) -> tuple[str, str]:
        """Format a value with its unit."""
        unit = self._validate_unit(unit)
        scaled = value * self._UNIT_SCALE[unit]
        return f"{scaled:.3f}", unit

    def get_formatted(
        self,
        name: str,
        strategy: Strategy | None = None,
        unit: str | None = None,
    ) -> str:
        """
        Get a formatted timing string.

        Args:
            name: Name of the measurement
            strategy: Aggregation strategy
            unit: Display unit (s, ms, us)

        Returns:
            Formatted string like "123.456ms"
        """
        value = self.get(name, strategy)
        val_str, unit_str = self._format_value(
            value, unit=self._units.get(name, unit)
        )
        return f"{val_str}{unit_str}"

    def separator(self) -> None:
        """Add a visual separator in the output table."""
        self.times["_separator" + hex(random.randint(0, 100000))] = []

    def group(self, name: str, filter_: str | Callable[[str], bool]) -> None:
        """
        Group measurements under a single name.

        Args:
            name: Name for the grouped measurement
            filter_: Either a string pattern (matches if key contains it)
                    or a predicate function
        """
        if isinstance(filter_, str):
            pattern = filter_
            filter_ = lambda k: pattern in k

        samples = [
            val
            for key, values in self.times.items()
            if filter_(key)
            for val in values
        ]

        if samples:
            self.times[name] = samples

    def to_table(self) -> Table:
        """
        Generate a rich Table with timing results.

        Returns:
            A rich Table object for display
        """
        has_multisamples = any(len(vs) > 1 for vs in self.times.values())
        strats = self.strategy.display_strats
        if not has_multisamples:
            strats = [Times.Strategy.AVG]

        table = Table(title="Timings")
        table.add_column("Category", style="cyan")
        if has_multisamples:
            table.add_column("Samples", justify="right")

        for strat in strats:
            col_name = strat.name if has_multisamples else "Value"
            table.add_column(col_name, justify="right", style="green")
            table.add_column("Unit", style="yellow")

        rows: list[list[str]] = []
        raw_rows: list[list[float | None]] = []
        separators: list[int] = []

        for key, values in self.times.items():
            if key.startswith("_separator"):
                separators.append(len(rows))
                continue
            if any(part.startswith("_") for part in key.split(":")):
                continue

            row_values: list[str] = []
            raw_values: list[float | None] = []

            for strat in strats:
                val = self.get(key, strat)
                val_str, unit = self._format_value(val, unit=self._units.get(key))
                row_values.append(val_str)
                raw_values.append(val)
                row_values.append(unit)
                raw_values.append(None)  # Unit column is non-numeric

            categories = [key]
            samples = [str(len(values))] if has_multisamples else []
            row = categories + samples + row_values
            rows.append(row)
            raw_rows.append([None] * len(categories + samples) + raw_values)

        if not rows:
            return table

        # Apply color gradient based on quartiles
        self._apply_color_gradient(rows, raw_rows)

        for i, row in enumerate(rows):
            if i in separators:
                table.add_section()
            table.add_row(*row)

        return table

    def _apply_color_gradient(
        self,
        rows: list[list[str]],
        raw_rows: list[list[float | None]],
    ) -> None:
        """Apply color gradient to numeric columns based on quartiles."""
        for col_idx in range(len(rows[0])):
            col_raw = [r[col_idx] for r in raw_rows]
            col_display = [row[col_idx] for row in rows]

            numeric_vals = [v for v in col_raw if isinstance(v, float)]
            if not numeric_vals:
                continue

            min_val = min(numeric_vals)
            max_val = max(numeric_vals)

            if min_val == max_val:
                continue

            sorted_vals = sorted(numeric_vals)
            q1 = sorted_vals[int(len(sorted_vals) * 0.25)]
            q3 = sorted_vals[int(len(sorted_vals) * 0.75)]

            for row_idx, val in enumerate(col_raw):
                if val is None:
                    continue

                if val <= q1:
                    color = "green"
                elif val <= q3:
                    color = "yellow"
                else:
                    color = "red"

                rows[row_idx][col_idx] = f"[{color}]{col_display[row_idx]}[/{color}]"

    def to_str(self) -> str:
        """
        Get a string representation of the timing table.

        Returns:
            String representation of the table
        """
        return rich_to_string(self.to_table())

    def __repr__(self) -> str:
        """String representation."""
        return self.to_str()

    def __rich_repr__(self):
        """Rich representation for rich.print()."""
        yield self.to_table()
