# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass
from typing import Any, Optional

import faebryk.core.node as fabll
import faebryk.library._F as F
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

    # @staticmethod
    # def of(spec_node: "SpecNode") -> Spec:
    #     return Spec(
    #         param=spec_node.param,
    #         unit=spec_node.unit,
    #         tolerance=spec_node.tolerance,
    #         prefix=spec_node.prefix,
    #         suffix=spec_node.suffix,
    #         default=spec_node.default,
    #     )

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

        @property
        def default(self) -> fabll.LiteralT | None:
            literal = F.Parameters.StringParameter.bind_instance(
                self.default_.get().instance
            ).try_extract_constrained_literal()
            return "" if literal is None else str(literal)

        def _get_value(self) -> str:
            value = self.param.get_name()
            if value is None:
                if self.default is not None:
                    return str(self.default)
                raise
            else:
                return value  # TODO: Where shoudl value actually come from?

            domain = self.param.domain

            # TODO this is probably not the only place we will ever need
            #  this big switch
            # consider moving it somewhere else
            if isinstance(domain, EnumDomain):
                if self.tolerance:
                    raise ValueError("tolerance not supported for enum")
                # TODO handle units
                enum = EnumSet.from_value(value)
                if not enum.is_single_element():
                    raise NotImplementedError()
                val = next(iter(enum.elements))
                # TODO not sure I like this
                if isinstance(val.value, str):
                    return val.value
                return val.name

            if isinstance(domain, Boolean):
                if self.tolerance:
                    raise ValueError("tolerance not supported for boolean")
                bool_val = BoolSet.from_value(value)
                if not bool_val.is_single_element():
                    raise NotImplementedError()
                return str(next(iter(bool_val.elements))).lower()

            if isinstance(domain, Numbers):
                unit = self.unit if self.unit is not None else self.param.units
                # TODO If tolerance, maybe hint that it's weird there isn't any
                value_lit = Quantity_Interval_Disjoint.from_value(value)
                if value_lit.is_single_element():
                    return to_si_str(value_lit.min_elem, unit, 2)
                if len(value_lit._intervals.intervals) > 1:
                    raise NotImplementedError()
                center, tolerance = value_lit.as_gapless().as_center_tuple(
                    relative=True
                )
                center_str = to_si_str(center, unit, 2)
                assert isinstance(tolerance, Quantity)
                if self.tolerance and tolerance > 0:
                    tolerance_str = f" ±{to_si_str(tolerance, '%', 0)}"
                    return f"{center_str}{tolerance_str}"
                return center_str

            raise NotImplementedError(f"No support for {domain}")

        def get_value(self) -> str:
            try:
                value = self._get_value()
            except Exception as e:
                if self.default is None:
                    raise
                logger.debug(f"Failed to get value for `{self.param}`: {e}")
                return ""
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
                F.Collections.Pointer.EdgeField(
                    [out, cls.param_ptr_],
                    [spec.param],
                )
            )
            if spec.unit is not None:
                # TODO: Fix units
                print(spec.unit.get_full_name())
                out.add_dependant(
                    F.Collections.Pointer.EdgeField(
                        [out, cls.unit_],
                        [spec.unit.get_full_name()],
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
            F.Collections.PointerSet.EdgeFields(
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

    _is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

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
        for spec in specs:
            spec_node = cls.SpecNode.MakeChild(spec)
            out.add_dependant(spec_node)
            out.add_dependant(
                F.Collections.PointerSet.EdgeField(
                    [out, cls.specs_set_],
                    [spec_node],
                )
            )
        return out

    # def __init__(self, *specs: Spec, prefix: str = "", suffix: str = "") -> None:
    #     super().__init__()
    #     self.specs = specs
    #     self.prefix = prefix
    #     self.suffix = suffix

    def get_value(self) -> str:
        return join_if_non_empty(
            " ",
            self.prefix,
            *[s.get_value() for s in self.specs],
            self.suffix,
        )
