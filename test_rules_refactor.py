#!/usr/bin/env python3
"""Test script to verify the refactored rules export produces the same output."""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from faebryk.exporters.pcb.rules.rules import export_rules as export_rules_old
# from faebryk.exporters.pcb.rules.export_refactored import (
    export_rules as export_rules_new,  # removed in consolidation
)


# Mock the required modules for testing
class MockSolver:
    def inspect_get_known_supersets(self, param):
        return None


class MockModule:
    def get_children_modules(self, direct_only=False, types=None):
        return []

    def get_children(self, direct_only=False, types=None):
        return []


def compare_outputs():
    """Compare the outputs of the old and new export_rules functions."""
    # Create mock objects
    app = MockModule()
    solver = MockSolver()

    # Test with the examples/design_rules project
    import os

    original_dir = os.getcwd()

    try:
        # Change to the design_rules example directory
        os.chdir(Path(__file__).parent / "examples" / "design_rules")

        # Run old implementation
        print("Running old implementation...")
        export_rules_old(app, solver)
        old_output = Path("layout/default/default.kicad_dru").read_text()

        # Backup old output
        Path("layout/default/default.kicad_dru.old").write_text(old_output)

        # Run new implementation
        print("Running new implementation...")
        export_rules_new(app, solver)
        new_output = Path("layout/default/default.kicad_dru").read_text()

        # Compare outputs
        if old_output == new_output:
            print("✅ Outputs match perfectly!")
            return True
        else:
            print("❌ Outputs differ!")
            print("\nOld output preview:")
            print(old_output[:500])
            print("\nNew output preview:")
            print(new_output[:500])

            # Save for comparison
            Path("layout/default/default.kicad_dru.new").write_text(new_output)
            print("\nSaved outputs to:")
            print("  - layout/default/default.kicad_dru.old (original)")
            print("  - layout/default/default.kicad_dru.new (refactored)")

            return False
    finally:
        os.chdir(original_dir)


if __name__ == "__main__":
    if compare_outputs():
        sys.exit(0)
    else:
        sys.exit(1)
