# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.has_kicad_ref import has_kicad_ref


class has_defined_kicad_ref(has_kicad_ref.impl()):
    def __init__(self, ref: str) -> None:
        super().__init__()
        self.ref = ref

    def get_ref(self) -> str:
        return self.ref
