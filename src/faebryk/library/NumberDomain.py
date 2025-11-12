# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Any, Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class NumberDomain(fabll.Node):
    negative = F.Parameters.BooleanParameter.MakeChild()
    zero_allowed = F.Parameters.BooleanParameter.MakeChild()
    integer = F.Parameters.BooleanParameter.MakeChild()

    def setup(
        self, negative: bool = False, zero_allowed: bool = True, integer: bool = False
    ) -> Self:
        self.negative.get().constrain_to_single(value=negative)
        self.zero_allowed.get().constrain_to_single(value=zero_allowed)
        self.integer.get().constrain_to_single(value=integer)
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
            *cls.EdgeFields(
                ref=[out],
                negative=negative,
                zero_allowed=zero_allowed,
                integer=integer,
            )
        )
        return out

    @classmethod
    def EdgeFields(
        cls,
        ref: list[str | fabll._ChildField[Any]],
        negative: bool = False,
        zero_allowed: bool = True,
        integer: bool = False,
    ):
        out = [
            F.Literals.Booleans.MakeChild_ConstrainToLiteral(
                [*ref, cls.negative], negative
            ),
            F.Literals.Booleans.MakeChild_ConstrainToLiteral(
                [*ref, cls.zero_allowed], zero_allowed
            ),
            F.Literals.Booleans.MakeChild_ConstrainToLiteral(
                [*ref, cls.integer], integer
            ),
        ]
        return out

    def unbounded(self, units: type[fabll.NodeT]) -> "F.Literals.Numbers":
        if self.integer.get().extract_single():
            # TODO
            pass
        if not self.zero_allowed.get().extract_single():
            # TODO
            raise NotImplementedError("Non-zero unbounded not implemented")
        if self.negative.get().extract_single():
            # TODO
            pass
        return F.Literals.Numbers.unbounded(units=units)

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
