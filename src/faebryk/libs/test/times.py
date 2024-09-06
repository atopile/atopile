# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import time
from textwrap import indent


class Times:
    def __init__(self) -> None:
        self.times = {}
        self.last_time = time.time()

    def add(self, name: str):
        now = time.time()
        if name not in self.times:
            self.times[name] = now - self.last_time
        self.last_time = now

    def _format_val(self, val: float):
        return f"{val * 1000:.2f}ms"

    def __repr__(self):
        formatted = {
            k: self._format_val(v)
            for k, v in self.times.items()
            if not k.startswith("_")
        }
        longest_name = max(len(k) for k in formatted)
        return "Timings: \n" + indent(
            "\n".join(f"{k:>{longest_name}}: {v:<10}" for k, v in formatted.items()),
            " " * 4,
        )

    class Context:
        def __init__(self, name: str, times: "Times"):
            self.name = name
            self.times = times

        def __enter__(self):
            self.times.add("_" + self.name)
            self.start = time.time()

        def __exit__(self, exc_type, exc_value, traceback):
            self.times.times[self.name] = time.time() - self.start

    def context(self, name: str):
        return Times.Context(name, self)
