# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import typing
from textwrap import indent
from typing import Generic, TypeVar

from faebryk.core.core import Parameter
from faebryk.libs.util import TwistArgs, find, try_avoid_endless_recursion

logger = logging.getLogger(__name__)

PV = TypeVar("PV")


class Operation(Generic[PV], Parameter[PV]):
    class OperationNotExecutable(Exception): ...

    def __init__(
        self,
        operands: typing.Sequence[Parameter[PV]],
        operation: typing.Callable[..., Parameter[PV]],
    ) -> None:
        super().__init__()
        self.operands = operands
        self.operation = operation

    @try_avoid_endless_recursion
    def __repr__(self):
        opsnames = {
            Parameter.__truediv__: "/",
            Parameter.__add__: "+",
            Parameter.__sub__: "-",
            Parameter.__mul__: "*",
        }

        op = self.operation
        operands = self.operands

        # little hack to make it look better
        if isinstance(op, TwistArgs):
            op = op.op
            operands = list(reversed(operands))

        fname = op.__qualname__

        try:
            fname = find(
                opsnames.items(), lambda x: fname.startswith(x[0].__qualname__)
            )[1]
        except KeyError:
            ...

        return (
            super().__repr__()
            + f"[{fname}]"
            + f"(\n{'\n'.join(indent(repr(o), '  ') for o in operands)}\n)"
        )

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
