# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.util import join_if_non_empty

logger = logging.getLogger(__name__)


class has_simple_value_representation(fabll.Node):
    @dataclass
    class Spec:
        param: fabll._ChildField
        unit: Optional[fabll.Node] = None
        tolerance: bool = False
        prefix: str = ""
        suffix: str = ""
        default: Optional[str] = None

    class SpecNode(fabll.Node):
        # TODO: Is the pointer set necessary? Can it be the spec node itself?
        spec_set_ = F.Collections.PointerSet.MakeChild()
        param_ptr_ = F.Collections.Pointer.MakeChild()
        unit_ = F.Collections.Pointer.MakeChild()
        tolerance_ = F.Parameters.BooleanParameter.MakeChild()
        prefix_ = F.Parameters.StringParameter.MakeChild()
        suffix_ = F.Parameters.StringParameter.MakeChild()
        default_ = F.Parameters.StringParameter.MakeChild()

        @property
        def param(self) -> fabll.Node:
            # assert isinstance(self.param_ptr_.get(), F.Collections.Pointer)
            return self.param_ptr_.get().deref()

        @property
        def prefix(self) -> str:
            literal = F.Parameters.StringParameter.bind_instance(
                self.prefix_.get().instance
            ).try_extract_constrained_literal()
            return "" if literal is None else literal.get_values()[0]

        @property
        def suffix(self) -> str:
            literal = F.Parameters.StringParameter.bind_instance(
                self.suffix_.get().instance
            ).try_extract_constrained_literal()
            return "" if literal is None else literal.get_values()[0]

        @property
        def default(self) -> str:
            literal = F.Parameters.StringParameter.bind_instance(
                self.default_.get().instance
            ).try_extract_constrained_literal()
            return "" if literal is None else literal.get_values()[0]

        def _get_value(self) -> str:
            lit = self.param.get_trait(
                F.Parameters.is_parameter_operatable
            ).try_get_aliased_literal()
            if lit is None:
                raise ValueError(f"No literal found for {self.param}")
            return lit.pretty_str()

            # TODO this is probably not the only place we will ever need
            #  this big switch
            # consider moving it somewhere else
            # if isinstance(domain, EnumDomain):
            #     if self.tolerance:
            #         raise ValueError("tolerance not supported for enum")
            #     # TODO handle units
            #     enum = EnumSet.from_value(value)
            #     if not enum.is_singleton():
            #         raise NotImplementedError()
            #     val = next(iter(enum.elements))
            #     # TODO not sure I like this
            #     if isinstance(val.value, str):
            #         return val.value
            #     return val.name

            # if isinstance(domain, Boolean):
            #     if self.tolerance:
            #         raise ValueError("tolerance not supported for boolean")
            #     bool_val = BoolSet.from_value(value)
            #     if not bool_val.is_singleton():
            #         raise NotImplementedError()
            #     return str(next(iter(bool_val.elements))).lower()

            # if isinstance(domain, Numbers):
            #     unit = self.unit if self.unit is not None else self.param.units
            #     # TODO If tolerance, maybe hint that it's weird there isn't any
            #     value_lit = Quantity_Interval_Disjoint.from_value(value)
            #     if value_lit.is_singleton():
            #         return to_si_str(value_lit.min_elem, unit, 2)
            #     if len(value_lit._intervals.intervals) > 1:
            #         raise NotImplementedError()
            #     center, tolerance = value_lit.as_gapless().as_center_tuple(
            #         relative=True
            #     )
            #     center_str = to_si_str(center, unit, 2)
            #     assert isinstance(tolerance, Quantity)
            #     if self.tolerance and tolerance > 0:
            #         tolerance_str = f" ±{to_si_str(tolerance, '%', 0)}"
            #         return f"{center_str}{tolerance_str}"
            #     return center_str

            # raise NotImplementedError(f"No support for {domain}")

        def get_value(self) -> str:
            try:
                value = self._get_value()
            except Exception as e:
                if not self.default:
                    logger.debug(f"No value or default for `{self.param}`: {e}")
                    return ""
                logger.debug(f"Failed to get value for `{self.param}`: {e}")
                return self.default
            return join_if_non_empty(
                " ",
                self.prefix,
                value,
                self.suffix,
            )

        @classmethod
        def MakeChild(
            cls,
            spec: "has_simple_value_representation.Spec",
        ):
            out = fabll._ChildField(cls)

            out.add_dependant(
                F.Collections.Pointer.MakeEdge(
                    [out, cls.param_ptr_],
                    [spec.param],
                )
            )
            if spec.unit is not None:
                spec_unit = spec.unit.MakeChild()
                out.add_dependant(spec_unit)
                out.add_dependant(
                    F.Collections.Pointer.MakeEdge(
                        [out, cls.unit_],
                        [spec_unit, "is_unit"],
                    )
                )

            # Constrain literals
            out.add_dependant(
                F.Literals.Booleans.MakeChild_ConstrainToLiteral(
                    [out, cls.tolerance_], spec.tolerance
                )
            )
            out.add_dependant(
                F.Literals.Strings.MakeChild_ConstrainToLiteral(
                    [out, cls.prefix_], spec.prefix
                )
            )
            out.add_dependant(
                F.Literals.Strings.MakeChild_ConstrainToLiteral(
                    [out, cls.suffix_], spec.suffix
                )
            )
            if spec.default is not None:
                out.add_dependant(
                    F.Literals.Strings.MakeChild_ConstrainToLiteral(
                        [out, cls.default_], spec.default
                    )
                )

            # Connect Spec Set to all fields
            F.Collections.PointerSet.MakeEdges(
                [out, cls.spec_set_],
                [
                    [out, cls.param_ptr_],
                    [out, cls.unit_],
                    [out, cls.tolerance_],
                    [out, cls.prefix_],
                    [out, cls.suffix_],
                    [out, cls.default_],
                ],
            )

            return out

    specs_set_ = F.Collections.PointerSet.MakeChild()
    prefix_ = F.Parameters.StringParameter.MakeChild()
    suffix_ = F.Parameters.StringParameter.MakeChild()

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def get_specs(self) -> list[SpecNode]:
        specs_set = self.specs_set_.get()
        assert isinstance(specs_set, F.Collections.PointerSet)
        node_list = specs_set.as_list()
        spec_list = [self.SpecNode.bind_instance(node.instance) for node in node_list]
        return spec_list

    def get_params(self):
        specs = self.get_specs()
        return [spec.param for spec in specs]

    @property
    def specs(self) -> list[SpecNode]:
        return self.get_specs()

    @property
    def prefix(self) -> fabll.LiteralT | None:
        literal = F.Parameters.StringParameter.bind_instance(
            self.prefix_.get().instance
        ).try_extract_constrained_literal()
        return "" if literal is None else str(literal)

    @property
    def suffix(self) -> fabll.LiteralT | None:
        literal = F.Parameters.StringParameter.bind_instance(
            self.suffix_.get().instance
        ).try_extract_constrained_literal()
        return "" if literal is None else str(literal)

    @classmethod
    def MakeChild(cls, *specs: Spec):
        out = fabll._ChildField(cls)
        # TODO: trips solver
        # for spec in specs:
        #     spec_node = cls.SpecNode.MakeChild(spec)
        #     out.add_dependant(spec_node)
        #     out.add_dependant(
        #         F.Collections.PointerSet.MakeEdge(
        #             [out, cls.specs_set_],
        #             [spec_node],
        #         )
        #     )
        return out

    def get_value(self) -> str:
        return join_if_non_empty(
            " ",
            self.prefix,
            *[s.get_value() for s in self.specs],
            self.suffix,
        )


