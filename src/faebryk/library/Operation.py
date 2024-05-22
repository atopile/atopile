# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import typing
from typing import Generic, TypeVar

from faebryk.core.core import Parameter

logger = logging.getLogger(__name__)

PV = TypeVar("PV")


class Operation(Generic[PV], Parameter[PV]):
    class OperationNotExecutable(Exception):
        ...

    def __init__(
        self,
        operands: typing.Sequence[Parameter[PV]],
        operation: typing.Callable[..., Parameter[PV]],
    ) -> None:
        super().__init__()
        self.operands = operands
        self.operation = operation

    def __repr__(self):
        return super().__repr__() + f"({self.operands!r})"
        # return f"{type(self).__name__}({self.operands!r})@{id(self):#x}"

    def execute(self):
        operands = [o.get_most_narrow() for o in self.operands]
        out = self.operation(*operands)
        if isinstance(out, Operation):
            raise Operation.OperationNotExecutable()
        self._narrowed(out)
        logger.debug(f"{operands=} resolved to {out}")
        return out

    def get_most_narrow(self) -> Parameter[PV]:
        out = super().get_most_narrow()
        if out is self:
            try:
                return self.execute()
            except Operation.OperationNotExecutable:
                pass
        return out
