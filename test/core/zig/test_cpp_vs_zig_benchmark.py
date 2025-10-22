# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Performance comparison: C++ vs Zig pathfinder.

Tests two key scenarios:
1. Deep chains: N1 -> N2 -> N3 -> ... -> Nn (linear depth)
2. Wide nets: Central node connected to N nodes (star topology, 1 layer deep)

Measures both execution time and memory consumption.

MEMORY MEASUREMENT:
Uses resource.getrusage() ru_maxrss (maximum RSS) which is deterministic and
monotonically increasing. Memory is measured as the delta from baseline to peak.

Note: Since ru_maxrss is process-global and never decreases, when running both
C++ and Zig in the same process, the second measurement may show 0 MB if it doesn't
exceed the first implementation's peak. Time measurements are always accurate.

For isolated memory measurements, use:
  pytest test/core/zig/test_cpp_vs_zig_benchmark.py --only-cpp -v -s -n0
  pytest test/core/zig/test_cpp_vs_zig_benchmark.py --only-zig -v -s -n0
"""

import gc
import subprocess
import sys
import time
from pathlib import Path

import pytest

from faebryk.core import cpp
from faebryk.core.moduleinterface import ModuleInterface as RealMIF
from faebryk.core.pathfinder import find_paths as find_paths_cpp
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.graph.graph import GraphView, Node


def timer(func, iterations=1):
    """Time a function call."""
    total_time = 0
    result = None
    for _ in range(iterations):
        start = time.perf_counter()
        result = func()
        total_time += time.perf_counter() - start
    return total_time / iterations, result


def measure_memory_subprocess(impl_type, size_param):
    """
    Measure memory in isolated subprocess for accurate measurement.

    Args:
        impl_type: 'cpp_chain', 'zig_chain', 'cpp_star', or 'zig_star'
        size_param: chain_length or num_leaves

    Returns: (memory_mb, path_count)
    """
    # Create a temporary script to run in subprocess
    script = f"""
import gc
import resource
import sys

# Setup path to import from workspace
sys.path.insert(0, '{Path(__file__).parent.parent.parent.parent}')

from faebryk.core import cpp
from faebryk.core.moduleinterface import ModuleInterface as RealMIF
from faebryk.core.pathfinder import find_paths as find_paths_cpp
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.graph.graph import GraphView, Node

# Reproduce the helper classes
class CppModuleInterface(cpp.Node):
    def __init__(self):
        super().__init__()
        cpp.Node.transfer_ownership(self)
        self.connected = cpp.GraphInterfaceModuleConnection()
        self.connected.node = self
        self.connected.connect(self.self_gif, cpp.LinkSibling())

CppModuleInterface.__name__ = "ModuleInterface"
CppModuleInterface.__qualname__ = "ModuleInterface"
CppModuleInterface.__module__ = "faebryk.core.moduleinterface"
CppModuleInterface._mro_ids = {{id(RealMIF), id(CppModuleInterface)}}

def build_cpp_chain(length):
    nodes = [CppModuleInterface() for _ in range(length)]
    for i in range(length - 1):
        nodes[i].connected.connect(nodes[i + 1].connected, cpp.LinkDirect())
    return nodes

def build_zig_chain(length):
    g = GraphView.create()
    nodes = [g.insert_node(node=Node.create()) for _ in range(length)]
    for i in range(length - 1):
        EdgeInterfaceConnection.connect(bn1=nodes[i], bn2=nodes[i + 1])
    return g, nodes

def build_cpp_star(num_leaves):
    center = CppModuleInterface()
    leaves = [CppModuleInterface() for _ in range(num_leaves)]
    for leaf in leaves:
        center.connected.connect(leaf.connected, cpp.LinkDirect())
    return center, leaves

def build_zig_star(num_leaves):
    g = GraphView.create()
    center = g.insert_node(node=Node.create())
    leaves = [g.insert_node(node=Node.create()) for _ in range(num_leaves)]
    for leaf in leaves:
        EdgeInterfaceConnection.connect(bn1=center, bn2=leaf)
    return g, center, leaves

# Clean up and get baseline
gc.collect()
baseline_maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

# Run the benchmark
impl_type = "{impl_type}"
size = {size_param}

if impl_type == "cpp_chain":
    nodes = build_cpp_chain(size)
    paths = find_paths_cpp(nodes[0], [nodes[-1]])
