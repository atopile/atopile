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
            return (
                F.Parameters.StringParameter.bind_instance(
                    self.prefix_.get().instance
                ).try_extract_singleton()
                or ""
            )

        @property
        def suffix(self) -> str:
            return (
                F.Parameters.StringParameter.bind_instance(
                    self.suffix_.get().instance
                ).try_extract_singleton()
                or ""
            )

        @property
        def default(self) -> str:
            return (
                F.Parameters.StringParameter.bind_instance(
                    self.default_.get().instance
                ).try_extract_singleton()
                or ""
            )

        def _get_value(self, show_tolerance: Optional[bool] = None) -> str:
            try:
                _, part_picked = self.param.get_parent_with_trait(
                    F.Pickable.has_part_picked
                )
                param_name = self.param.get_name()
                if (is_lit := part_picked.get_attribute(param_name)) is not None:
                    return self._format_literal(is_lit, show_tolerance)
            except KeyError:
                # No picked part, or attribute not found, continue
                # extracting from constraints
                pass

            # Fallback: extract from parameter constraints
            lit = self.param.get_trait(
                F.Parameters.is_parameter_operatable
            ).try_extract_superset()

            if lit is None:
                raise ValueError(f"No literal found for {self.param}")

            return self._format_literal(lit, show_tolerance)

        def _format_literal(
            self, lit: "F.Literals.is_literal", show_tolerance: Optional[bool]
        ) -> str:
            """Format a literal for display."""
            tolerance_preference = (
                F.Parameters.BooleanParameter.bind_instance(
                    self.tolerance_.get().instance
                ).try_extract_singleton()
                is True
            )
            # `self.tolerance_` is the preference/default.
            # `show_tolerance` (if provided) overrides it.
            show_tolerance = (
                tolerance_preference if show_tolerance is None else show_tolerance
            )

            # NumericParameter handles display unit conversion
            numeric_param = self.param.try_cast(F.Parameters.NumericParameter)
            concrete_lit = lit.switch_cast()
            numbers_lit = concrete_lit.try_cast(F.Literals.Numbers)

            if numeric_param and numbers_lit:
                return numeric_param.format_literal_for_display(
                    numbers_lit, show_tolerance=show_tolerance, force_center=True
                )
            elif numbers_lit:
                return numbers_lit.pretty_str(show_tolerance=show_tolerance)
            else:
                return concrete_lit.pretty_str()

        def get_value(self, show_tolerance: Optional[bool] = None) -> str:
            try:
                value = self._get_value(show_tolerance=show_tolerance)
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
                F.Literals.Booleans.MakeChild_SetSuperset(
                    [out, cls.tolerance_], spec.tolerance
                )
            )
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset(
                    [out, cls.prefix_], spec.prefix
                )
            )
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset(
                    [out, cls.suffix_], spec.suffix
                )
            )
            if spec.default is not None:
                out.add_dependant(
                    F.Literals.Strings.MakeChild_SetSuperset(
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
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()

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
    def prefix(self) -> str:
        return (
            F.Parameters.StringParameter.bind_instance(
                self.prefix_.get().instance
            ).try_extract_singleton()
            or ""
        )

    @property
    def suffix(self) -> str:
        return (
            F.Parameters.StringParameter.bind_instance(
                self.suffix_.get().instance
            ).try_extract_singleton()
            or ""
        )

    @classmethod
    def MakeChild(cls, *specs: Spec):
        out = fabll._ChildField(cls)
        # TODO: trips solver
        for spec in specs:
            spec_node = cls.SpecNode.MakeChild(spec)
            out.add_dependant(spec_node)
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge(
                    [out, cls.specs_set_],
                    [spec_node],
                )
            )
        return out

    def get_value(self) -> str:
        return join_if_non_empty(
            " ",
            self.prefix,
            *[s.get_value() for s in self.specs],
            self.suffix,
        )


class TestHasSimpleValueRepresentation:
    def test_repr_chain_basic(self):
        import faebryk.library._F as F

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _TestModule(fabll.Node):
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

        m = _TestModule.bind_typegraph(tg).create_instance(g=g)
        m.param1.get().set_superset(
            g=g,
            value=F.Literals.Numbers.bind_typegraph(tg)
            .create_instance(g=g)
            .setup_from_min_max(
                min=10.0,
                max=20,
                unit=F.Units.Volt.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .is_unit.get(),
            ),
        )
        m.param2.get().set_superset(
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
        m.param3.get().set_superset(
            g=g,
            value=F.Literals.Numbers.bind_typegraph(tg)
            .create_instance(g=g)
            .setup_from_singleton(
                value=10.0,
                unit=F.Units.Volt.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .is_unit.get(),
            ),
        )

        val = m._simple_repr.get().get_value()
        assert val == "TM {10..20}V 5A P2 10V P3"

    def test_repr_with_picked_attributes(self, monkeypatch):
        from unittest.mock import Mock

        import faebryk.library._F as F
        from faebryk.libs.picker import lcsc

        # Mock lcsc.attach to avoid network calls to LCSC/EasyEDA API
        monkeypatch.setattr(lcsc, "attach", Mock())

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _TestModule(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            param1 = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
            param2 = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)

            S = has_simple_value_representation.Spec
            _simple_repr = fabll.Traits.MakeEdge(
                has_simple_value_representation.MakeChild(
                    S(param=param1, prefix="V:", tolerance=True),
                    S(param=param2, suffix="A"),
                )
            )

            # Add pickable_by_type trait so Component.attach can work
            _pickable = fabll.Traits.MakeEdge(
                F.Pickable.is_pickable_by_type.MakeChild(
                    endpoint=F.Pickable.is_pickable_by_type.Endpoint.RESISTORS,
                    params={"param1": param1, "param2": param2},
                )
            )
            _can_attach = fabll.Traits.MakeEdge(
                F.Footprints.can_attach_to_footprint.MakeChild()
            )

        m = _TestModule.bind_typegraph(tg).create_instance(g=g)

        lit1 = (
            F.Literals.Numbers.bind_typegraph(tg)
            .create_instance(g=g)
            .setup_from_center_rel(
                center=12.0,
                rel=0.05,
                unit=F.Units.Volt.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .is_unit.get(),
            )
        )
        lit2 = (
            F.Literals.Numbers.bind_typegraph(tg)
            .create_instance(g=g)
            .setup_from_singleton(
                value=2.5,
                unit=F.Units.Ampere.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .is_unit.get(),
            )
        )

        # Use Component.attach to attach the part with attributes
        from faebryk.libs.picker.api.models import Component

        # Serialize literals for component attributes
        # Filter out None values as Component expects dict[str, dict]
        attributes = {}
        for name, lit in [("param1", lit1), ("param2", lit2)]:
            serialized = lit.is_literal.get().serialize()
            if serialized is not None:
                attributes[name] = serialized

        component = Component(
            lcsc=12345,
            manufacturer_name="TestMfr",
            part_number="TestPart",
            package="0402",
            datasheet_url="",
            description="Test component",
            is_basic=0,
            is_preferred=0,
            stock=100,
            price=[],
            attributes=attributes,
        )

        # Attach the component (this will set has_part_picked and attributes)
        component.attach(
            m.get_trait(F.Pickable.is_pickable_by_type).get_trait(
                F.Pickable.is_pickable
            ),
            qty=1,
        )

        val = m._simple_repr.get().get_value()
        assert val == "V: 12±5.0%V 2.5A A"

    def test_repr_chain_non_number(self):
        import faebryk.library._F as F

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class TestEnum(Enum):
            A = "AS"
            B = "BS"

        class _TestModule(fabll.Node):
            param1 = F.Parameters.EnumParameter.MakeChild(TestEnum)
            param2 = F.Parameters.BooleanParameter.MakeChild()

            S = has_simple_value_representation.Spec
            _simple_repr = fabll.Traits.MakeEdge(
                has_simple_value_representation.MakeChild(
                    S(param=param1),
                    S(param=param2, prefix="P2:"),
                )
            )

        m = _TestModule.bind_typegraph(tg).create_instance(g=g)
        test_enum_lit = (
            F.Literals.AbstractEnums.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup(TestEnum.A)
        )
        m.param1.get().is_parameter_operatable.get().set_superset(
            g=g,
            value=test_enum_lit,
        )
        m.param2.get().set_singleton(value=True)

        val = m._simple_repr.get().get_value()
        assert val == "A P2: true"

    def test_repr_chain_no_literal(self):
        import faebryk.library._F as F

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _TestModule(fabll.Node):
            param1 = F.Parameters.NumericParameter.MakeChild(
                unit=F.Units.Volt, domain=F.NumberDomain.Args(negative=True)
            )
            param2 = F.Parameters.NumericParameter.MakeChild(
                unit=F.Units.Ampere, domain=F.NumberDomain.Args(negative=True)
            )
            param3 = F.Parameters.NumericParameter.MakeChild(
                unit=F.Units.Volt, domain=F.NumberDomain.Args(negative=True)
            )

            S = has_simple_value_representation.Spec
            _simple_repr = fabll.Traits.MakeEdge(
                has_simple_value_representation.MakeChild(
                    S(param=param1, default=None),
                    S(param=param2),
                    S(param=param3, default="P3: MISSING"),
                )
            )

        m = _TestModule.bind_typegraph(tg).create_instance(g=g)

        val = m._simple_repr.get().get_value()
        assert val == "P3: MISSING"

        m.param1.get().set_superset(
            g=g,
            value=F.Literals.Numbers.bind_typegraph(tg)
            .create_instance(g=g)
            .setup_from_singleton(
                value=10.0,
                unit=F.Units.Volt.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .is_unit.get(),
            ),
        )
        val = m._simple_repr.get().get_value()
        assert val == "10V P3: MISSING"

    def _make_kiloohm_unit(
        self, g: graph.GraphView, tg: fbrk.TypeGraph
    ) -> "F.Units.is_unit":
        from faebryk.library.Units import BasisVector, is_unit, is_unit_type

        class _Kiloohm(fabll.Node):
            unit_vector_arg = BasisVector(kilogram=1, meter=2, second=-3, ampere=-2)
            is_unit_type_trait = fabll.Traits.MakeEdge(
                is_unit_type.MakeChild(("kΩ", "kohm"), unit_vector_arg)
            ).put_on_type()
            is_unit_trait = fabll.Traits.MakeEdge(
                is_unit.MakeChild(("kΩ", "kohm"), unit_vector_arg, multiplier=1000.0)
            )
            can_be_operand = fabll.Traits.MakeEdge(
                F.Parameters.can_be_operand.MakeChild()
            )

        kohm_instance = _Kiloohm.bind_typegraph(tg=tg).create_instance(g=g)
        return kohm_instance.is_unit_trait.get()

    def test_repr_display_unit_conversion(self):
        """
        Test that values are converted to display unit (e.g., kΩ instead of Ω).
        """
        import faebryk.library._F as F

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        # Define Kiloohm unit with proper symbols
        kohm_unit = self._make_kiloohm_unit(g=g, tg=tg)

        # Create parameter with kohm as display unit
        param = F.Parameters.NumericParameter.bind_typegraph(tg).create_instance(g=g)
        param.setup(is_unit=kohm_unit)

        # Set value in base ohms (47000 ohm = 47 kohm)
        base_ohm = F.Units.Ohm.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get()
        lit = (
            F.Literals.Numbers.bind_typegraph(tg)
            .create_instance(g=g)
            .setup_from_singleton(value=47000.0, unit=base_ohm)
        )
        param.set_superset(g=g, value=lit)

        # format_literal_for_display should convert value and show correct unit
        formatted = param.format_literal_for_display(lit)

        # Should show 47kΩ (converted from 47000Ω)
        assert formatted == "47kΩ", f"Expected '47kΩ', got '{formatted}'"

    def test_resistor_value_representation(self):
        """Test that resistor value representation shows correctly formatted values.

        Note: The Resistor class uses Ohm (Ω) as the display unit, so values are shown
        in base Ohms. The literal is set in kΩ but converted to Ω for display.
        """
        import faebryk.library._F as F
        from faebryk.library.Resistor import Resistor

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        resistor = Resistor.bind_typegraph(tg=tg).create_instance(g=g)

        # Create kΩ unit for the literal value (10kΩ ±1%)
        kohm_unit = self._make_kiloohm_unit(g=g, tg=tg)

        resistor.resistance.get().set_superset(
            g=g,
            value=F.Literals.Numbers.bind_typegraph(tg)
            .create_instance(g=g)
            .setup_from_center_rel(
                center=10.0,
                rel=0.01,
                unit=kohm_unit,
            ),
        )
        resistor.max_power.get().set_superset(
            g=g,
            value=F.Literals.Numbers.bind_typegraph(tg)
            .create_instance(g=g)
            .setup_from_singleton(
                value=0.125,
                unit=F.Units.Watt.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .is_unit.get(),
            ),
        )
        resistor.max_voltage.get().set_superset(
            g=g,
            value=F.Literals.Numbers.bind_typegraph(tg)
            .create_instance(g=g)
            .setup_from_singleton(
                value=10.0,
                unit=F.Units.Volt.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .is_unit.get(),
            ),
        )
        # 10kΩ converts to 10000Ω in display units
        assert (
            resistor._simple_repr.get().get_specs()[0].get_value(show_tolerance=False)
            == "10000Ω"
        )
        # Full representation: 10000Ω ±1% plus power and voltage
        assert resistor._simple_repr.get().get_value() == "10000±1.0%Ω 0.125W 10V"
