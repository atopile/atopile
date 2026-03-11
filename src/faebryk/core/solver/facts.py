# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Any, Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.library.Expressions import (
    OperandPointer,
    _make_instance_from_operand_instance,
    _op,
    get_operand_path,
    is_assertable,
    is_canonical,
    is_expression,
    is_expression_type,
    is_logic,
    is_predicate,
    is_setic,
)


class IsUniversalEnclosure(fabll.Node):
    """
    A ss!∀[S](l, u)
    -> forall s in lower_subset(S): A(s) ss! [l, u]

    Ordered endpoints are stored directly because the staged uncertainty pass
    also persists carrier states with `l > u`, which cannot be represented as
    a Numbers literal.
    """

    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        F.Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression_type = fabll.Traits.MakeEdge(
        is_expression_type.MakeChild(
            repr_style=is_expression_type.ReprStyle(
                symbol="⊆∀", placement=is_expression_type.ReprStyle.Placement.PREFIX
            )
        ).put_on_type()
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    is_expression = fabll.Traits.MakeEdge(is_expression.MakeChild())
    is_logic = fabll.Traits.MakeEdge(is_logic.MakeChild())
    is_setic = fabll.Traits.MakeEdge(is_setic.MakeChild())

    # Operand identifiers participate in ordering, so these preserve:
    # superset, source, universal_min, universal_max.
    superset = OperandPointer.MakeChild()
    zsource = OperandPointer.MakeChild()

    # Can't use Numbers literal because we don't require min <= max.
    zuniversal_min = OperandPointer.MakeChild()
    zzuniversal_max = OperandPointer.MakeChild()

    def get_superset_operand(self) -> "F.Parameters.can_be_operand":
        return self.superset.get().deref().cast(F.Parameters.can_be_operand)

    def get_source_operand(self) -> "F.Parameters.can_be_operand":
        return self.zsource.get().deref().cast(F.Parameters.can_be_operand)

    def get_universal_min_operand(self) -> "F.Parameters.can_be_operand":
        return self.zuniversal_min.get().deref().cast(F.Parameters.can_be_operand)

    def get_universal_max_operand(self) -> "F.Parameters.can_be_operand":
        return self.zzuniversal_max.get().deref().cast(F.Parameters.can_be_operand)

    def get_universal_enclosure(self) -> tuple[float, float]:
        return (
            fabll.Traits(self.get_universal_min_operand().as_literal.force_get())
            .get_obj_raw()
            .cast(F.Literals.Numbers)
            .get_single(),
            fabll.Traits(self.get_universal_max_operand().as_literal.force_get())
            .get_obj_raw()
            .cast(F.Literals.Numbers)
            .get_single(),
        )

    @classmethod
    def MakeChild(
        cls,
        superset: fabll.RefPath,
        source: fabll.RefPath,
        universal_min: fabll.RefPath,
        universal_max: fabll.RefPath,
        assert_: bool = False,
    ) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        if assert_:
            out.add_dependant(
                fabll.Traits.MakeEdge(is_predicate.MakeChild(), [out]),
            )
        out.add_dependant(
            OperandPointer.MakeEdge([out, cls.superset], get_operand_path(superset)),
        )
        out.add_dependant(
            OperandPointer.MakeEdge([out, cls.zsource], get_operand_path(source)),
        )
        out.add_dependant(
            OperandPointer.MakeEdge(
                [out, cls.zuniversal_min], get_operand_path(universal_min)
            ),
        )
        out.add_dependant(
            OperandPointer.MakeEdge(
                [out, cls.zzuniversal_max], get_operand_path(universal_max)
            ),
        )
        return out

    def setup(
        self,
        superset: "F.Parameters.can_be_operand",
        source: "F.Parameters.can_be_operand",
        universal_min: "F.Parameters.can_be_operand",
        universal_max: "F.Parameters.can_be_operand",
        assert_: bool = False,
    ) -> Self:
        def validate_endpoint(operand: "F.Parameters.can_be_operand") -> None:
            lit = operand.as_literal.force_get()
            num = fabll.Traits(lit).get_obj_raw().try_cast(F.Literals.Numbers)
            assert num is not None and num.is_singleton(), (
                "universal enclosure endpoints must be singleton numeric literals"
            )

        validate_endpoint(universal_min)
        validate_endpoint(universal_max)

        self.superset.get().point(superset)
        self.zsource.get().point(source)
        self.zuniversal_min.get().point(universal_min)
        self.zzuniversal_max.get().point(universal_max)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        superset: "F.Parameters.can_be_operand",
        source: "F.Parameters.can_be_operand",
        universal_min: "F.Parameters.can_be_operand",
        universal_max: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls,
            (superset, source, universal_min, universal_max),
            g=g,
            tg=tg,
        )
        return instance.setup(
            superset, source, universal_min, universal_max, assert_=assert_
        )

    @classmethod
    def c(
        cls,
        superset: "F.Parameters.can_be_operand",
        source: "F.Parameters.can_be_operand",
        universal_min: "F.Parameters.can_be_operand",
        universal_max: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(
            cls.from_operands(
                superset,
                source,
                universal_min,
                universal_max,
                g=g,
                tg=tg,
                assert_=assert_,
            )
        )
