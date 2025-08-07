# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_symbol_layout_defined(F.has_symbol_layout.impl()):
    def __init__(self, translations: str = ""):
        super().__init__()
        self.translations = translations
