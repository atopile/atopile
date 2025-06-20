# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import io
import logging
from typing import Sequence

from more_itertools import partition
from rich.console import Console
from rich.table import Table

from faebryk.core.cpp import Counter, Path, set_indiv_measure, set_max_paths
from faebryk.core.cpp import find_paths as find_paths_cpp
from faebryk.core.node import Node
from faebryk.libs.util import ConfigFlag, ConfigFlagInt

logger = logging.getLogger(__name__)

PATHFINDER_LOG = ConfigFlag(
    "PATHFINDER_LOG", default=False, descr="Log filter counters (expensive)"
)

# Also in C++
INDIV_MEASURE = ConfigFlag(
    "INDIV_MEASURE", default=False, descr="Measure individual paths"
)
set_indiv_measure(bool(INDIV_MEASURE))


MAX_PATHS = ConfigFlagInt("MAX_PATHS", default=int(1e6), descr="Max paths to search")
MAX_PATHS_NO_NEW_WEAK = ConfigFlagInt(
    "MAX_PATHS_NO_NEW_WEAK", default=int(1e4), descr="Max paths with no new weak"
)
MAX_PATHS_NO_WEAK = ConfigFlagInt(
    "MAX_PATHS_NO_WEAK", default=int(1e5), descr="Max paths with no weak"
)
set_max_paths(int(MAX_PATHS), int(MAX_PATHS_NO_NEW_WEAK), int(MAX_PATHS_NO_WEAK))


def find_paths(src: Node, dst: Sequence[Node]) -> Sequence[Path]:
    paths, counters = find_paths_cpp(src, dst)

    if PATHFINDER_LOG:
        logger.debug(Counters(counters))
    return paths


class Counters:
    def __init__(self, counters: list[Counter]):
        self.counters: dict[str, Counter] = {c.name: c for c in counters}

    def __repr__(self):
        table = Table(title="Filter Counters")
        table.add_column("func", style="cyan", width=20)
        table.add_column("in", style="green", justify="right")
        table.add_column("weak in", style="green", justify="right")
        table.add_column("out", style="green", justify="right")
        # table.add_column("drop", style="cyan", justify="center")
        table.add_column("filt", style="magenta", justify="right")
        table.add_column("weaker", style="green", justify="right")
        table.add_column("stronger", style="green", justify="right")
        table.add_column("time", style="yellow", justify="right")
        table.add_column("time/in", style="yellow", justify="right")

        individual, total = partition(
            lambda x: x[1].total_counter, self.counters.items()
        )
        individual = list(individual)
        for section in partition(lambda x: x[1].multi, individual):
            for k, v in sorted(
                section,
                key=lambda x: (x[1].out_cnt, x[1].in_cnt),
                reverse=True,
            ):
                k_clean = (
                    k.split("path_")[-1]
                    .replace("_", " ")
                    .removeprefix("by ")
                    .removeprefix("with ")
                )
                if v.in_cnt == 0:
                    continue
                table.add_row(
                    k_clean,
                    str(v.in_cnt),
                    str(v.weak_in_cnt),
                    str(v.out_cnt),
                    # "x" if getattr(k, "discovery_filter", False) else "",
                    f"{(1 - v.out_cnt / v.in_cnt) * 100:.1f} %" if v.in_cnt else "-",
                    str(v.out_weaker),
                    str(v.out_stronger),
                    f"{v.time_spent_s * 1000:.2f} ms",
                    f"{v.time_spent_s / v.in_cnt * 1000 * 1000:.2f} us"
                    if v.in_cnt
                    else "-",
                )
            table.add_section()

        table.add_section()
        for k, v in total:
            if v.in_cnt == 0:
                continue
            table.add_row(
                k,
                str(v.in_cnt),
                str(v.weak_in_cnt),
                str(v.out_cnt),
                # "x" if getattr(k, "discovery_filter", False) else "",
                f"{(1 - v.out_cnt / v.in_cnt) * 100:.1f} %" if v.in_cnt else "-",
                str(v.out_weaker),
                str(v.out_stronger),
                f"{v.time_spent_s * 1000:.2f} ms",
                f"{v.time_spent_s / v.in_cnt * 1000 * 1000:.2f} us"
                if v.in_cnt
                else "-",
            )
        if INDIV_MEASURE:
            table.add_row(
                "Total",
                "",
                "",
                "",
                # "",
                "",
                "",
                "",
                f"{sum(v.time_spent_s for _, v in individual) * 1000:.2f} ms",
                f"{sum(v.time_spent_s / v.in_cnt for _, v in individual if v.in_cnt) * 1000 * 1000:.2f} us",  # noqa: E501
            )

        console = Console(record=True, width=120, file=io.StringIO())
        console.print(table)
        return console.export_text(styles=True)