elif impl_type == "zig_chain":
    g, nodes = build_zig_chain(size)
    paths = EdgeInterfaceConnection.get_connected(source=nodes[0])
elif impl_type == "cpp_star":
    center, leaves = build_cpp_star(size)
    paths = find_paths_cpp(center, leaves)
elif impl_type == "zig_star":
    g, center, leaves = build_zig_star(size)
    paths = EdgeInterfaceConnection.get_connected(source=center)

# Get peak
peak_maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

# Calculate increase
if sys.platform == 'darwin':
    increase_mb = (peak_maxrss - baseline_maxrss) / 1024 / 1024
else:
    increase_mb = (peak_maxrss - baseline_maxrss) / 1024

print(f"{{increase_mb:.2f}},{{len(paths)}}")
"""

    # Run in subprocess
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=300
    )

    if result.returncode != 0:
        raise RuntimeError(f"Subprocess failed: {result.stderr}")

    # Parse output
    mem_mb, path_count = result.stdout.strip().split(",")
    return float(mem_mb), int(path_count)


# ============================================================================
# C++ Graph Construction
# ============================================================================


class CppModuleInterface(cpp.Node):
    """
    ModuleInterface with C++ backing for benchmarking.

    Recreates the old architecture where ModuleInterface inherited from cpp.Node.
    Includes proper graph interface linking for pathfinding.
    """

    def __init__(self):
        super().__init__()
        cpp.Node.transfer_ownership(self)

        # Create the "connected" GraphInterface for inter-node connections
        self.connected = cpp.GraphInterfaceModuleConnection()
        self.connected.node = self

        # Link self_gif to connected so pathfinding can traverse through it
        # (pathfinding starts from self_gif, needs to reach connected interface)
        self.connected.connect(self.self_gif, cpp.LinkSibling())


# Register our class as "ModuleInterface" for C++ type checking
CppModuleInterface.__name__ = "ModuleInterface"
CppModuleInterface.__qualname__ = "ModuleInterface"
CppModuleInterface.__module__ = "faebryk.core.moduleinterface"
CppModuleInterface._mro_ids = {id(RealMIF), id(CppModuleInterface)}


def build_cpp_chain(length: int):
    """Build a linear chain using C++ backend: N1 -> N2 -> ... -> Nn"""
    nodes = [CppModuleInterface() for _ in range(length)]
    for i in range(length - 1):
        nodes[i].connected.connect(nodes[i + 1].connected, cpp.LinkDirect())
    return nodes


def build_cpp_star(num_leaves: int):
    """Build a star/hub topology: Center connected to N leaf nodes (1 layer deep)"""
    center = CppModuleInterface()
    leaves = [CppModuleInterface() for _ in range(num_leaves)]
    for leaf in leaves:
        center.connected.connect(leaf.connected, cpp.LinkDirect())
    return center, leaves


# ============================================================================
# Zig Graph Construction
# ============================================================================


def build_zig_chain(length: int):
    """Build a linear chain using Zig backend: N1 -> N2 -> ... -> Nn"""
    g = GraphView.create()
    nodes = [g.insert_node(node=Node.create()) for _ in range(length)]
    for i in range(length - 1):
        EdgeInterfaceConnection.connect(bn1=nodes[i], bn2=nodes[i + 1])
    return g, nodes


def build_zig_star(num_leaves: int):
    """Build a star/hub topology: Center connected to N leaf nodes (1 layer deep)"""
    g = GraphView.create()
    center = g.insert_node(node=Node.create())
    leaves = [g.insert_node(node=Node.create()) for _ in range(num_leaves)]
    for leaf in leaves:
        EdgeInterfaceConnection.connect(bn1=center, bn2=leaf)
    return g, center, leaves


# ============================================================================
# Common Benchmark Runner
# ============================================================================


def show_winner(cpp_val, zig_val):
    """Show which implementation wins and by how much."""
    if cpp_val == 0 and zig_val == 0:
        return "Tie"
    elif cpp_val == 0:
        return "Zig (∞x)"
    elif zig_val == 0:
        return "C++ (∞x)"
    elif cpp_val < zig_val:
        speedup = zig_val / cpp_val
        return f"C++ ({speedup:.2f}x)"
    else:
        speedup = cpp_val / zig_val
        return f"Zig ({speedup:.2f}x)"


def run_benchmark(
    request,
    test_name: str,
    size_desc: str,
    size_param: int,
    topology: str,  # 'chain' or 'star'
    cpp_build_and_query,
    zig_build_and_query,
    cpp_build_func,
    zig_build_func,
    cpp_query_func,
    zig_query_func,
):
    """
    Generic benchmark runner for C++ vs Zig comparison.

    Args:
        test_name: Name of the test (e.g., "DEEP CHAIN", "WIDE NET")
        size_desc: Size description (e.g., "deep chain, 1000 nodes")
        size_param: Numeric size parameter
        topology: 'chain' or 'star'
        (other args same as before)
    """
    only_cpp = request.config.getoption("--only-cpp")
    only_zig = request.config.getoption("--only-zig")

    run_cpp = not only_zig
    run_zig = not only_cpp

    print(f"\n{'=' * 70}")
    print(f"{test_name}: {size_desc}")
    print(f"{'=' * 70}")

    cpp_build_time = cpp_time = cpp_mem = cpp_paths = cpp_graph_data = None
    if run_cpp:
        print("\n  === C++ Implementation ===")

        # Measure memory in isolated subprocess
        cpp_mem, cpp_path_count = measure_memory_subprocess(
            f"cpp_{topology}", size_param
        )

        # Measure time and verify path count in-process
        _, (cpp_graph_data, cpp_paths) = timer(cpp_build_and_query)
        cpp_build_time, _ = timer(cpp_build_func)
        cpp_time, _ = timer(cpp_query_func, iterations=3)

        assert len(cpp_paths) == cpp_path_count, (
            f"Path count mismatch: {len(cpp_paths)} vs {cpp_path_count}"
        )

        print(f"  Build time: {cpp_build_time * 1000:.2f} ms")
        print(f"  Query time: {cpp_time * 1000:.3f} ms")
        print(f"  Memory: {cpp_mem:.2f} MB")
        print(f"    Paths found: {len(cpp_paths)}")
        if len(cpp_paths) > 0:
            path_lengths = [len(p) for p in cpp_paths]
            print(f"    Path lengths: min={min(path_lengths)}, max={max(path_lengths)}")

        # Clean up completely before Zig
        del cpp_graph_data, cpp_paths
        gc.collect()

    zig_build_time = zig_time = zig_mem = zig_paths = zig_graph_data = None
    if run_zig:
        print("\n  === Zig Implementation ===")

        # Measure memory in isolated subprocess
        zig_mem, zig_path_count = measure_memory_subprocess(
            f"zig_{topology}", size_param
        )

        # Measure time and verify path count in-process
        _, (zig_graph_data, zig_paths) = timer(zig_build_and_query)
        zig_build_time, _ = timer(zig_build_func)
        zig_time, _ = timer(zig_query_func, iterations=3)

        assert len(zig_paths) == zig_path_count, (
            f"Path count mismatch: {len(zig_paths)} vs {zig_path_count}"
        )

        print(f"  Build time: {zig_build_time * 1000:.2f} ms")
        print(f"  Query time: {zig_time * 1000:.3f} ms")
        print(f"  Memory: {zig_mem:.2f} MB")
        print(f"    Paths found: {len(zig_paths)}")
        if len(zig_paths) > 0:
            print(f"    Path lengths: min={min(zig_paths)}, max={max(zig_paths)}")

    # --- Summary ---
    print(f"\n{'=' * 70}")
    print(f"Summary ({size_desc}):")
    print(f"{'=' * 70}")

    if run_cpp and run_zig:
        print(f"{'Metric':<25} {'C++':<15} {'Zig':<15} {'Winner':<15}")
        print(f"{'-' * 70}")
        print(
            f"{'Build (ms)':<25} {cpp_build_time * 1000:<15.3f} "
            f"{zig_build_time * 1000:<15.3f} "
            f"{show_winner(cpp_build_time, zig_build_time):<15}"
        )
        print(
            f"{'Find all paths (ms)':<25} {cpp_time * 1000:<15.3f} "
            f"{zig_time * 1000:<15.3f} "
            f"{show_winner(cpp_time, zig_time):<15}"
        )
        print(
            f"{'Memory (MB)':<25} {cpp_mem:<15.2f} "
            f"{zig_mem:<15.2f} "
            f"{show_winner(cpp_mem, zig_mem):<15}"
        )
    else:
        print(f"{'Metric':<25} {'Value':<15}")
        print(f"{'-' * 70}")
        if run_cpp:
            print(f"{'Build (ms)':<25} {cpp_build_time * 1000:<15.3f}")
            print(f"{'Find all paths (ms)':<25} {cpp_time * 1000:<15.3f}")
            print(f"{'Memory (MB)':<25} {cpp_mem:<15.2f}")
        else:
            print(f"{'Build (ms)':<25} {zig_build_time * 1000:<15.3f}")
            print(f"{'Find all paths (ms)':<25} {zig_time * 1000:<15.3f}")
            print(f"{'Memory (MB)':<25} {zig_mem:<15.2f}")

    print(f"{'=' * 70}\n")


# ============================================================================
# Test 1: Deep Chains
# ============================================================================


@pytest.mark.parametrize("chain_length", [10, 100, 1000, 10000])
def test_deep_chain(request, chain_length: int):
    """
    Scenario: Long linear chain N1 -> N2 -> N3 -> ... -> Nn
    Operation: Find all paths (full BFS exploration)

    This tests pathfinder performance on graphs with high depth.
    """
    # Build closures that capture chain_length
    cpp_nodes = [None]
    zig_data = [None, None]

    def cpp_build_and_query():
        nodes = build_cpp_chain(chain_length)
        paths = find_paths_cpp(nodes[0], [nodes[-1]])
        cpp_nodes[0] = nodes
        return nodes, paths

    def zig_build_and_query():
        g, nodes = build_zig_chain(chain_length)
        paths = EdgeInterfaceConnection.get_connected(source=nodes[0])
        zig_data[0], zig_data[1] = g, nodes
        return (g, nodes), paths

    run_benchmark(
        request,
        "DEEP CHAIN",
        f"deep chain, {chain_length} nodes",
        chain_length,
        "chain",
        cpp_build_and_query,
        zig_build_and_query,
        lambda: build_cpp_chain(chain_length),
        lambda: build_zig_chain(chain_length),
        lambda: find_paths_cpp(cpp_nodes[0][0], [cpp_nodes[0][-1]]),
        lambda: EdgeInterfaceConnection.get_connected(source=zig_data[1][0]),
    )


# ============================================================================
# Test 2: Wide Nets (Star Topology)
# ============================================================================


@pytest.mark.parametrize("num_leaves", [10, 100, 1000, 10000])
def test_wide_net(request, num_leaves: int):
    """
    Scenario: Star topology - one center node connected to N leaf nodes (1 layer deep)
    Operation: Find all paths (full BFS exploration)

    This tests pathfinder performance on graphs with high width but shallow depth.
    Simulates scenarios like a power rail connected to many components.
    """
    # Build closures that capture num_leaves
    cpp_graph = [None, None]
    zig_data = [None, None, None]

    def cpp_build_and_query():
        center, leaves = build_cpp_star(num_leaves)
        paths = find_paths_cpp(center, leaves)
        cpp_graph[0], cpp_graph[1] = center, leaves
        return (center, leaves), paths

    def zig_build_and_query():
        g, center, leaves = build_zig_star(num_leaves)
        paths = EdgeInterfaceConnection.get_connected(source=center)
        zig_data[0], zig_data[1], zig_data[2] = g, center, leaves
        return (g, center, leaves), paths

    run_benchmark(
        request,
        "WIDE NET",
        f"wide net, {num_leaves} leaves",
        num_leaves,
        "star",
        cpp_build_and_query,
        zig_build_and_query,
        lambda: build_cpp_star(num_leaves),
        lambda: build_zig_star(num_leaves),
        lambda: find_paths_cpp(cpp_graph[0], cpp_graph[1]),
        lambda: EdgeInterfaceConnection.get_connected(source=zig_data[1]),
    )


if __name__ == "__main__":
    # Quick test run
    import sys

    class FakeRequest:
        class FakeConfig:
            def getoption(self, opt):
                return False

        config = FakeConfig()

    req = FakeRequest()
    print("\n=== Deep Chain Test ===")
    test_deep_chain(req, 100)

    print("\n=== Wide Net Test ===")
    test_wide_net(req, 100)
