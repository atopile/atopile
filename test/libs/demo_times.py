#!/usr/bin/env python3
"""
Demos for the Times class.

Run with: python test/libs/demo_times.py
"""
# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import time

from rich.console import Console

from faebryk.libs.test.times import Times


def demo_basic():
    """Basic timing demonstration."""
    print("\n" + "=" * 60)
    print("DEMO: Basic Timing")
    print("=" * 60)

    t = Times()

    # Measure time since creation
    time.sleep(0.05)
    t.add("startup")

    # Measure time since last add()
    time.sleep(0.02)
    t.add("initialization")

    # Add explicit duration
    t.add("external_call", duration=0.15)

    print(t.to_str())


def demo_context_manager():
    """Context manager demonstration."""
    print("\n" + "=" * 60)
    print("DEMO: Context Manager (measure)")
    print("=" * 60)

    t = Times()

    with t.measure("fast_operation"):
        time.sleep(0.01)

    with t.measure("slow_operation"):
        time.sleep(0.05)

    with t.measure("medium_operation"):
        time.sleep(0.03)

    print(t.to_str())


def demo_nested_timing():
    """Nested timing demonstration using child()."""
    print("\n" + "=" * 60)
    print("DEMO: Nested Timing with explicit child()")
    print("=" * 60)

    # Parent timer
    build = Times(name="build")

    # Child timer for compilation
    compile_timer = build.child("compile")
    with compile_timer.measure("parse"):
        time.sleep(0.02)
    with compile_timer.measure("optimize"):
        time.sleep(0.03)
    with compile_timer.measure("codegen"):
        time.sleep(0.01)

    # Child timer for tests
    test_timer = build.child("test")
    with test_timer.measure("unit"):
        time.sleep(0.02)
    with test_timer.measure("integration"):
        time.sleep(0.04)

    # Add top-level timing
    build.add("package", duration=0.01)

    print("Child timer (compile):")
    print(compile_timer.to_str())

    print("\nChild timer (test):")
    print(test_timer.to_str())

    print("\nParent timer (build) - includes all child measurements:")
    print(build.to_str())


def demo_auto_nesting():
    """Automatic nesting demonstration - Times created inside measure() auto-link."""
    print("\n" + "=" * 60)
    print("DEMO: Automatic Nesting (3 levels)")
    print("=" * 60)

    level1 = Times(name="level1")

    with level1.measure("outer_work"):
        time.sleep(0.01)

        # level2 is automatically linked to level1 because it's inside measure()
        level2 = Times(name="level2")
        level2.add("level2_direct", duration=0.05)

        with level2.measure("middle_work"):
            time.sleep(0.02)

            # level3 is automatically linked to level2
            level3 = Times(name="level3")
            level3.add("deep_task_a", duration=0.03)
            level3.add("deep_task_b", duration=0.04)

    print("Level 3 (deepest) - only its own measurements:")
    print(level3.to_str())

    print("\nLevel 2 - its own + level3 prefixed:")
    print(level2.to_str())

    print("\nLevel 1 (top) - its own + level2:* + level2:level3:*:")
    print(level1.to_str())


def demo_multiple_samples():
    """Multiple samples with different strategies."""
    print("\n" + "=" * 60)
    print("DEMO: Multiple Samples & Strategies")
    print("=" * 60)

    # Using ALL strategy to show all aggregations
    t = Times(strategy=Times.Strategy.ALL)

    # Simulate multiple runs of the same operation
    for i in range(10):
        duration = 0.01 + (i * 0.005)  # Increasing durations
        t.add("operation", duration=duration)

    print("With Strategy.ALL (shows AVG, SUM, MIN, MAX, MEDIAN, P80):")
    print(t.to_str())

    # Now with AVG strategy
    t2 = Times(strategy=Times.Strategy.AVG)
    for i in range(10):
        duration = 0.01 + (i * 0.005)
        t2.add("operation", duration=duration)

    print("\nWith Strategy.AVG:")
    print(t2.to_str())


def demo_grouping():
    """Grouping and separators demonstration."""
    print("\n" + "=" * 60)
    print("DEMO: Grouping & Separators")
    print("=" * 60)

    t = Times()

    # Setup phase
    t.add("setup:config", duration=0.01)
    t.add("setup:database", duration=0.02)
    t.add("setup:cache", duration=0.005)

    t.separator()

    # Run phase
    t.add("run:fetch", duration=0.1)
    t.add("run:process", duration=0.2)
    t.add("run:save", duration=0.05)

    t.separator()

    # Cleanup phase
    t.add("cleanup:temp", duration=0.01)
    t.add("cleanup:connections", duration=0.02)

    # Create groups
    t.group("Total setup", "setup:")
    t.group("Total run", "run:")
    t.group("Total cleanup", "cleanup:")

    print(t.to_str())


def demo_formatted_output():
    """Formatted output demonstration."""
    print("\n" + "=" * 60)
    print("DEMO: Formatted Output")
    print("=" * 60)

    t = Times()
    t.add("quick", duration=0.001)  # 1ms
    t.add("medium", duration=0.5)  # 500ms
    t.add("slow", duration=2.5)  # 2.5s

    print(f"Quick (default ms): {t.get_formatted('quick')}")
    print(f"Quick (in us): {t.get_formatted('quick', unit='us')}")
    print(f"Medium (default ms): {t.get_formatted('medium')}")
    print(f"Slow (in s): {t.get_formatted('slow', unit='s')}")
    print(f"Slow (in ms): {t.get_formatted('slow', unit='ms')}")


def demo_color_gradient():
    """Color gradient demonstration."""
    print("\n" + "=" * 60)
    print("DEMO: Color Gradient (quartile-based)")
    print("=" * 60)

    t = Times()

    # Add measurements with varying durations
    # Green: bottom 25% (fastest)
    t.add("very_fast_1", duration=0.001)
    t.add("very_fast_2", duration=0.002)

    # Yellow: middle 50%
    t.add("medium_1", duration=0.01)
    t.add("medium_2", duration=0.02)
    t.add("medium_3", duration=0.03)

    # Red: top 25% (slowest)
    t.add("slow_1", duration=0.1)
    t.add("slow_2", duration=0.2)

    console = Console()
    console.print("\nValues are colored: [green]green[/green]=fast, "
                  "[yellow]yellow[/yellow]=medium, [red]red[/red]=slow")
    console.print(t.to_table())


def demo_real_world():
    """Real-world-like usage demonstration."""
    print("\n" + "=" * 60)
    print("DEMO: Real-World Usage Pattern")
    print("=" * 60)

    t = Times(name="api_request")

    # Simulate an API request pipeline
    with t.measure("auth"):
        time.sleep(0.01)  # Authentication

    with t.measure("validate"):
        time.sleep(0.005)  # Input validation

    with t.measure("query_db"):
        time.sleep(0.05)  # Database query

    with t.measure("transform"):
        time.sleep(0.02)  # Data transformation

    with t.measure("serialize"):
        time.sleep(0.01)  # Response serialization

    t.separator()
    t.group("Total processing", lambda k: k in ["validate", "transform", "serialize"])

    console = Console()
    console.print(t.to_table())

    # Show how to get specific values
    print(f"\nTotal request time (SUM): {t.get_formatted('query_db')}")


def main():
    """Run all demos."""
    demo_basic()
    demo_context_manager()
    demo_nested_timing()
    demo_auto_nesting()
    demo_multiple_samples()
    demo_grouping()
    demo_formatted_output()
    demo_color_gradient()
    demo_real_world()

    print("\n" + "=" * 60)
    print("All demos complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
