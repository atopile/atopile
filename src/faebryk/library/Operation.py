# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import typing
from textwrap import indent

from faebryk.core.parameter import Parameter
from faebryk.libs.util import TwistArgs, find, try_avoid_endless_recursion

logger = logging.getLogger(__name__)


class Operation(Parameter):
    class OperationNotExecutable(Exception): ...

    type LIT_OR_PARAM = Parameter.LIT_OR_PARAM

    def __init__(
        self,
        operands: typing.Iterable[LIT_OR_PARAM],
        operation: typing.Callable[..., Parameter],
    ) -> None:
        super().__init__()
        self.operands = tuple(self.from_literal(o) for o in operands)
        self.operation = operation

    @try_avoid_endless_recursion
    def __repr__(self):
        opsnames = {
            "Parameter.__truediv__": "/",
            "Parameter.__add__": "+",
            "Parameter.__sub__": "-",
            "Parameter.__mul__": "*",
        }

        op = self.operation
        operands = self.operands

        # little hack to make it look better
        if isinstance(op, TwistArgs):
            op = op.op
            operands = list(reversed(operands))

        fname = op.__qualname__

        try:
            fname = find(opsnames.items(), lambda x: fname.startswith(x[0]))[1]
        except KeyError:
            ...

        n = self.get_most_narrow()
        rep = repr(n) if n is not self else super().__repr__()
        return (
            rep
            + f"[{fname}]"
            + f"(\n{'\n'.join(indent(repr(o), '  ') for o in operands)}\n)"
        )

    def _execute(self):
        operands = [o.get_most_narrow() for o in self.operands]
        out = self.operation(*operands)
        if isinstance(out, Operation):
            raise Operation.OperationNotExecutable()
        logger.debug(f"{operands=} resolved to {out}")
        return out

    def try_compress(self) -> Parameter:
        try:
            return self._execute()
        except Operation.OperationNotExecutable:
            return self
