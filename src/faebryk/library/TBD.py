# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Generic, TypeVar

from faebryk.core.core import Parameter

PV = TypeVar("PV")


class TBD(Generic[PV], Parameter[PV]):
    def __init__(self) -> None:
        super().__init__()

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, TBD):
            return True

        return False

    def __hash__(self) -> int:
        return super().__hash__()
