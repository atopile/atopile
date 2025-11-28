"""
Implements a unit system and associated dimensional analysis.

All units are built on top of the SI base units, plus extensions for discrete quantities
(described below). A derived unit in this system can be modeled as a module over the
integers, represented by a vector of exponents for each of the base units, plus a
multiplier and offset to represent an affine transformation.

Dimensional properties:
- Units are commensurable if they share the same basis vector.
- An expression is dimensionally homogenous if all operands are commensurable.
- Dimensional homegeneity / commensurability is required for comparison, equation,
  addition, and subtraction of dimensional quantities.

Arithmetic:
- Unit multiplication/division map to addition/subtraction in the module, or
  element-wise addition/subtraction of the basis vectors.
- Exponentiation maps to scalar multiplication in the module, or element-wise
  multiplication of the basis vectors.
- Integration and differentiation map respectively to multiplication or division by the
  unit of the variable being integrated or differentiated with respect to, and therefore
  addition or subtraction of the involved basis vectors.

Discrete quantities:
The SI system specifies units for continuous quantities only. We extend this to include
certain discrete quantities (e.g. bits) in order to capture compatibility semantics.

Non-SI quantities:
Non-SI units are represented as affine transformations of SI units.

Angles:
Angle and solid angle (radian and steradian) dimensions are included in the basis,
contrary to the SI system, where they are dimensionless. This permits distinction
between e.g. torque and energy which would otherwise have the same basis vector.

Potential extensions to consider:
- explicit modeling of dimensions, separately from units
- support for rational exponents
- better model the distinction between affine and vector quantities
- also require orientational homogeneity when checking for commensurability

TODO:
 - add support for logarithmic units (e.g. dBSPL)
 - consider making incompatible units which differ only by context
   (e.g. Hertz and Becquerel)
 - check all `is_unit`s in compiled designs for symbol conflicts
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import reduce
from typing import Any, ClassVar, Self

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.core.zig.gen.faebryk import typegraph
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.libs.util import not_none


# Simple helper to normalize various unit-like objects to a class, defaulting to
# Dimensionless when no unit information is available.
def _unit_or_dimensionless(unit_like: Any) -> type[fabll.Node]:
    if isinstance(unit_like, fabll.TypeNodeBoundTG):
        return unit_like.t
    if isinstance(unit_like, type) and issubclass(unit_like, fabll.Node):
        return unit_like
    if isinstance(unit_like, fabll.Node):
        try:
            unit_trait = unit_like.get_trait(has_unit).get_is_unit()
            return type(unit_trait)
        except fabll.TraitNotFound:
            return Dimensionless
    if hasattr(unit_like, "get_unit"):
        return _unit_or_dimensionless(unit_like.get_unit())
    return Dimensionless


class UnitException(Exception): ...


class UnitsNotCommensurableError(UnitException):
    def __init__(self, message: str, incommensurable_items: Sequence[fabll.NodeT]):
        self.message = message
        self.incommensurable_items = incommensurable_items

    def __str__(self) -> str:
        return self.message


class UnitNotFoundError(UnitException):
    def __init__(self, symbol: str):
        self.symbol = symbol

    def __str__(self) -> str:
        return f"Unit not found: {self.symbol}"


class UnitExpressionError(UnitException): ...


@dataclass
class BasisVector:
    ampere: int = field(default=0, metadata={"display_symbol": "A"})
    second: int = field(default=0, metadata={"display_symbol": "s"})
    meter: int = field(default=0, metadata={"display_symbol": "m"})
    kilogram: int = field(default=0, metadata={"display_symbol": "kg"})
    kelvin: int = field(default=0, metadata={"display_symbol": "K"})
    mole: int = field(default=0, metadata={"display_symbol": "mol"})
    candela: int = field(default=0, metadata={"display_symbol": "cd"})
    radian: int = field(default=0, metadata={"display_symbol": "rad"})
    steradian: int = field(default=0, metadata={"display_symbol": "sr"})
    bit: int = field(default=0, metadata={"display_symbol": "bit"})

    @classmethod
    def get_symbol(cls, field_name: str) -> str:
        return cls.__dataclass_fields__[field_name].metadata["display_symbol"]

    @classmethod
    def iter_fields_and_symbols(cls) -> Sequence[tuple[str, str]]:
        return [
            (name, f.metadata["display_symbol"])
            for name, f in cls.__dataclass_fields__.items()
        ]

    def _vector_op(
        self, other: "BasisVector", op: Callable[[int, int], int]
    ) -> "BasisVector":
        return BasisVector(
            **{
                field: op(getattr(self, field), getattr(other, field))
                for field in self.__dataclass_fields__.keys()
            }
        )

    def _scalar_op(self, op: Callable[[int], int]) -> "BasisVector":
        return BasisVector(
            **{
                field: op(getattr(self, field))
                for field in self.__dataclass_fields__.keys()
            }
        )

    def add(self, other: "BasisVector") -> "BasisVector":
        return self._vector_op(other, lambda x, y: x + y)

    def subtract(self, other: "BasisVector") -> "BasisVector":
        return self._vector_op(other, lambda x, y: x - y)

    def scalar_multiply(self, scalar: int) -> "BasisVector":
        return self._scalar_op(lambda x: x * scalar)


class _BasisVector(fabll.Node):
    ORIGIN: ClassVar[BasisVector] = BasisVector()

    @classmethod
    def MakeChild(cls, vector: BasisVector) -> fabll._ChildField[Self]:  # type: ignore
        """
        Create a _BasisVector child field with exponent values set at type level.
        Each basis dimension (ampere, second, meter, etc.) is stored as a Counts child
        with a composition edge linking it to this _BasisVector node.
        """
        out = fabll._ChildField(cls)

        from faebryk.library.Literals import Counts

        for field_name in BasisVector.__dataclass_fields__.keys():
            child = Counts.MakeChild(getattr(vector, field_name))
            # Add as dependant to ensure it's created as a sibling node
            out.add_dependant(child)
            # Create composition edge to make it a child of this _BasisVector
            out.add_dependant(
                fabll.MakeEdge(
                    [out],
                    [child],
                    edge=EdgeComposition.build(child_identifier=field_name),
                )
            )
        return out

    def setup(
        self, g: graph.GraphView, tg: graph.TypeGraph, vector: BasisVector
    ) -> Self:  # type: ignore
        from faebryk.library.Literals import Counts

        for field_name in BasisVector.__dataclass_fields__.keys():
            child = Counts.bind_typegraph(tg=tg).create_instance(g=g)
            child.setup_from_values(g=g, tg=tg, values=[getattr(vector, field_name)])
            _ = EdgeComposition.add_child(
                bound_node=self.instance,
                child=child.instance.node(),
                child_identifier=field_name,
            )

        return self

    def extract_vector(self) -> BasisVector:
        from faebryk.library.Literals import Counts

        children_by_name = {
            name: child
            for name, child in self.get_direct_children()
            if name is not None
        }
        return BasisVector(
            **{
                name: children_by_name[name].cast(Counts).get_values()[0]
                for name in BasisVector.__dataclass_fields__.keys()
            }
        )


def test_basis_vector_store_and_retrieve():
    """Test that BasisVector can be stored in and retrieved from _BasisVector."""
    import faebryk.core.faebrykpy as fbrk

    # Setup graph and typegraph
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create a test vector with some non-zero exponents
    original_vector = BasisVector(
        ampere=1,
        second=-2,
        meter=3,
        kilogram=0,
        kelvin=0,
        mole=0,
        candela=0,
        radian=0,
        steradian=0,
        bit=0,
    )

    # Create a _BasisVector instance and store the vector
    basis_vector = _BasisVector.bind_typegraph(tg=tg).create_instance(g=g)
    basis_vector.setup(g=g, tg=tg, vector=original_vector)

    # Retrieve the vector and verify it matches
    retrieved_vector = basis_vector.extract_vector()

    assert retrieved_vector == original_vector, (
        f"Retrieved vector {retrieved_vector} does not match original {original_vector}"
    )


class is_base_unit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_unit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    # symbol = F.Parameters.StringParameter.MakeChild()
    """
    Symbol or symbols representing the unit. Any member of the set is valid to indicate
    the unit in ato code. Must not conflict with symbols for other units
    """

    basis_vector = F.Collections.Pointer.MakeChild()
    """
    SI base units and corresponding exponents representing a derived unit. Must consist
    of base units only.
    """

    _multiplier_identifier: ClassVar[str] = "multiplier"
    _offset_identifier: ClassVar[str] = "offset"
    _symbol_identifier: ClassVar[str] = "symbol"

    """
    Multiplier to apply when converting to SI base units.
    """

    """
    Offset to apply when converting to SI base units.
    """

    @classmethod
    def MakeChild(  # type: ignore
        cls,
        symbols: list[str],
        unit_vector: BasisVector,
        multiplier: float = 1.0,
        offset: float = 0.0,
    ) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)

        from faebryk.library.Literals import NumericInterval, Strings

        symbol_field = Strings.MakeChild(*symbols)
        out.add_dependant(symbol_field)

        out.add_dependant(
            fabll.MakeEdge(
                [out],
                [symbol_field],
                edge=EdgeComposition.build(child_identifier=cls._symbol_identifier),
            )
        )

        multiplier_field = NumericInterval.MakeChild(min=multiplier, max=multiplier)
        out.add_dependant(multiplier_field)
        out.add_dependant(
            fabll.MakeEdge(
                [out],
                [multiplier_field],
                edge=EdgeComposition.build(child_identifier=cls._multiplier_identifier),
            )
        )

        offset_field = NumericInterval.MakeChild(min=offset, max=offset)
        out.add_dependant(offset_field)
        out.add_dependant(
            fabll.MakeEdge(
                [out],
                [offset_field],
                edge=EdgeComposition.build(child_identifier=cls._offset_identifier),
            )
        )

        unit_vector_field = _BasisVector.MakeChild(unit_vector)
        out.add_dependant(unit_vector_field)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.basis_vector], [unit_vector_field])
        )

        return out

    @classmethod
    def MakeChild_Empty(cls) -> fabll._ChildField[Self]:  # type: ignore
        return fabll._ChildField(cls)

    def _extract_multiplier(self) -> float:
        multiplier_numeric = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._multiplier_identifier
        )
        assert multiplier_numeric is not None
        from faebryk.library.Literals import NumericInterval

        return NumericInterval.bind_instance(multiplier_numeric).get_value()

    def _extract_offset(self) -> float:
        offset_numeric = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._offset_identifier
        )
        assert offset_numeric is not None
        from faebryk.library.Literals import NumericInterval

        return NumericInterval.bind_instance(offset_numeric).get_value()

    def _extract_symbol(self) -> list[str]:
        symbol_field = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._symbol_identifier
        )
        assert symbol_field is not None
        from faebryk.library.Literals import Strings

        return Strings.bind_instance(symbol_field).get_values()

    def _extract_basis_vector(self) -> BasisVector:
        return _BasisVector.bind_instance(
            self.basis_vector.get().deref().instance
        ).extract_vector()

    def setup(  # type: ignore
        self,
        g: graph.GraphView,
        tg: graph.TypeGraph,
        symbols: list[str],
        unit_vector: BasisVector,
        multiplier: float = 1.0,
        offset: float = 0.0,
    ) -> Self:
        from faebryk.library.Literals import NumericInterval, Strings

        symbol = (
            Strings.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_values(*symbols)
        )
        _ = EdgeComposition.add_child(
            bound_node=self.instance,
            child=symbol.instance.node(),
            child_identifier=self._symbol_identifier,
        )
        multiplier_numeric = (
            NumericInterval.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_singleton(g=g, tg=tg, value=multiplier)
        )
        _ = EdgeComposition.add_child(
            bound_node=self.instance,
            child=multiplier_numeric.instance.node(),
            child_identifier=self._multiplier_identifier,
        )
        offset_numeric = (
            NumericInterval.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_singleton(g=g, tg=tg, value=offset)
        )
        _ = EdgeComposition.add_child(
            bound_node=self.instance,
            child=offset_numeric.instance.node(),
            child_identifier=self._offset_identifier,
        )
        basis_vector_field = (
            _BasisVector.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup(g=g, tg=tg, vector=unit_vector)
        )
        self.basis_vector.get().point(basis_vector_field)

        return self

    def get_owner_node(self) -> fabll.Node:
        """
        Get the owner node that has this IsUnit trait.
        Useful when creating new QuantitySets from unit operations.
        """
        import faebryk.core.faebrykpy as fbrk

        owner = fbrk.EdgeTrait.get_owner_node_of(bound_node=self.instance)
        assert owner is not None, "IsUnit trait must have an owner node"
        return fabll.Node.bind_instance(instance=owner)

    def get_symbols(self) -> list[str]:
        lit = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._symbol_identifier
        )
        assert lit is not None
        from faebryk.library.Literals import Strings

        lit = Strings.bind_instance(lit)
        if lit is None:
            return []
        return lit.get_values()

    @property
    def is_affine(self) -> bool:
        return self._extract_offset() != 0.0

    def is_commensurable_with(self, other: "is_unit") -> bool:
        self_vector = self._extract_basis_vector()
        other_vector = other._extract_basis_vector()
        return self_vector == other_vector

    def is_dimensionless(self) -> bool:
        return self._extract_basis_vector() == _BasisVector.ORIGIN

    def is_angular(self) -> bool:
        """
        Check if this unit is angular (radians).
        Valid input for trigonometric functions.
        Enforces explicit use of Radian unit rather than accepting dimensionless.
        """
        v = self._extract_basis_vector()
        return v == BasisVector(radian=1)

    def to_base_units(self, g: graph.GraphView, tg: graph.TypeGraph) -> "is_unit":
        """
        Returns a new anonymous unit with the same basis vector, but with multiplier=1.0
        and offset=0.0.

        Examples:
        Kilometer.to_base_units() -> Meter
        DegreesCelsius.to_base_units() -> Kelvin
        Newton.to_base_units() -> kg*m/s^-2 (anonymous)

        # TODO: lookup and return existing named unit if available
        """

        return self.new(
            g=g, tg=tg, vector=self._extract_basis_vector(), multiplier=1.0, offset=0.0
        )

    @classmethod
    def new(
        cls,
        g: graph.GraphView,
        tg: graph.TypeGraph,
        vector: BasisVector,
        multiplier: float,
        offset: float,
    ) -> "is_unit":
        # TODO: caching?
        # TODO: generate symbol
        unit = (
            _AnonymousUnit.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup(vector=vector, multiplier=multiplier, offset=offset)
        )

        return unit.get_trait(is_unit)

    def scaled_copy(
        self, g: graph.GraphView, tg: graph.TypeGraph, multiplier: float
    ) -> "is_unit":
        return self.new(
            g=g,
            tg=tg,
            vector=self._extract_basis_vector(),
            multiplier=multiplier,
            offset=self._extract_offset(),
        )

    def op_multiply(
        self, g: graph.GraphView, tg: graph.TypeGraph, other: "is_unit"
    ) -> "is_unit":
        v1, v2 = self._extract_basis_vector(), other._extract_basis_vector()
        m1, m2 = self._extract_multiplier(), other._extract_multiplier()

        new_multiplier = m1 * m2
        new_vector = v1.add(v2)

        return self.new(
            g=g,
            tg=tg,
            vector=new_vector,
            multiplier=new_multiplier,
            offset=0.0,  # TODO
        )

    def op_divide(
        self, g: graph.GraphView, tg: graph.TypeGraph, other: "is_unit"
    ) -> "is_unit":
        v1, v2 = self._extract_basis_vector(), other._extract_basis_vector()
        m1, m2 = self._extract_multiplier(), other._extract_multiplier()

        new_multiplier = m1 / m2
        new_vector = v1.subtract(v2)

        return self.new(
            g=g,
            tg=tg,
            vector=new_vector,
            multiplier=new_multiplier,
            offset=0.0,  # TODO
        )

    def op_invert(self, g: graph.GraphView, tg: graph.TypeGraph) -> "is_unit":
        v = self._extract_basis_vector()
        m = self._extract_multiplier()
        return self.new(
            g=g,
            tg=tg,
            vector=v.scalar_multiply(-1),
            multiplier=1.0 / m,
            offset=0.0,
        )

    def op_power(
        self, g: graph.GraphView, tg: graph.TypeGraph, exponent: int
    ) -> "is_unit":
        v = self._extract_basis_vector()
        m = self._extract_multiplier()
        return self.new(
            g=g,
            tg=tg,
            vector=v.scalar_multiply(exponent),
            multiplier=m**exponent,
            offset=0.0,  # TODO
        )

    def get_conversion_to(self, target: "is_unit") -> tuple[float, float]:
        if not self.is_commensurable_with(target):
            raise UnitsNotCommensurableError(
                f"Units {self} and {target} are not commensurable",
                incommensurable_items=[self, target],
            )

        m1, o1 = self._extract_multiplier(), self._extract_offset()
        m2, o2 = target._extract_multiplier(), target._extract_offset()

        scale = m1 / m2
        offset = (o1 - o2) / m2

        return (scale, offset)

    def compact_repr(self) -> str:
        if symbols := self._extract_symbol():
            return symbols[0]

        vector = self._extract_basis_vector()
        multiplier = self._extract_multiplier()
        offset = self._extract_offset()

        parts = []
        for dim_name, symbol in BasisVector.iter_fields_and_symbols():
            exp = getattr(vector, dim_name)
            if exp != 0:
                parts.append(f"{symbol}^{exp}" if exp != 1 else symbol)

        result = "·".join(parts) if parts else "1"

        if multiplier != 1.0:
            result = f"{multiplier}×{result}"

        if offset != 0.0:
            result = f"({result}+{offset})"

        return result


class is_si_prefixed_unit(fabll.Node):
    SI_PREFIXES: ClassVar[dict[str, float]] = {
        "Q": 10**30,  # quetta
        "R": 10**27,  # ronna
        "Y": 10**24,  # yotta
        "Z": 10**21,  # zetta
        "E": 10**18,  # exa
        "P": 10**15,  # peta
        "T": 10**12,  # tera
        "G": 10**9,  # giga
        "M": 10**6,  # mega
        "k": 10**3,  # kilo
        "h": 10**2,  # hecto
        "da": 10**1,  # deca
        "d": 10**-1,  # deci
        "c": 10**-2,  # centi
        "m": 10**-3,  # milli
        "u": 10**-6,  # micro
        "µ": 10**-6,  # micro
        "n": 10**-9,  # nano
        "p": 10**-12,  # pico
        "f": 10**-15,  # femto
        "a": 10**-18,  # atto
        "z": 10**-21,  # zepto
        "y": 10**-24,  # yocto
        "r": 10**-27,  # ronto
        "q": 10**-30,  # quecto
    }

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_binary_prefixed_unit(fabll.Node):
    BINARY_PREFIXES: ClassVar[dict[str, float]] = {
        "Ki": 2**20,  # kibi
        "Mi": 2**20,  # mebi
        "Gi": 2**30,  # gibi
        "Ti": 2**40,  # tebi
        "Pi": 2**50,  # pebi
        "Ei": 2**60,  # exbi
        "Zi": 2**70,  # zebi
        "Yi": 2**80,  # yobi
    }

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


def decode_symbol(g: graph.GraphView, tg: typegraph.TypeGraph, symbol: str) -> is_unit:
    # TODO: caching
    # TODO: optimisation: pre-compute symbol map; build suffix trie

    all_units = fabll.Traits.get_implementors(is_unit.bind_typegraph(tg), g)
    symbol_map = {s: unit for unit in all_units for s in unit.get_symbols()}

    # 1. Exact match
    if symbol in symbol_map:
        return symbol_map[symbol]

    # 2. Prefixed
    for known_symbol in symbol_map.keys():
        if symbol.endswith(known_symbol):
            prefix = symbol.removesuffix(known_symbol)
            unit = symbol_map[known_symbol]
            parent, _ = unit.get_parent_force()

            if (
                parent.has_trait(is_si_prefixed_unit)
                and prefix in is_si_prefixed_unit.SI_PREFIXES
            ):
                scale_factor = is_si_prefixed_unit.SI_PREFIXES[prefix]
            elif (
                parent.has_trait(is_binary_prefixed_unit)
                and prefix in is_binary_prefixed_unit.BINARY_PREFIXES
            ):
                scale_factor = is_binary_prefixed_unit.BINARY_PREFIXES[prefix]
            else:
                continue

            return unit.scaled_copy(g=g, tg=tg, multiplier=scale_factor)

    raise UnitNotFoundError(symbol)


class is_si_unit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class has_unit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    unit = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(cls, unit: type[fabll.NodeT]) -> fabll._ChildField[Self]:  # type: ignore
        out = fabll._ChildField(cls)
        unit_field = unit.MakeChild()
        out.add_dependant(unit_field)
        out.add_dependant(F.Collections.Pointer.MakeEdge([out, cls.unit], [unit_field]))
        return out

    def setup(self, g: graph.GraphView, unit: fabll.Node) -> Self:  # type: ignore
        self.unit.get().point(unit)
        return self

    def get_is_unit(self) -> is_unit:
        return self.unit.get().deref().get_trait(is_unit)


UnitVectorT = list[tuple[type[fabll.Node], int]]


class is_unit_expression(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class UnitExpression(fabll.Node):
    # TODO: tie to NewUnitExpression fields
    _is_unit_expression = fabll.Traits.MakeEdge(is_unit_expression.MakeChild())
    expr = F.Collections.Pointer.MakeChild()
    multiplier = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits()
    offset = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits()

    def get_expr(self) -> fabll.Node:
        return self.expr.get().deref()

    def get_multiplier(self) -> float:
        multiplier_lit = self.multiplier.get().try_extract_aliased_literal()
        return not_none(multiplier_lit).get_value()

    def get_offset(self) -> float:
        offset_lit = self.offset.get().try_extract_aliased_literal()
        return not_none(offset_lit).get_value()


def make_unit_expression_type(
    unit_vector: UnitVectorT, multiplier: float = 1.0, offset: float = 0.0
) -> type[fabll.Node]:
    from faebryk.library.Expressions import Multiply, Power

    class NewUnitExpression(fabll.Node):
        _is_unit_expression = fabll.Traits.MakeEdge(is_unit_expression.MakeChild())

        expr = F.Collections.Pointer.MakeChild()
        multiplier = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits()
        offset = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits()

        @classmethod
        def MakeChild(cls) -> fabll._ChildField[Self]:  # type: ignore
            out = fabll._ChildField(cls)
            term_fields = []

            for unit, exponent in unit_vector:
                unit_field = unit.MakeChild()
                out.add_dependant(unit_field)

                exponent_field = (
                    F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(
                        integer=True
                    )
                )
                out.add_dependant(exponent_field)
                # Exponent is a dimensionless integer value for unit exponentiation
                exponent_lit = F.Literals.Numbers.MakeChild(
                    min=exponent, max=exponent, unit=Dimensionless
                )
                exponent_is_expr = F.Expressions.Is.MakeChild_Constrain(
                    [[exponent_field], [exponent_lit]]
                )
                exponent_is_expr.add_dependant(
                    exponent_lit, identifier="lit", before=True
                )
                out.add_dependant(exponent_is_expr)

                term_field = Power.MakeChild_FromOperands(unit_field, exponent_field)
                out.add_dependant(term_field)
                term_fields.append(term_field)

            expr_field = Multiply.MakeChild_FromOperands(*term_fields)
            out.add_dependant(expr_field)
            out.add_dependant(
                F.Collections.Pointer.MakeEdge([out, cls.expr], [expr_field])
            )
            from faebryk.library.Literals import Numbers

            multiplier_lit = Numbers.MakeChild(
                min=multiplier, max=multiplier, unit=Dimensionless
            )
            multiplier_is_expr = F.Expressions.Is.MakeChild_Constrain(
                [[out, cls.multiplier], [multiplier_lit]]
            )
            multiplier_is_expr.add_dependant(
                multiplier_lit, identifier="lit", before=True
            )
            out.add_dependant(multiplier_is_expr)

            offset_lit = Numbers.MakeChild(min=offset, max=offset, unit=Dimensionless)
            offset_is_expr = F.Expressions.Is.MakeChild_Constrain(
                [[out, cls.offset], [offset_lit]]
            )
            offset_is_expr.add_dependant(offset_lit, identifier="lit", before=True)
            out.add_dependant(offset_is_expr)

            return out

    unit_vector_str = "".join(
        f"{unit.__name__}^{exponent}" for unit, exponent in unit_vector
    )
    NewUnitExpression.__name__ = f"UnitExpression<{unit_vector_str}>"

    return NewUnitExpression


class _AnonymousUnit(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(is_unit.MakeChild_Empty())

    def setup(  # type: ignore
        self, vector: BasisVector, multiplier: float = 1.0, offset: float = 0.0
    ) -> Self:
        self._is_unit.get().setup(
            g=self.instance.g(),
            tg=self.tg,
            symbols=[],
            unit_vector=vector,
            multiplier=multiplier,
            offset=offset,
        )

        return self


class _UnitExpressionResolver:
    def __init__(self, g: graph.GraphView, tg: graph.TypeGraph):
        self.g = g
        self.tg = tg

    def visit(self, node: fabll.Node) -> is_unit:
        if unit := node.try_get_trait(is_unit):
            if unit.is_affine:
                raise UnitExpressionError(
                    "Cannot use affine unit in compound expression"
                )
            return unit

        if node.isinstance(F.Expressions.Multiply):
            return self.visit_multiply(node.cast(F.Expressions.Multiply))
        elif node.isinstance(F.Expressions.Divide):
            return self.visit_divide(node.cast(F.Expressions.Divide))
        elif node.isinstance(F.Expressions.Power):
            return self.visit_power(node.cast(F.Expressions.Power))
        elif node.has_trait(is_unit_expression):
            return self.visit_unit_expression(
                node.cast(
                    UnitExpression,
                    # originally a NewUnitExpression, but the fields should match
                    check=False,
                )
            )

        raise UnitExpressionError(
            f"Unsupported expression type: {node.get_type_name()}"
        )

    def visit_unit_expression(self, node: UnitExpression) -> is_unit:
        """Resolve a UnitExpression by traversing its expression tree."""

        multiplier = node.get_multiplier()
        offset = node.get_offset()

        if offset != 0.0:
            # TODO: document affine unit limitations
            raise UnitExpressionError("Cannot use unit expression with non-zero offset")

        inner_unit = self.visit(node.get_expr())
        inner_vector = inner_unit._extract_basis_vector()
        inner_multiplier = inner_unit._extract_multiplier()

        return is_unit.new(
            g=self.g,
            tg=self.tg,
            vector=inner_vector,
            multiplier=multiplier * inner_multiplier,
            offset=0.0,
        )

    def visit_multiply(self, node: F.Expressions.Multiply) -> is_unit:
        operands = node.operands.get().as_list()

        if not operands:
            return is_unit.new(
                g=self.g,
                tg=self.tg,
                vector=_BasisVector.ORIGIN,
                multiplier=1.0,
                offset=0.0,
            ).get_trait(is_unit)

        return reduce(
            lambda a, b: a.op_multiply(self.g, self.tg, b),
            (self.visit(op) for op in operands),
        )

    def visit_divide(self, node: F.Expressions.Divide) -> is_unit:
        return reduce(
            lambda a, b: a.op_divide(self.g, self.tg, b),
            (
                self.visit(op)
                for op in (
                    node.numerator.get().deref(),
                    *node.denominator.get().as_list(),
                )
            ),
        )

    def visit_power(self, node: F.Expressions.Power) -> is_unit:
        base = node.base.get().deref()
        exponent_node = node.exponent.get().deref()

        exponent_lit = (
            not_none(exponent_node.try_get_trait(F.Parameters.is_parameter_operatable))
            .force_extract_literal()
            .switch_cast()
        )

        if not exponent_lit.isinstance(F.Literals.Numbers):
            raise UnitExpressionError(
                f"Unit exponent must be numeric, got {exponent_lit.get_type_name()}"
            )

        exponent_val = exponent_lit.cast(F.Literals.Numbers).get_value()

        if not float(exponent_val).is_integer():
            raise UnitExpressionError(
                f"Unit exponent must be integer, got {exponent_val}"
            )

        return self.visit(base).op_power(self.g, self.tg, int(exponent_val))


def resolve_unit_expression(
    g: graph.GraphView, tg: graph.TypeGraph, expr: graph.BoundNode
) -> fabll.Node:
    # TODO: caching?
    resolver = _UnitExpressionResolver(g=g, tg=tg)
    node = fabll.Node.bind_instance(expr)
    result_unit = resolver.visit(node)
    parent, _ = result_unit.get_parent_force()
    return parent


class _UnitRegistry(Enum):
    # TODO: check all `is_unit`s in design for symbol conflicts

    Dimensionless = auto()

    # Scalar multiples
    Percent = auto()
    Ppm = auto()

    # SI base units
    Ampere = auto()
    Second = auto()
    Meter = auto()
    Kilogram = auto()
    Kelvin = auto()
    Mole = auto()
    Candela = auto()

    # SI derived units
    Radian = auto()
    Steradian = auto()
    Hertz = auto()
    Newton = auto()
    Pascal = auto()
    Joule = auto()
    Watt = auto()
    Coulomb = auto()
    Volt = auto()
    Farad = auto()
    Ohm = auto()
    Siemens = auto()
    Weber = auto()
    Tesla = auto()
    Henry = auto()
    DegreeCelsius = auto()
    Lumen = auto()
    Lux = auto()
    Becquerel = auto()
    Gray = auto()
    Sievert = auto()
    Katal = auto()

    # SI patches
    Gram = auto()

    # non-SI units
    Bit = auto()
    Byte = auto()

    # non-SI multiples

    # angles
    Degree = auto()
    ArcMinute = auto()
    ArcSecond = auto()

    # time
    Minute = auto()
    Hour = auto()
    Day = auto()
    Week = auto()
    Month = auto()
    Year = auto()

    # volume
    Liter = auto()

    # angular frequency
    RPM = auto()


_UNIT_SYMBOLS: dict[_UnitRegistry, list[str]] = {
    _UnitRegistry.Dimensionless: ["dimensionless"],  # TODO: allow None?
    _UnitRegistry.Percent: ["%"],
    _UnitRegistry.Ppm: ["ppm"],
    _UnitRegistry.Ampere: ["A"],
    _UnitRegistry.Second: ["s"],
    _UnitRegistry.Meter: ["m"],
    _UnitRegistry.Kilogram: ["kg"],
    _UnitRegistry.Kelvin: ["K"],
    _UnitRegistry.Mole: ["mol"],
    _UnitRegistry.Candela: ["cd"],
    _UnitRegistry.Radian: ["rad"],
    _UnitRegistry.Steradian: ["sr"],
    _UnitRegistry.Hertz: ["Hz"],
    _UnitRegistry.Newton: ["N"],
    _UnitRegistry.Pascal: ["Pa"],
    _UnitRegistry.Joule: ["J"],
    _UnitRegistry.Watt: ["W"],
    _UnitRegistry.Coulomb: ["C"],
    _UnitRegistry.Volt: ["V"],
    _UnitRegistry.Farad: ["F"],
    _UnitRegistry.Ohm: ["Ω", "Ohm"],
    _UnitRegistry.Siemens: ["S"],
    _UnitRegistry.Weber: ["Wb"],
    _UnitRegistry.Tesla: ["T"],
    _UnitRegistry.Henry: ["H"],
    _UnitRegistry.DegreeCelsius: ["°C"],
    _UnitRegistry.Lumen: ["lm"],
    _UnitRegistry.Lux: ["lx"],
    _UnitRegistry.Becquerel: ["Bq"],
    _UnitRegistry.Gray: ["Gy"],
    _UnitRegistry.Sievert: ["Sv"],
    _UnitRegistry.Katal: ["kat"],
    _UnitRegistry.Bit: ["bit"],
    _UnitRegistry.Byte: ["byte"],
    _UnitRegistry.Gram: ["g"],
    _UnitRegistry.Degree: ["°", "deg"],
    _UnitRegistry.ArcMinute: ["arcmin"],
    _UnitRegistry.ArcSecond: ["arcsec"],
    _UnitRegistry.Minute: ["min"],
    _UnitRegistry.Day: ["day"],
    _UnitRegistry.Hour: ["hour"],
    _UnitRegistry.Week: ["week"],
    _UnitRegistry.Month: ["month"],
    _UnitRegistry.Year: ["year"],
    _UnitRegistry.Liter: ["liter"],
    _UnitRegistry.RPM: ["rpm", "RPM"],
}


# Dimensionless ------------------------------------------------------------------------


# TODO: rename to One?
class Dimensionless(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = _BasisVector.ORIGIN

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Dimensionless], unit_vector_arg)
    )


# SI base units ------------------------------------------------------------------------


class Ampere(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(ampere=1)

    _is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Ampere], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Meter(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=1)

    _is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Meter], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Kilogram(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1)

    _is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Kilogram], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())


class Second(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    _is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Second], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Kelvin(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kelvin=1)

    _is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Kelvin], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Mole(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(mole=1)

    _is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Mole], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Candela(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(candela=1)

    _is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Candela], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# SI coherent derived units ------------------------------------------------------------


class Radian(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Radian], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Steradian(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(steradian=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Steradian], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Hertz(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=-1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Hertz], unit_vector_arg)
    )
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Newton(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1, meter=1, second=-2)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Newton], unit_vector_arg)
    )
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Pascal(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=-1, second=-2
    )

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Pascal], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Joule(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1, meter=2, second=-2)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Joule], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Watt(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1, meter=2, second=-3)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Watt], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Coulomb(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(ampere=1, second=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Coulomb], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Volt(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-3, ampere=-1
    )

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Volt], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Farad(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=-1, meter=-2, second=4, ampere=2
    )

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Farad], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Ohm(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-3, ampere=-2
    )

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Ohm], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Siemens(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=-1, meter=-2, second=3, ampere=2
    )

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Siemens], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Weber(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-2, ampere=-1
    )

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Weber], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Tesla(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, second=-2, ampere=-1
    )

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Tesla], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Henry(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-2, ampere=-2
    )

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Henry], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class DegreeCelsius(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kelvin=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.DegreeCelsius],
            unit_vector_arg,
            offset=273.15,
        )
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Lumen(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(candela=1, steradian=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Lumen], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Lux(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        candela=1, steradian=1, meter=-2
    )

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Lux], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# TODO: prevent mixing with Hertz via context/domain tagging system?
class Becquerel(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=-1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Becquerel], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Gray(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=2, second=-2)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Gray], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Sievert(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=2, second=-2)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Sievert], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Katal(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(mole=1, second=-1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Katal], unit_vector_arg)
    )
    _is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# SI patches ---------------------------------------------------------------------------


class Gram(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Gram], unit_vector_arg, multiplier=1e-3
        )
    )
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# non-SI base units --------------------------------------------------------------------


class Bit(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(bit=1)

    _is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Bit], unit_vector_arg)
    )
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())
    _is_binary_prefixed = fabll.Traits.MakeEdge(is_binary_prefixed_unit.MakeChild())


# Dimensionless scalar multiples -------------------------------------------------------


class Percent(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = _BasisVector.ORIGIN

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Percent], unit_vector_arg, multiplier=1e-2
        )
    )


class Ppm(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = _BasisVector.ORIGIN

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ppm], unit_vector_arg, multiplier=1e-6
        )
    )


# Common non-SI multiples --------------------------------------------------------------


class Degree(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kelvin=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Degree],
            unit_vector_arg,
            multiplier=math.pi / 180.0,
        )
    )


class Minute(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Minute], unit_vector_arg, multiplier=60.0
        )
    )


class Hour(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Hour], unit_vector_arg, multiplier=3600.0
        )
    )


class Day(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Day], unit_vector_arg, multiplier=24 * 3600.0
        )
    )


class Week(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Week],
            unit_vector_arg,
            multiplier=7 * 24 * 3600.0,
        )
    )


class Month(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Month],
            unit_vector_arg,
            multiplier=(365.25 / 12) * 24 * 3600.0,
        )
    )


class Year(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Year],
            unit_vector_arg,
            multiplier=365.25 * 24 * 3600.0,
        )
    )


class Liter(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=3)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Liter], unit_vector_arg, multiplier=1e-3
        )
    )
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class RPM(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1, second=-1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.RPM],
            unit_vector_arg,
            multiplier=(2 * math.pi) / 60.0,
        )
    )


class Byte(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(bit=1)

    _is_unit = is_unit.MakeChild(
        _UNIT_SYMBOLS[_UnitRegistry.Byte], unit_vector_arg, multiplier=8.0
    )
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())
    _is_binary_prefixed = fabll.Traits.MakeEdge(is_binary_prefixed_unit.MakeChild())


# Shortcuts for use elsewhere in the standard library ---------------------------------


class BitsPerSecond(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(bit=1, second=-1)

    _is_unit = fabll.Traits.MakeEdge(is_unit.MakeChild([], unit_vector_arg))
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())
    _is_binary_prefixed = fabll.Traits.MakeEdge(is_binary_prefixed_unit.MakeChild())


class AmpereHour(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(ampere=1, second=1)

    _is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild([], unit_vector_arg, multiplier=3600.0)
    )
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


VoltsPerSecond = make_unit_expression_type([(Volt, 1), (Second, -1)])

# Logarithmic units --------------------------------------------------------------------
# TODO: logarithmic units
