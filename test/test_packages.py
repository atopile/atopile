# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from dataclasses import fields
from pathlib import Path

import pytest
from dataclasses_json import CatchAll
from dataclasses_json.utils import CatchAllVar

from atopile.packages import KNOWN_PACKAGES_TO_FOOTPRINT
from faebryk.libs.kicad.fileformats_latest import C_kicad_footprint_file
from faebryk.libs.sexp.dataclass_sexp import dataclass_dfs


def load_footprint(package_path: Path) -> C_kicad_footprint_file:
    """Load a footprint file and return the parsed dataclass."""
    return C_kicad_footprint_file.loads(package_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("package_path", KNOWN_PACKAGES_TO_FOOTPRINT.values())
def test_no_unknown_fields(package_path: Path):
    """Test that no fields in the footprint are marked as unknown.

    This test ensures that all fields in the footprint file can be properly parsed
    into our dataclass structure without falling back to CatchAll fields, which would
    indicate a mismatch between our schema and the file format.
    """
    footprint = load_footprint(package_path)

    # Walk through all dataclass instances in the footprint
    for obj, path, name_path in dataclass_dfs(footprint):
        # dataclass_dfs returns all objects in the tree, including non-dataclass ones
        # like strings and numbers. We only want to check dataclass instances, which
        # have the special __dataclass_fields__ attribute.
        if not hasattr(obj, "__dataclass_fields__"):
            continue

        # Find any CatchAll fields in this dataclass. CatchAll fields are used by
        # dataclasses-json to store any JSON fields that don't match our schema.
        catch_all_fields = [f for f in fields(obj) if f.type in (CatchAll, CatchAllVar)]

        # For each CatchAll field, verify it's None (no unknown fields). A non-None
        # value would indicate that the file contained data we weren't expecting
        # and couldn't properly parse into our schema.
        for field in catch_all_fields:
            value = getattr(obj, field.name)
            assert value is None, (
                f"Found non-None CatchAll field '{field.name}' at {'.'.join(name_path)}"
                f" with value: {value}"
            )
