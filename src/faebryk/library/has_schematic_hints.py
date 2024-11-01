# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.libs.library import L


class has_schematic_hints(L.Module.TraitT.decless()):
    """
    Hints for the schematic exporter.

    Attributes:
        lock_rotation_certainty: Don't rotate symbols to that have an obviously
            correct orientation (eg a power source with the positive terminal up).
    """

    def __init__(self, lock_rotation_certainty: float = 0.6):
        self.lock_rotation_certainty = lock_rotation_certainty
