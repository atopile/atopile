# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING, Any, Self, Type

import faebryk.core.graph as graph
import faebryk.core.node as fabll
from faebryk.library.Literals import Booleans, Numbers
from faebryk.library.Parameters import BooleanParameter
from faebryk.libs.util import once

if TYPE_CHECKING:
    from faebryk.library import Literals


class NumberDomain(fabll.Node):
    # Type annotation for type checkers - assigned at module level
    BoundNumberDomainContext: Type["BoundNumberDomainContext"]  # type: ignore[assignment]

    negative = BooleanParameter.MakeChild()
    zero_allowed = BooleanParameter.MakeChild()
    integer = BooleanParameter.MakeChild()

    def setup(
        self, negative: bool = False, zero_allowed: bool = True, integer: bool = False
    ) -> Self:
        self.negative.get().alias_to_single(value=negative)
        self.zero_allowed.get().alias_to_single(value=zero_allowed)
        self.integer.get().alias_to_single(value=integer)
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

    def unbounded(self, units: type[fabll.NodeT]) -> "Literals.Numbers":
        if self.integer.get().extract_single():
            # TODO
            pass
        if not self.zero_allowed.get().extract_single():
            # TODO
            raise NotImplementedError("Non-zero unbounded not implemented")
        if self.negative.get().extract_single():
            # TODO
            pass
        return Numbers.unbounded(units=units)

    @classmethod
    def get_shared_domain(cls, *domains: "NumberDomain") -> "NumberDomain":
        if len(domains) == 0:
            raise ValueError("No domains provided")
        if len(domains) == 1:
            return domains[0]
        one, two = domains[:2]

        # TODO could consider just using And() expression, but lets leave this for now
        shared = (
            cls.bind_typegraph_from_instance(one.instance)
            .create_instance(one.instance.g())
            .setup(
                negative=one.negative.get().extract_single()
                and two.negative.get().extract_single(),
                zero_allowed=one.zero_allowed.get().extract_single()
                and two.zero_allowed.get().extract_single(),
                integer=one.integer.get().extract_single()
                or two.integer.get().extract_single(),
            )
        )

        if len(domains) == 2:
            return shared
        return NumberDomain.get_shared_domain(shared, *domains[2:])


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
        negative: bool = False,
        zero_allowed: bool = True,
        integer: bool = False,
    ) -> "NumberDomain":
        return self.NumberDomain.create_instance(g=self.g).setup(
            negative=negative,
            zero_allowed=zero_allowed,
            integer=integer,
        )


NumberDomain.BoundNumberDomainContext = BoundNumberDomainContext
