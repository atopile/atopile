# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from dataclasses import dataclass

import faebryk.core.node as fabll


class NumberDomain(fabll.Node):
    @dataclass
    class Args:
        negative: bool = False
        zero_allowed: bool = True
        integer: bool = False
