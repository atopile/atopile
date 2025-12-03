# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self, Type

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
from faebryk.library.Literals import Booleans, Numbers
from faebryk.library.Parameters import BooleanParameter
from faebryk.libs.util import once

if TYPE_CHECKING:
    from faebryk.library import Literals


class NumberDomain(fabll.Node):
    @dataclass
    class Args:
        negative: bool = False
        zero_allowed: bool = True
        integer: bool = False

    from faebryk.library.Parameters import can_be_operand

    # Type annotation for type checkers - assigned at module level
    BoundNumberDomainContext: Type["BoundNumberDomainContext"]  # type: ignore[assignment]
    _can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

    negative = BooleanParameter.MakeChild()
    zero_allowed = BooleanParameter.MakeChild()
    integer = BooleanParameter.MakeChild()

    def setup(self, args: Args | None = None) -> Self:
        args = args or self.Args()
        self.negative.get().alias_to_single(value=args.negative)
        self.zero_allowed.get().alias_to_single(value=args.zero_allowed)
        self.integer.get().alias_to_single(value=args.integer)
        return self

    @classmethod
    def MakeChild(
        cls,
        negative: bool = False,
        zero_allowed: bool = True,
        integer: bool = False,
    ):
        out = fabll._ChildField(cls)
        out.add_dependant(
            *cls.MakeEdges(
                ref=[out],
                negative=negative,
                zero_allowed=zero_allowed,
                integer=integer,
            )
        )
        return out

    @classmethod
    def MakeEdges(
        cls,
        ref: list[str | fabll._ChildField[Any]],
        negative: bool = False,
        zero_allowed: bool = True,
        integer: bool = False,
    ):
        out = [
            Booleans.MakeChild_ConstrainToLiteral([*ref, cls.negative], negative),
            Booleans.MakeChild_ConstrainToLiteral(
                [*ref, cls.zero_allowed], zero_allowed
            ),
            Booleans.MakeChild_ConstrainToLiteral([*ref, cls.integer], integer),
        ]
        return out

    def get_args(self) -> Args:
        return NumberDomain.Args(
            negative=self.negative.get().extract_single(),
            zero_allowed=self.zero_allowed.get().extract_single(),
            integer=self.integer.get().extract_single(),
        )

    def unbounded(
        self,
        units: type[fabll.NodeT],
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "Literals.Numbers":
        from faebryk.library.Units import is_unit

        if self.integer.get().extract_single():
            # TODO
            pass
        if not self.zero_allowed.get().extract_single():
            # TODO
            raise NotImplementedError("Non-zero unbounded not implemented")
        if self.negative.get().extract_single():
            # TODO
            pass
        g = g or self.g
        tg = tg or self.tg
        has_unit = units.bind_typegraph(tg=tg).create_instance(g=g)
        return Numbers.unbounded(g=g, tg=tg, unit=has_unit.get_trait(is_unit))

    @classmethod
    def get_shared_domain(
        cls,
        *domains: "NumberDomain",
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
    ) -> "NumberDomain":
        if len(domains) == 0:
            raise ValueError("No domains provided")
        new_domain = cls.bind_typegraph(tg=tg).create_instance(g=g)
        one = domains[0].get_args()
        if len(domains) == 1:
            return new_domain.setup(args=one)
        two = domains[1].get_args()

        # TODO could consider just using And() expression, but lets leave this for now
        shared = new_domain.setup(
            args=NumberDomain.Args(
                negative=one.negative and two.negative,
                zero_allowed=one.zero_allowed and two.zero_allowed,
                integer=one.integer or two.integer,
            )
        )

        if len(domains) == 2:
            return shared
        return NumberDomain.get_shared_domain(shared, *domains[2:], g=g, tg=tg)

    def as_operand(self) -> "can_be_operand":
        return self._can_be_operand.get()


# Binding context ----------------------------------------------------------------------


class BoundNumberDomainContext:
    def __init__(self, tg: graph.TypeGraph, g: graph.GraphView):
        self.tg = tg
        self.g = g

    @property
    @once
    def NumberDomain(self):
        return NumberDomain.bind_typegraph(tg=self.tg)

    def create_number_domain(
        self,
        args: "NumberDomain.Args",
    ) -> "NumberDomain":
        return self.NumberDomain.create_instance(g=self.g).setup(args=args)


NumberDomain.BoundNumberDomainContext = BoundNumberDomainContext
