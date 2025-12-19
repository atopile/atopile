# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.zig.gen.graph.graph import (  # type: ignore[import-untyped]
    BFSPath,
    BoundEdge,
    BoundNode,
    GraphView,
)
from faebryk.core.zig.gen.graph.graph import (  # type: ignore[import-untyped]
    EdgeReference as Edge,
)
from faebryk.core.zig.gen.graph.graph import (  # type: ignore[import-untyped]
    NodeReference as Node,
)

logger = logging.getLogger(__name__)

__all__ = [
    "BFSPath",
    "BoundEdge",
    "BoundNode",
    "GraphView",
    "Node",
    "Edge",
]


def test_graph_garbage_collection(
    n: int = 10**5,
    trim: bool = True,
    trace_python_alloc: bool = False,
):
    import ctypes
    import gc
    import os
    import sys

    import psutil

    if trace_python_alloc:
        # Helps distinguish "RSS didn't drop" from "Python is still holding objects".
        # Note: this measures Python allocations, not Zig allocations.
        import tracemalloc

        tracemalloc.start()

    mem = psutil.Process().memory_info().rss

    def _get_mem_diff() -> int:
        nonlocal mem
        old_mem = mem
        mem = psutil.Process().memory_info().rss
        return mem - old_mem

    # pre measure memory
    g = GraphView.create()

    for _ in range(n):
        g.create_and_insert_node()

    mem_create = _get_mem_diff()

    g.destroy()

    mem_destroy = _get_mem_diff()

    # run gc

    gc.collect()

    mem_gc = _get_mem_diff()

    if trace_python_alloc:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        try:
            blocks = sys.getallocatedblocks()
        except AttributeError:
            blocks = None
        print("Py tracemalloc current: ", current / 1024 / 1024, "MB")
        print("Py tracemalloc peak: ", peak / 1024 / 1024, "MB")
        if blocks is not None:
            print("Py allocated blocks: ", blocks)

    # On glibc (common on Linux), freed memory is often kept in the process heap
    # and not returned to the OS immediately, which makes RSS-based "leak" tests
    # look worse than reality. `malloc_trim(0)` asks glibc to release free heap
    # pages back to the OS. This is a no-op on non-glibc allocators.
    mem_trim = 0
    try:
        if trim and os.name == "posix":
            libc = ctypes.CDLL(None)
            trimmer = getattr(libc, "malloc_trim", None)
            if trimmer is not None:
                trimmer.argtypes = [ctypes.c_size_t]
                trimmer.restype = ctypes.c_int
                trimmer(0)
                mem_trim = _get_mem_diff()
    except Exception as e:
        print("Failed to trim memory", e)
        pass

    mem_leaked = sum([mem_create, mem_destroy, mem_gc, mem_trim])

    print("N: ", n)
    print("Mem create: ", mem_create / 1024 / 1024, "MB")
    print("Mem destroy: ", mem_destroy / 1024 / 1024, "MB")
    print("Mem gc: ", mem_gc / 1024 / 1024, "MB")
    print("Mem trim: ", mem_trim / 1024 / 1024, "MB")
    print("Mem leaked: ", mem_leaked / 1024 / 1024, "MB")

    if trim:
        # This is RSS in *bytes*. After destroy+gc+trim we expect this to be small.
        assert mem_leaked < 2 * 1024 * 1024


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()
    typer.run(test_graph_garbage_collection)
