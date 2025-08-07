# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.trait import Trait


class has_kicad_ref(Trait):
    def get_ref(self) -> str:
        raise NotImplementedError()
