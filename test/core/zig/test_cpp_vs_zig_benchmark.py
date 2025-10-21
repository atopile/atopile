# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Performance comparison: C++ vs Zig pathfinder.

Tests two key scenarios:
1. Deep chains: N1 -> N2 -> N3 -> ... -> Nn (linear depth)
2. Wide nets: Central node connected to N nodes (star topology, 1 layer deep)

Measures both execution time and memory consumption.
"""

import gc
import threading
import time

import psutil
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


def measure_memory_and_time(func, iterations=1):
    """
    Measure execution time and PEAK memory consumption during operation.
    
    Samples memory immediately before and after each iteration to catch
    peak allocation. Important for Zig which allocates and frees memory
    within the operation.
    
    Returns: (avg_time, peak_memory_mb, result)
    """
    process = psutil.Process()
    
    # Force garbage collection before measurement
    gc.collect()
    
    # Measure baseline memory (RSS)
    baseline_mem = process.memory_info().rss / 1024 / 1024  # MB
    
    total_time = 0
    peak_mem = baseline_mem
    result = None
    
    # Run the operation
    for _ in range(iterations):
        start = time.perf_counter()
        result = func()
        elapsed = time.perf_counter() - start
        total_time += elapsed
        
        # Sample memory IMMEDIATELY after operation (before any cleanup)
        # This catches Zig's peak before the wrapper frees memory
        current = process.memory_info().rss / 1024 / 1024
        peak_mem = max(peak_mem, current)
    
    # Peak memory consumed = peak - baseline
    mem_consumed = peak_mem - baseline_mem
    
    return total_time / iterations, mem_consumed, result


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
# Test 1: Deep Chains
# ============================================================================


@pytest.mark.parametrize("chain_length", [10, 100, 1000])
def test_deep_chain(request, chain_length: int):
    """
    Scenario: Long linear chain N1 -> N2 -> N3 -> ... -> Nn
    Operation: Find all paths (full BFS exploration)
    
    This tests pathfinder performance on graphs with high depth.
    """
    only_cpp = request.config.getoption("--only-cpp")
    only_zig = request.config.getoption("--only-zig")
    
    run_cpp = not only_zig
    run_zig = not only_cpp
    
    print(f"\n{'=' * 70}")
    print(f"DEEP CHAIN: {chain_length} nodes in linear chain")
    print(f"{'=' * 70}")

    # --- Build graphs ---
    print(f"\nBuilding chains...")

    # Measure memory from before build for both (fair comparison)
    gc.collect()
    mem_baseline = psutil.Process().memory_info().rss / 1024 / 1024

    cpp_build_time = cpp_nodes = None
    if run_cpp:
        cpp_build_time, cpp_nodes = timer(lambda: build_cpp_chain(chain_length))
        print(f"  C++ build: {cpp_build_time * 1000:.2f} ms")

    zig_mem_baseline = mem_baseline
    zig_build_time = zig_g = zig_nodes = None
    if run_zig:
        zig_build_time, (zig_g, zig_nodes) = timer(lambda: build_zig_chain(chain_length))
        print(f"  Zig build: {zig_build_time * 1000:.2f} ms")

    # --- Find all paths (full exploration) ---
    print(f"\nFinding all paths (full BFS)...")

    cpp_time = cpp_mem = cpp_paths = None
    if run_cpp:
        # Measure time  
        cpp_time, cpp_paths = timer(
            lambda: find_paths_cpp(cpp_nodes[0], [cpp_nodes[-1]]), 
            iterations=1
        )
        
        # Measure total memory from baseline (same as Zig)
        mem_peak = psutil.Process().memory_info().rss / 1024 / 1024
        cpp_mem = mem_peak - mem_baseline
        
        print(f"  C++ time: {cpp_time * 1000:.3f} ms")
        print(f"  C++ memory (total peak): {cpp_mem:.2f} MB")
        print(f"    Paths found: {len(cpp_paths)}")
        if len(cpp_paths) > 0:
            path_lengths = [len(p) for p in cpp_paths]
            print(f"    Path lengths: min={min(path_lengths)}, max={max(path_lengths)}")

    zig_time = zig_mem = zig_paths = None
    if run_zig:
        # Measure time (single iteration, no warmup to catch peak)
        zig_time, zig_paths = timer(
            lambda: EdgeInterfaceConnection.get_connected(source=zig_nodes[0]),
            iterations=1
        )
        
        # Measure total memory from baseline (includes graph + query peak)
        mem_peak = psutil.Process().memory_info().rss / 1024 / 1024
        zig_mem = mem_peak - zig_mem_baseline
        
        print(f"  Zig time: {zig_time * 1000:.3f} ms")
        print(f"  Zig memory (total peak): {zig_mem:.2f} MB")
        print(f"    Paths found: {len(zig_paths)}")
        if len(zig_paths) > 0:
            print(f"    Path lengths: min={min(zig_paths)}, max={max(zig_paths)}")

    # --- Summary ---
    print(f"\n{'=' * 70}")
    print(f"Summary (deep chain, {chain_length} nodes):")
    print(f"{'=' * 70}")
    
    if run_cpp and run_zig:
        print(f"{'Metric':<25} {'C++':<15} {'Zig':<15} {'Winner':<15}")
        print(f"{'-' * 70}")
        
        def show_winner(cpp_val, zig_val):
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
        
        print(f"{'Build (ms)':<25} {cpp_build_time * 1000:<15.3f} {zig_build_time * 1000:<15.3f} {show_winner(cpp_build_time, zig_build_time):<15}")
        print(f"{'Find all paths (ms)':<25} {cpp_time * 1000:<15.3f} {zig_time * 1000:<15.3f} {show_winner(cpp_time, zig_time):<15}")
        print(f"{'Memory (MB)':<25} {cpp_mem:<15.2f} {zig_mem:<15.2f} {show_winner(cpp_mem, zig_mem):<15}")
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
# Test 2: Wide Nets (Star Topology)
# ============================================================================


@pytest.mark.parametrize("num_leaves", [10, 100, 1000])
def test_wide_net(request, num_leaves: int):
    """
    Scenario: Star topology - one center node connected to N leaf nodes (1 layer deep)
    Operation: Find all paths (full BFS exploration)
    
    This tests pathfinder performance on graphs with high width but shallow depth.
    Simulates scenarios like a power rail connected to many components.
    """
    only_cpp = request.config.getoption("--only-cpp")
    only_zig = request.config.getoption("--only-zig")
    
    run_cpp = not only_zig
    run_zig = not only_cpp
    
    print(f"\n{'=' * 70}")
    print(f"WIDE NET: 1 center + {num_leaves} leaves (star topology)")
    print(f"{'=' * 70}")

    # --- Build graphs ---
    print(f"\nBuilding star topology...")
    
    # Measure memory from before build for both (fair comparison)
    gc.collect()
    mem_baseline = psutil.Process().memory_info().rss / 1024 / 1024
    
    cpp_build_time = cpp_center = cpp_leaves = None
    if run_cpp:
        cpp_build_time, (cpp_center, cpp_leaves) = timer(lambda: build_cpp_star(num_leaves))
        print(f"  C++ build: {cpp_build_time * 1000:.2f} ms")

    zig_mem_baseline = mem_baseline
    zig_build_time = zig_g = zig_center = zig_leaves = None
    if run_zig:
        zig_build_time, (zig_g, zig_center, zig_leaves) = timer(lambda: build_zig_star(num_leaves))
        print(f"  Zig build: {zig_build_time * 1000:.2f} ms")

    # --- Find all paths from center ---
    print(f"\nFinding all paths from center (full BFS)...")

    cpp_time = cpp_mem = cpp_paths = None
    if run_cpp:
        # Measure time
        cpp_time, cpp_paths = timer(
            lambda: find_paths_cpp(cpp_center, cpp_leaves), 
            iterations=1
        )
        
        # Measure total memory from baseline (same as Zig)
        mem_peak = psutil.Process().memory_info().rss / 1024 / 1024
        cpp_mem = mem_peak - mem_baseline
        
        print(f"  C++ time: {cpp_time * 1000:.3f} ms")
        print(f"  C++ memory (total peak): {cpp_mem:.2f} MB")
        print(f"    Paths found: {len(cpp_paths)}")
        if len(cpp_paths) > 0:
            path_lengths = [len(p) for p in cpp_paths]
            print(f"    Path lengths: min={min(path_lengths)}, max={max(path_lengths)}")

    zig_time = zig_mem = zig_paths = None
    if run_zig:
        # Measure time (single iteration, no warmup to catch peak)
        zig_time, zig_paths = timer(
            lambda: EdgeInterfaceConnection.get_connected(source=zig_center),
            iterations=1
        )
        
        # Measure total memory from baseline (includes graph + query peak)
        mem_peak = psutil.Process().memory_info().rss / 1024 / 1024
        zig_mem = mem_peak - zig_mem_baseline
        
        print(f"  Zig time: {zig_time * 1000:.3f} ms")
        print(f"  Zig memory (total peak): {zig_mem:.2f} MB")
        print(f"    Paths found: {len(zig_paths)}")
        if len(zig_paths) > 0:
            print(f"    Path lengths: min={min(zig_paths)}, max={max(zig_paths)}")

    # --- Summary ---
    print(f"\n{'=' * 70}")
    print(f"Summary (wide net, {num_leaves} leaves):")
    print(f"{'=' * 70}")
    
    if run_cpp and run_zig:
        print(f"{'Metric':<25} {'C++':<15} {'Zig':<15} {'Winner':<15}")
        print(f"{'-' * 70}")
        
        def show_winner(cpp_val, zig_val):
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
        
        print(f"{'Build (ms)':<25} {cpp_build_time * 1000:<15.3f} {zig_build_time * 1000:<15.3f} {show_winner(cpp_build_time, zig_build_time):<15}")
        print(f"{'Find all paths (ms)':<25} {cpp_time * 1000:<15.3f} {zig_time * 1000:<15.3f} {show_winner(cpp_time, zig_time):<15}")
        print(f"{'Memory (MB)':<25} {cpp_mem:<15.2f} {zig_mem:<15.2f} {show_winner(cpp_mem, zig_mem):<15}")
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
