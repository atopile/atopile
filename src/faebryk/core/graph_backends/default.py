# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum, auto

from faebryk.libs.util import ConfigFlagEnum


class Backends(StrEnum):
    NX = auto()
    GT = auto()
    PY = auto()


BACKEND = ConfigFlagEnum(Backends, "BACKEND", Backends.PY, "Graph backend")

if BACKEND == Backends.GT:
    from faebryk.core.graph_backends.graphgt import GraphGT as GraphImpl  # noqa: F401
elif BACKEND == Backends.NX:
    from faebryk.core.graph_backends.graphnx import GraphNX as GraphImpl  # noqa: F401
elif BACKEND == Backends.PY:
    from faebryk.core.graph_backends.graphpy import GraphPY as GraphImpl  # noqa: F401
else:
    print(BACKEND)
    assert False
