#!/usr/bin/env python3
"""Test script for the pyzig extension module."""

# Now import and test
print("\nTesting the extension...")
import faebryk.core.zig.experiment as pyzig  # noqa: E402

# Test the add function
result = pyzig.add(a=3, b=7)
print(f"pyzig.add(3, 7) = {result}")
assert result == 10, f"Expected 10, got {result}"

result = pyzig.add(a=-5, b=15)
print(f"pyzig.add(-5, 15) = {result}")
assert result == 10, f"Expected 10, got {result}"

result = pyzig.add(a=100, b=200)
print(f"pyzig.add(100, 200) = {result}")
assert result == 300, f"Expected 300, got {result}"

# Test the Top class
print("\nTesting Top class...")
top = pyzig.Top(10, 20)
print(f"Created: {top}")
print(f"top.a = {top.a}")
print(f"top.b = {top.b}")
print(f"top.sum() = {top.sum()}")

# Test attribute modification
top.a = 50
top.b = 75
print(f"After modification: {top}")
print(f"top.sum() = {top.sum()}")
assert top.sum() == 125, f"Expected 125, got {top.sum()}"

print("\nAll tests passed!")