def test_repr_chain_basic():
    import faebryk.library._F as F

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestModule(fabll.Node):
        param1 = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
        param2 = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
        param3 = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)

        S = has_simple_value_representation.Spec
        _simple_repr = fabll.Traits.MakeEdge(
            has_simple_value_representation.MakeChild(
                S(param=param1, prefix="TM", tolerance=True),
                S(param=param2, suffix="P2"),
                S(param=param3, tolerance=True, suffix="P3"),
            )
        )

    m = TestModule.bind_typegraph(tg).create_instance(g=g)
    m.param1.get().alias_to_literal(
        g=g,
        value=F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g=g)
        .setup_from_min_max(
            min=10.0,
            max=20,
            unit=F.Units.Volt.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get(),
        ),
    )
    m.param2.get().alias_to_literal(
        g=g,
        value=F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g=g)
        .setup_from_singleton(
            value=5.0,
            unit=F.Units.Ampere.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .is_unit.get(),
        ),
    )
    m.param3.get().alias_to_literal(
        g=g,
        value=F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g=g)
        .setup_from_singleton(
            value=10.0,
            unit=F.Units.Volt.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get(),
        ),
    )

    val = m._simple_repr.get().get_value()
    assert val == "TM {10.0..20.0}V 5.0A P2 10.0V P3"


def test_repr_chain_non_number():
    import faebryk.library._F as F

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestEnum(Enum):
        A = "AS"
        B = "BS"

    class TestModule(fabll.Node):
        param1 = F.Parameters.EnumParameter.MakeChild(TestEnum)
        param2 = F.Parameters.BooleanParameter.MakeChild()

        S = has_simple_value_representation.Spec
        _simple_repr = fabll.Traits.MakeEdge(
            has_simple_value_representation.MakeChild(
                S(param=param1),
                S(param=param2, prefix="P2:"),
            )
        )

    m = TestModule.bind_typegraph(tg).create_instance(g=g)
    # Use AbstractEnums directly - setup() internally uses EnumsFactory for type defs
    test_enum_lit = (
        F.Literals.AbstractEnums.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(TestEnum.A)
    )
    m.param1.get().is_parameter_operatable.get().alias_to_literal(
        g=g,
        value=test_enum_lit,
    )
    m.param2.get().alias_to_single(value=True)

    val = m._simple_repr.get().get_value()
    assert val == "AS P2: true"


def test_repr_chain_no_literal():
    import faebryk.library._F as F

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestModule(fabll.Node):
        param1 = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
        param2 = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
        param3 = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)

        S = has_simple_value_representation.Spec
        _simple_repr = fabll.Traits.MakeEdge(
            has_simple_value_representation.MakeChild(
                S(param=param1, default=None),
                S(param=param2),
                S(param=param3, default="P3: MISSING"),
            )
        )

    m = TestModule.bind_typegraph(tg).create_instance(g=g)

    val = m._simple_repr.get().get_value()
    assert val == "P3: MISSING"

    m.param1.get().alias_to_literal(
        g=g,
        value=F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g=g)
        .setup_from_singleton(
            value=10.0,
            unit=F.Units.Volt.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get(),
        ),
    )
    val = m._simple_repr.get().get_value()
    assert val == "10.0V P3: MISSING"
