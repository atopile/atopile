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
from dataclasses import dataclass, field, fields
from enum import Enum, auto
from functools import reduce
from typing import ClassVar, Self, cast

import pytest
from dataclasses_json import DataClassJsonMixin

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.util import not_none, once


class UnitException(Exception): ...


class UnitsNotCommensurableError(UnitException):
    def __init__(
        self, message: str, incommensurable_items: Sequence[fabll.NodeT] | None = None
    ):
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
class BasisVector(DataClassJsonMixin):
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


@dataclass(frozen=True)
class UnitInfo:
    basis_vector: BasisVector
    multiplier: float
    offset: float

    def op_power(self, exponent: int) -> "UnitInfo":
        return UnitInfo(
            basis_vector=self.basis_vector.scalar_multiply(exponent),
            multiplier=self.multiplier**exponent,
            offset=self.offset,
        )

    def op_multiply(self, other: "UnitInfo") -> "UnitInfo":
        if self.offset != 0.0 or other.offset != 0.0:
            raise UnitExpressionError("Cannot use unit expression with non-zero offset")

        return UnitInfo(
            basis_vector=self.basis_vector.add(other.basis_vector),
            multiplier=self.multiplier * other.multiplier,
            offset=self.offset + other.offset,
        )

    def is_commensurable_with(self, other: "UnitInfo") -> bool:
        return self.basis_vector == other.basis_vector

    def convert_value(self, value: float, value_unit_info: "UnitInfo") -> float:
        if not self.is_commensurable_with(value_unit_info):
            raise UnitsNotCommensurableError(
                f"Units {self} and {value_unit_info} are not commensurable"
            )
        scale = value_unit_info.multiplier / self.multiplier
        offset = value_unit_info.offset - self.offset
        return value * scale + offset


class _BasisVector(fabll.Node):
    ORIGIN: ClassVar[BasisVector] = BasisVector()

    @classmethod
    def MakeChild(cls, vector: BasisVector) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
        """
        Create a _BasisVector child field with exponent values set at type level.
        Each basis dimension (ampere, second, meter, etc.) is stored as a Counts child
        linked to this _BasisVector node's fields pointer set.
        """
        out = fabll._ChildField(cls)

        from faebryk.library.Literals import Counts

        for f in fields(BasisVector):
            child = Counts.MakeChild(getattr(vector, f.name))
            out.add_dependant(child)
            out.add_dependant(F.Collections.Pointer.MakeEdge([out, f.name], [child]))
        return out

    def setup(  # type: ignore[invalid-method-override]
        self, vector: BasisVector
    ) -> Self:
        from faebryk.library.Literals import Counts

        g = self.g
        tg = self.tg

        for f in fields(BasisVector):
            child = (
                Counts.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .setup_from_values(values=[getattr(vector, f.name)])
            )
            getattr(self, f.name).get().point(child)

        return self

    def extract_vector(self) -> BasisVector:
        from faebryk.library.Literals import Counts

        field_counts = {
            cast(fabll.Node, pointer).get_name(): cast(
                F.Collections.PointerProtocol, pointer
            )
            .deref()
            .cast(Counts)
            .get_single()
            for pointer in self.get_children(
                direct_only=True,
                types=F.Collections.Pointer,  # type: ignore[arg-type]
            )
        }
        assert field_counts
        return BasisVector(**field_counts)


for f in fields(BasisVector):
    _BasisVector._add_field(f.name, F.Collections.Pointer.MakeChild())


class TestBasisVector:
    def test_basis_vector_store_and_retrieve(self):
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
        basis_vector.setup(vector=original_vector)

        # Retrieve the vector and verify it matches
        retrieved_vector = basis_vector.extract_vector()

        assert retrieved_vector == original_vector, (
            f"Retrieved vector {retrieved_vector} does not match original"
            f" {original_vector}"
        )


class is_base_unit(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_unit_type(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    symbol_ptr = F.Collections.Pointer.MakeChild()
    basis_vector = F.Collections.Pointer.MakeChild()
    multiplier_ptr = F.Collections.Pointer.MakeChild()
    offset_ptr = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(  # type: ignore[invalid-method-override]
        cls,
        symbols: tuple[str, ...],
        basis_vector: BasisVector | None = None,
        multiplier: float | None = None,
        offset: float = 0.0,
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)

        from faebryk.library.Literals import NumericInterval, Strings

        symbol_field = Strings.MakeChild(*symbols)
        out.add_dependant(symbol_field)

        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.symbol_ptr], [symbol_field])
        )

        if multiplier:
            multiplier_field = NumericInterval.MakeChild(min=multiplier, max=multiplier)
            out.add_dependant(multiplier_field)
            out.add_dependant(
                F.Collections.Pointer.MakeEdge(
                    [out, cls.multiplier_ptr], [multiplier_field]
                )
            )

        offset_field = NumericInterval.MakeChild(min=offset, max=offset)
        out.add_dependant(offset_field)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.offset_ptr], [offset_field])
        )

        if basis_vector:
            basis_vector_field = _BasisVector.MakeChild(basis_vector)
            out.add_dependant(basis_vector_field)
            out.add_dependant(
                F.Collections.Pointer.MakeEdge(
                    [out, cls.basis_vector], [basis_vector_field]
                )
            )

        return out

    def get_symbols(self) -> list[str]:
        lit = self.symbol_ptr.get().deref().instance
        assert lit is not None
        from faebryk.library.Literals import Strings

        lit = Strings.bind_instance(lit)
        if lit is None:
            return []
        return lit.get_values()

    def get_basis_vector(self) -> BasisVector:
        return _BasisVector.bind_instance(
            self.basis_vector.get().deref().instance
        ).extract_vector()


class is_unit(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    symbol_ptr = F.Collections.Pointer.MakeChild()
    """
    Symbol or symbols representing the unit. Any member of the set is valid to indicate
    the unit in ato code. Must not conflict with symbols for other units
    """

    basis_vector = F.Collections.Pointer.MakeChild()
    """
    SI base units and corresponding exponents representing a derived unit. Must consist
    of base units only.
    """

    multiplier_ptr = F.Collections.Pointer.MakeChild()
    """
    Multiplier to apply when converting to SI base units.
    """

    offset_ptr = F.Collections.Pointer.MakeChild()
    """
    Offset to apply when converting to SI base units.
    """

    @classmethod
    def MakeChild(  # type: ignore[invalid-method-override]
        cls,
        symbols: tuple[str, ...],
        basis_vector: BasisVector,
        multiplier: float = 1.0,
        offset: float = 0.0,
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)

        from faebryk.library.Literals import NumericInterval, Strings

        symbol_field = Strings.MakeChild(*symbols)
        out.add_dependant(symbol_field)

        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.symbol_ptr], [symbol_field])
        )

        multiplier_field = NumericInterval.MakeChild(min=multiplier, max=multiplier)
        out.add_dependant(multiplier_field)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.multiplier_ptr], [multiplier_field]
            )
        )

        offset_field = NumericInterval.MakeChild(min=offset, max=offset)
        out.add_dependant(offset_field)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.offset_ptr], [offset_field])
        )

        basis_vector_field = _BasisVector.MakeChild(basis_vector)
        out.add_dependant(basis_vector_field)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.basis_vector], [basis_vector_field]
            )
        )

        return out

    @classmethod
    def MakeChild_Empty(cls) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
        return fabll._ChildField(cls)

    def _extract_multiplier(self) -> float:
        multiplier_numeric = self.multiplier_ptr.get().try_deref()
        if multiplier_numeric is None:  # TODO: Pointer never set, assume default
            return 1.0
        from faebryk.library.Literals import NumericInterval

        return NumericInterval.bind_instance(multiplier_numeric.instance).get_single()

    def _extract_offset(self) -> float:
        offset_numeric = self.offset_ptr.get().deref()
        assert offset_numeric is not None
        from faebryk.library.Literals import NumericInterval

        return NumericInterval.bind_instance(offset_numeric.instance).get_single()

    def _extract_symbols(self) -> list[str]:
        symbol_field = self.symbol_ptr.get().deref()
        assert symbol_field is not None
        from faebryk.library.Literals import Strings

        return Strings.bind_instance(symbol_field.instance).get_values()

    def _extract_basis_vector(self) -> BasisVector:
        return _BasisVector.bind_instance(
            self.basis_vector.get().deref().instance
        ).extract_vector()

    def setup(  # type: ignore[invalid-method-override]
        self,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
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
        self.symbol_ptr.get().point(symbol)
        multiplier_numeric = (
            NumericInterval.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_singleton(value=multiplier)
        )
        self.multiplier_ptr.get().point(multiplier_numeric)
        offset_numeric = (
            NumericInterval.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_singleton(value=offset)
        )
        self.offset_ptr.get().point(offset_numeric)
        basis_vector_field = (
            _BasisVector.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup(vector=unit_vector)
        )
        self.basis_vector.get().point(basis_vector_field)

        return self

    def get_owner_node(self) -> fabll.Node:
        """
        Get the owner node that has this is_unit trait.
        Useful when creating new QuantitySets from unit operations.
        """
        import faebryk.core.faebrykpy as fbrk

        owner = fbrk.EdgeTrait.get_owner_node_of(bound_node=self.instance)
        assert owner is not None, "is_unit trait must have an owner node"
        return fabll.Node.bind_instance(instance=owner)

    def get_symbols(self) -> list[str]:
        lit = self.symbol_ptr.get().deref().instance
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

    def to_base_units(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "is_unit":
        """
        Returns a new anonymous unit with the same basis vector, but with multiplier=1.0
        and offset=0.0.

        Examples:
        Kilometer.to_base_units() -> Meter
        DegreesCelsius.to_base_units() -> Kelvin
        Newton.to_base_units() -> kg*m/s^-2 (anonymous)

        # TODO: lookup and return existing named unit if available
        """
        all_is_units = fabll.Traits.get_implementors(is_unit.bind_typegraph(tg=tg), g)
        for _is_unit in all_is_units:
            # Must match basis vector AND have base unit multiplier/offset
            if (
                _is_unit._extract_basis_vector() == self._extract_basis_vector()
                and _is_unit._extract_multiplier() == 1.0
                and _is_unit._extract_offset() == 0.0
            ):
                return _is_unit

        return self.new(
            g=g, tg=tg, vector=self._extract_basis_vector(), multiplier=1.0, offset=0.0
        )

    @classmethod
    def new(
        cls,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        vector: BasisVector,
        multiplier: float,
        offset: float,
    ) -> "is_unit":
        # TODO: caching?
        # TODO: generate symbol

        return (
            AnonymousUnitFactory(vector=vector, multiplier=multiplier, offset=offset)
            .bind_typegraph(tg=tg)
            .create_instance(g=g)
            .cast(_AnonymousUnit, check=False)
            .get_is_unit()
        )

    def scaled_copy(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, multiplier: float
    ) -> "is_unit":
        return self.new(
            g=g,
            tg=tg,
            vector=self._extract_basis_vector(),
            multiplier=multiplier * self._extract_multiplier(),
            offset=self._extract_offset(),
        )

    def op_multiply(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "is_unit"
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
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "is_unit"
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

    def op_invert(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "is_unit":
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
        self, g: graph.GraphView, tg: fbrk.TypeGraph, exponent: int
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
        """Return compact unit repr (symbol or basis vector with multipliers)."""

        def to_superscript(n: int) -> str:
            """Convert an integer to Unicode superscript characters."""
            superscript_map = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
            return str(n).translate(superscript_map)

        def format_number(value: float) -> str:
            """Format a number without unnecessary trailing zeros."""
            if value == int(value):
                return str(int(value))
            return f"{value:g}"

        # use the first pre-defined symbol if available
        if symbols := self._extract_symbols():
            return symbols[0]

        # otherwise, render the basis vector
        vector = self._extract_basis_vector()
        multiplier = self._extract_multiplier()
        offset = self._extract_offset()

        result = "·".join(
            [
                f"{symbol}{to_superscript(exp)}" if exp != 1 else symbol
                for dim_name, symbol in BasisVector.iter_fields_and_symbols()
                if (exp := getattr(vector, dim_name)) != 0
            ]
        )

        if multiplier != 1.0:
            mult_str = format_number(multiplier)
            result = f"{mult_str}×{result}" if result else mult_str

        if offset != 0.0:
            result = f"({result}+{format_number(offset)})"

        return result

    def serialize(self) -> dict | str:
        """
        Serialize this unit to a dictionary.

        Returns a dict matching the component API format:
        {
            "symbols": ["symbol1", "symbol2"],
            "basis_vector": {"
                "ampere": 0,
                "second": 0,
                "meter": 0,
                "kilogram": 0,
                "kelvin": 0,
                "mole": 0,
                "candela": 0,
                "radian": 0,
                "steradian": 0,
                "bit": 0,
            },
            "multiplier": 1.0,
            "offset": 0.0,
        }
        """
        if symbols := self._extract_symbols():
            return symbols[0]

        out = {}
        basis_vector = self._extract_basis_vector()
        multiplier = self._extract_multiplier()
        offset = self._extract_offset()

        out["symbols"] = symbols
        out["basis_vector"] = basis_vector.to_dict()
        out["multiplier"] = multiplier
        out["offset"] = offset

        return out


class is_si_unit(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class has_unit(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    is_unit_ptr = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(cls, unit: fabll.RefPath) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
        out = fabll._ChildField(cls)
        # TODO: improve by removing string reference
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.is_unit_ptr], [*unit, "is_unit"])
        )
        return out

    def setup(self, is_unit: "is_unit") -> Self:  # type: ignore[invalid-method-override]
        self.is_unit_ptr.get().point(is_unit)
        return self

    def get_is_unit(self) -> "is_unit":
        return self.is_unit_ptr.get().deref().cast(is_unit)


class has_display_unit(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    is_unit_ptr = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(cls, unit: fabll.RefPath) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.is_unit_ptr], [*unit, "is_unit"])
        )
        return out

    def setup(self, is_unit: "is_unit") -> Self:  # type: ignore[invalid-method-override]
        self.is_unit_ptr.get().point(is_unit)
        return self

    def get_is_unit(self) -> "is_unit":
        return self.is_unit_ptr.get().deref().cast(is_unit)


class is_si_prefixed_unit(fabll.Node):
    # FIXME: short and long forms, plus trait to select for display
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

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_binary_prefixed_unit(fabll.Node):
    BINARY_PREFIXES: ClassVar[dict[str, float]] = {
        "Ki": 2**10,  # kibi
        "Mi": 2**20,  # mebi
        "Gi": 2**30,  # gibi
        "Ti": 2**40,  # tebi
        "Pi": 2**50,  # pebi
        "Ei": 2**60,  # exbi
        "Zi": 2**70,  # zebi
        "Yi": 2**80,  # yobi
    }

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


def decode_symbol(
    g: graph.GraphView, tg: fbrk.TypeGraph, symbol: str
) -> type[fabll.Node]:
    """
    Decode a unit symbol to a unit type at compile-time (type-level lookup).

    This queries the typegraph for type definitions that have the is_unit trait,
    rather than searching for instances. Use this when you need to resolve
    symbols before any instances are created.
    """
    # TODO: caching
    # TODO: optimisation: pre-compute symbol map; build suffix trie
    # FIXME: only once per typegraph
    sorted_symbol_map = register_all_units(
        g, tg
    )  # Ensure all unit types are registered)

    # 1. Exact match
    if symbol in sorted_symbol_map.keys():
        return sorted_symbol_map[symbol]

    # 2. Prefixed
    for known_symbol in sorted_symbol_map.keys():
        if symbol.endswith(known_symbol):
            prefix = symbol.removesuffix(known_symbol)
            fabll_unit_type = sorted_symbol_map[known_symbol]

            if (
                getattr(fabll_unit_type, "is_si_prefixed", False)
                and prefix in is_si_prefixed_unit.SI_PREFIXES
            ):
                scale_factor = is_si_prefixed_unit.SI_PREFIXES[prefix]
            elif (
                getattr(fabll_unit_type, "is_binary_prefixed", False)
                and prefix in is_binary_prefixed_unit.BINARY_PREFIXES
            ):
                scale_factor = is_binary_prefixed_unit.BINARY_PREFIXES[prefix]
            else:
                continue

            # fabll_unit_type_node = not_none(
            #     fabll_unit_type.bind_typegraph(tg).try_get_type_trait(is_unit_type)
            # ).get_basis_vector()
            unit_expression_t = UnitExpressionFactory(
                (symbol,), ((fabll_unit_type, 1),), scale_factor, 0.0
            )

            return unit_expression_t

    raise UnitNotFoundError(symbol)


# TODO: remove?
def decode_symbol_runtime(
    g: graph.GraphView, tg: fbrk.TypeGraph, symbol: str
) -> is_unit:
    # TODO: caching
    # TODO: optimisation: pre-compute symbol map; build suffix trie

    all_units = fabll.Traits.get_implementors(is_unit.bind_typegraph(tg), g)
    # TODO: more efficient filtering
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

            # TODO: provide symbol for caching
            return unit.scaled_copy(g=g, tg=tg, multiplier=scale_factor)

    raise UnitNotFoundError(symbol)


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
    Rpm = auto()


PERCENT_SYMBOL = "%"
DIMENSIONLESS_SYMBOL = "dimensionless"

_UNIT_SYMBOLS: dict[_UnitRegistry, tuple[str, ...]] = {
    # prefereed unit for display comes first (must be valid with prefixes)
    _UnitRegistry.Dimensionless: (DIMENSIONLESS_SYMBOL,),
    _UnitRegistry.Percent: (PERCENT_SYMBOL,),
    _UnitRegistry.Ppm: ("ppm",),
    _UnitRegistry.Ampere: ("A", "ampere"),
    _UnitRegistry.Second: ("s",),
    _UnitRegistry.Meter: ("m",),
    _UnitRegistry.Kilogram: ("kg",),
    _UnitRegistry.Kelvin: ("K",),
    _UnitRegistry.Mole: ("mol",),
    _UnitRegistry.Candela: ("cd",),
    _UnitRegistry.Radian: ("rad",),
    _UnitRegistry.Steradian: ("sr",),
    _UnitRegistry.Hertz: ("Hz", "hertz"),
    _UnitRegistry.Newton: ("N",),
    _UnitRegistry.Pascal: ("Pa",),
    _UnitRegistry.Joule: ("J",),
    _UnitRegistry.Watt: ("W", "watt"),
    _UnitRegistry.Coulomb: ("C",),
    _UnitRegistry.Volt: ("V", "volt"),
    _UnitRegistry.Farad: ("F", "farad"),
    _UnitRegistry.Ohm: ("Ω", "ohm"),
    _UnitRegistry.Siemens: ("S",),
    _UnitRegistry.Weber: ("Wb",),
    _UnitRegistry.Tesla: ("T",),
    _UnitRegistry.Henry: ("H", "henry"),
    _UnitRegistry.DegreeCelsius: ("°C", "degC"),
    _UnitRegistry.Lumen: ("lm",),
    _UnitRegistry.Lux: ("lx",),
    _UnitRegistry.Becquerel: ("Bq",),
    _UnitRegistry.Gray: ("Gy",),
    _UnitRegistry.Sievert: ("Sv",),
    _UnitRegistry.Katal: ("kat",),
    _UnitRegistry.Bit: ("b", "bit"),
    _UnitRegistry.Byte: ("B", "byte"),
    _UnitRegistry.Gram: ("g",),
    _UnitRegistry.Degree: ("°", "deg"),
    _UnitRegistry.ArcMinute: ("arcmin",),
    _UnitRegistry.ArcSecond: ("arcsec",),
    _UnitRegistry.Minute: ("min",),
    _UnitRegistry.Day: ("day",),
    _UnitRegistry.Hour: ("hour",),
    _UnitRegistry.Week: ("week",),
    _UnitRegistry.Month: ("month",),
    _UnitRegistry.Year: ("year",),
    _UnitRegistry.Liter: ("liter",),
    _UnitRegistry.Rpm: ("rpm", "RPM"),
}


class Dimensionless(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = _BasisVector.ORIGIN

    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Dimensionless], unit_vector_arg
        )
    ).put_on_type()
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            tuple(_UNIT_SYMBOLS[_UnitRegistry.Dimensionless]),
            unit_vector_arg,
        )
    )


UnitVectorT = tuple[tuple[type[fabll.Node], int], ...]


class is_unit_expression(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def get_obj(self) -> "UnitExpression":
        return fabll.Traits(self).get_obj_raw().cast(UnitExpression, check=False)


class UnitExpression(fabll.Node):
    """
    Base class for dynamically-constructed unit expression types.

    UnitExpressions represent higher-order derivations of static unit types
    (e.g., Volt/Second). Concrete types are created via UnitExpressionFactory.
    """

    is_unit_expression = fabll.Traits.MakeEdge(is_unit_expression.MakeChild())
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        F.Parameters.is_parameter_operatable.MakeChild()
    )
    _multiplier_identifier: ClassVar[str] = "multiplier"
    _offset_identifier: ClassVar[str] = "offset"

    _unit_vector_arg: ClassVar[tuple[tuple[type[fabll.Node], int], ...]] = ()
    _multiplier_arg: ClassVar[float] = 1.0
    _offset_arg: ClassVar[float] = 0.0

    expr = F.Collections.Pointer.MakeChild()

    def get_expr(self) -> fabll.Node:
        return self.expr.get().deref()

    def get_multiplier(self) -> float:
        multiplier_child = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._multiplier_identifier
        )
        return F.Literals.Numbers.bind_instance(not_none(multiplier_child)).get_single()

    def get_offset(self) -> float:
        offset_child = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._offset_identifier
        )
        return F.Literals.Numbers.bind_instance(not_none(offset_child)).get_single()

    def setup(self, expr_type: type["UnitExpression"]) -> Self:  # type: ignore[invalid-method-override]
        from faebryk.library.Expressions import Multiply, Power

        g = self.g
        tg = self.tg

        term_nodes: list["F.Parameters.can_be_operand"] = []
        for unit_type, exponent in expr_type._unit_vector_arg:
            unit_instance = unit_type.bind_typegraph(tg=tg).create_instance(g=g)

            exponent_param = (
                F.Parameters.NumericParameter.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .setup(
                    is_unit=Dimensionless.bind_typegraph(tg=tg)
                    .create_instance(g=g)
                    .is_unit.get()
                )
            )

            exponent_lit = (
                F.Literals.Numbers.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .setup_from_singleton(
                    value=float(exponent),
                    unit=Dimensionless.bind_typegraph(tg=tg)
                    .create_instance(g=g)
                    .is_unit.get(),
                )
            )

            F.Expressions.Is.bind_typegraph(tg=tg).create_instance(g=g).setup(
                exponent_param.can_be_operand.get(),
                exponent_lit.is_literal.get().as_operand.get(),
                assert_=True,
            )

            power_node = (
                Power.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .setup(
                    base=unit_instance.get_trait(F.Parameters.can_be_operand),
                    exponent=exponent_param.can_be_operand.get(),
                )
            )
            term_nodes.append(power_node.can_be_operand.get())

        multiply_node = (
            Multiply.bind_typegraph(tg=tg).create_instance(g=g).setup(*term_nodes)
        )

        self.expr.get().point(multiply_node)

        return self

    @classmethod
    def MakeChild(cls) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
        from faebryk.library.Expressions import Multiply, Power

        out = fabll._ChildField(cls)
        term_fields = list[fabll.RefPath]()

        for unit, exponent in cls._unit_vector_arg:
            unit_field = unit.MakeChild()
            out.add_dependant(unit_field)

            exponent_field = F.Parameters.NumericParameter.MakeChild(
                unit=Dimensionless,
                domain=F.NumberDomain.Args(negative=True, integer=True),
            )
            out.add_dependant(exponent_field)

            exponent_lit = F.Literals.Numbers.MakeChild(
                min=exponent, max=exponent, unit=Dimensionless
            )
            exponent_is_expr = F.Expressions.Is.MakeChild(
                [exponent_field], [exponent_lit], assert_=True
            )
            exponent_is_expr.add_dependant(exponent_lit, identifier="lit", before=True)
            out.add_dependant(exponent_is_expr)

            term_field = Power.MakeChild([unit_field], [exponent_field])
            out.add_dependant(term_field)
            term_fields.append([term_field])

        expr_field = Multiply.MakeChild(*term_fields)
        out.add_dependant(expr_field)
        out.add_dependant(F.Collections.Pointer.MakeEdge([out, cls.expr], [expr_field]))

        return out


@once
def UnitExpressionFactory(
    symbols: tuple[str, ...],
    unit_vector: UnitVectorT,
    multiplier: float = 1.0,
    offset: float = 0.0,
) -> type[UnitExpression]:
    ConcreteUnitExpr = fabll.Node._copy_type(UnitExpression)

    unit_vector_str = "".join(
        f"{unit.__name__}^{exponent}" for unit, exponent in unit_vector
    )
    ConcreteUnitExpr.__name__ = f"{UnitExpression.__name__}<{unit_vector_str}>"

    ConcreteUnitExpr._unit_vector_arg = unit_vector
    ConcreteUnitExpr._multiplier_arg = multiplier
    ConcreteUnitExpr._offset_arg = offset

    ConcreteUnitExpr._add_field(
        ConcreteUnitExpr._multiplier_identifier,
        F.Literals.Numbers.MakeChild_SingleValue(value=multiplier, unit=Dimensionless),
    )
    ConcreteUnitExpr._add_field(
        ConcreteUnitExpr._offset_identifier,
        F.Literals.Numbers.MakeChild_SingleValue(value=offset, unit=Dimensionless),
    )
    if not symbols and len(unit_vector) == 1:
        unit_type = unit_vector[0][0]
        unit_registry_member = getattr(_UnitRegistry, unit_type.__name__)
        symbols = tuple(_UNIT_SYMBOLS[unit_registry_member])
    assert len(symbols) >= 1, "Unit Expression must have at least one symbol"

    # Derive the basis/multiplier/offset tuple for this expression.
    # Resolve the unit vector to get the composed basis vector, multiplier, and offset
    # from any nested UnitExpressions. Then combine with the user-provided values.
    unit_info = resolve_unit_vector(unit_vector)

    ConcreteUnitExpr._add_field(
        "is_unit",
        fabll.Traits.MakeEdge(
            is_unit.MakeChild(
                symbols,
                unit_info.basis_vector,
                multiplier * unit_info.multiplier,
                offset + unit_info.offset,
            )
        ),
    )

    return ConcreteUnitExpr


class _AnonymousUnit(fabll.Node):
    _is_unit_id: ClassVar[str] = "is_unit"
    is_unit_type = fabll.Traits.MakeEdge(is_unit_type.MakeChild(())).put_on_type()
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())

    def get_is_unit(self) -> "is_unit":
        # FIXME
        return is_unit.bind_instance(
            instance=not_none(
                fbrk.EdgeComposition.get_child_by_identifier(
                    bound_node=self.instance, child_identifier=self._is_unit_id
                )
            )
        )


def AnonymousUnitFactory(
    vector: BasisVector,
    multiplier: float = 1.0,
    offset: float = 0.0,
    symbols: tuple[str, ...] = (),
) -> type[fabll.Node]:
    """
    Create an anonymous unit type from raw unit info.

    Unlike UnitExpressionFactory which takes a UnitVectorT (unit types with exponents),
    this takes a BasisVector directly. Useful for creating units with computed
    dimensional properties (e.g., from unit inference).
    """
    ConcreteUnit = fabll.Node._copy_type(_AnonymousUnit)
    ConcreteUnit.__name__ = f"_AnonymousUnit<{vector}x{multiplier}>"

    # Add attributes for extract_unit_info compatibility (same as base units)
    ConcreteUnit.unit_vector_arg = vector
    ConcreteUnit.multiplier_arg = multiplier
    ConcreteUnit.offset_arg = offset

    ConcreteUnit._add_field(
        ConcreteUnit._is_unit_id,
        fabll.Traits.MakeEdge(is_unit.MakeChild(symbols, vector, multiplier, offset)),
    )

    return ConcreteUnit


class _UnitExpressionResolver:
    def __init__(self, g: graph.GraphView, tg: fbrk.TypeGraph):
        self.g = g
        self.tg = tg

    def visit(self, node: fabll.Node) -> is_unit:
        if node.isinstance(F.Parameters.can_be_operand):
            # unwrap and try again
            return self.visit(
                node.cast(F.Parameters.can_be_operand, check=False).get_raw_obj()
            )

        if unit := node.try_get_trait(is_unit):
            # already resolved
            if unit.is_affine:
                raise UnitExpressionError(
                    "Cannot use affine unit in compound expression"
                )
            return unit

        if has_unit_trait := node.try_get_trait(has_unit):
            return has_unit_trait.get_is_unit()

        if node.isinstance(F.Expressions.Add):
            return self.visit_additive(node.cast(F.Expressions.Add))
        elif node.isinstance(F.Expressions.Subtract):
            return self.visit_subtract(node.cast(F.Expressions.Subtract))
        elif node.isinstance(F.Expressions.Multiply):
            return self.visit_multiply(node.cast(F.Expressions.Multiply))
        elif node.isinstance(F.Expressions.Divide):
            return self.visit_divide(node.cast(F.Expressions.Divide))
        elif node.isinstance(F.Expressions.Power):
            return self.visit_power(node.cast(F.Expressions.Power))
        elif node.has_trait(is_unit_expression):
            return self.visit_unit_expression(node.cast(UnitExpression, check=False))

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

    def visit_additive(self, node: F.Expressions.Add) -> is_unit:
        """Resolve Add expression - all operands must be commensurable."""
        operands = node.operands.get().as_list()

        first_op, *other_ops = operands
        first_unit = self.visit(first_op)
        first_vector = first_unit._extract_basis_vector()

        for op in other_ops:
            op_unit = self.visit(op)
            if op_unit._extract_basis_vector() != first_vector:
                raise UnitsNotCommensurableError(
                    "Operands in addition must have commensurable units"
                )

        return first_unit

    def visit_subtract(self, node: F.Expressions.Subtract) -> is_unit:
        """Resolve Subtract expression - all operands must be commensurable."""
        minuend = node.minuend.get().deref()
        subtrahends = node.subtrahends.get().as_list()

        minuend_unit = self.visit(minuend)
        minuend_vector = minuend_unit._extract_basis_vector()

        for sub in subtrahends:
            sub_unit = self.visit(sub)
            if sub_unit._extract_basis_vector() != minuend_vector:
                raise UnitsNotCommensurableError(
                    "Operands in subtraction must have commensurable units"
                )

        return minuend_unit

    def visit_multiply(self, node: F.Expressions.Multiply) -> is_unit:
        operands = node.operands.get().as_list()

        if not operands:
            return is_unit.new(
                g=self.g,
                tg=self.tg,
                vector=_BasisVector.ORIGIN,
                multiplier=1.0,
                offset=0.0,
            )

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
                    *node.zdenominator.get().as_list(),
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

        exponent_val = exponent_lit.cast(F.Literals.Numbers).get_single()

        if not float(exponent_val).is_integer():
            raise UnitExpressionError(
                f"Unit exponent must be integer, got {exponent_val}"
            )

        return self.visit(base).op_power(self.g, self.tg, int(exponent_val))


def resolve_unit_expression(
    g: graph.GraphView, tg: fbrk.TypeGraph, expr: graph.BoundNode
) -> _AnonymousUnit:
    # TODO: caching?
    resolver = _UnitExpressionResolver(g=g, tg=tg)
    node = fabll.Node.bind_instance(expr)
    result_unit = resolver.visit(node)
    parent, _ = result_unit.get_parent_force()
    return parent.cast(_AnonymousUnit, check=False)


def resolve_unit_vector(unit_vector: UnitVectorT) -> UnitInfo:
    return reduce(
        lambda a, b: a.op_multiply(b),
        [extract_unit_info(unit).op_power(exponent) for unit, exponent in unit_vector],
    )


# FIXME: refactor
def extract_unit_info(unit_type: type[fabll.Node]) -> UnitInfo:
    # Handle UnitExpression types (have _unit_vector_arg with underscore prefix)
    # These need to be recursively resolved since they compose other units
    if hasattr(unit_type, "_unit_vector_arg"):
        unit_vector = getattr(unit_type, "_unit_vector_arg")
        multiplier = getattr(unit_type, "_multiplier_arg")
        offset = getattr(unit_type, "_offset_arg")
        # Recursively resolve the unit vector to get the basis vector
        unit_info = resolve_unit_vector(unit_vector)
        # Combine multipliers (the inner multiplier is already factored into basis)
        return UnitInfo(
            basis_vector=unit_info.basis_vector,
            multiplier=multiplier * unit_info.multiplier,
            offset=offset + unit_info.offset,
        )

    # Handle base units (have unit_vector_arg without underscore)
    basis_vector = getattr(unit_type, "unit_vector_arg", None)
    # Check class name to avoid module path issues when running tests on source files
    assert basis_vector is not None and type(basis_vector).__name__ == "BasisVector", (
        f"Expected BasisVector, got {type(basis_vector)} for {unit_type}"
    )
    multiplier = getattr(unit_type, "multiplier_arg")
    offset = getattr(unit_type, "offset_arg")

    return UnitInfo(basis_vector=basis_vector, multiplier=multiplier, offset=offset)


# SI base units ------------------------------------------------------------------------


class Ampere(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(ampere=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ampere],
            unit_vector_arg,
            multiplier_arg,
            offset_arg,
        ),
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ampere],
            unit_vector_arg,
            multiplier_arg,
            offset_arg,
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Meter(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Meter],
            unit_vector_arg,
            multiplier_arg,
            offset_arg,
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Meter],
            unit_vector_arg,
            multiplier_arg,
            offset_arg,
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Kilogram(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Kilogram], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Kilogram], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())


class Second(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Second], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Second], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Kelvin(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kelvin=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Kelvin], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Kelvin], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Mole(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(mole=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Mole], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Mole], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Candela(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(candela=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Candela], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Candela], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# SI coherent derived units ------------------------------------------------------------


class Radian(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Radian], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Radian], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Steradian(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(steradian=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Steradian], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Steradian], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Hertz(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=-1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Hertz], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Hertz], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Newton(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1, meter=1, second=-2)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Newton], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Newton], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Pascal(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=-1, second=-2
    )
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Pascal], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Pascal], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Joule(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1, meter=2, second=-2)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Joule], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Joule], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Watt(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1, meter=2, second=-3)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Watt], unit_vector_arg)
    ).put_on_type()
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Watt], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Coulomb(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(ampere=1, second=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Coulomb], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Coulomb], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Volt(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-3, ampere=-1
    )
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Volt], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Volt], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Farad(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=-1, meter=-2, second=4, ampere=2
    )
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Farad], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Farad], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Ohm(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-3, ampere=-2
    )
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Ohm], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Ohm], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Siemens(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=-1, meter=-2, second=3, ampere=2
    )
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Siemens], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Siemens], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Weber(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-2, ampere=-1
    )
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Weber], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Weber], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Tesla(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, second=-2, ampere=-1
    )
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Tesla], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Tesla], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Henry(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-2, ampere=-2
    )
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Henry], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Henry], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class DegreeCelsius(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kelvin=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 273.15

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.DegreeCelsius],
            unit_vector_arg,
            offset=273.15,
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.DegreeCelsius],
            unit_vector_arg,
            offset=273.15,
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Lumen(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(candela=1, steradian=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Lumen], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Lumen], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Lux(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        candela=1, steradian=1, meter=-2
    )
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Lux], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Lux], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# TODO: prevent mixing with Hertz via context/domain tagging system?
class Becquerel(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=-1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Becquerel], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Becquerel], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Gray(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=2, second=-2)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Gray], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Gray], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Sievert(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=2, second=-2)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Sievert], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Sievert], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Katal(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(mole=1, second=-1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Katal], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Katal], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# SI patches ---------------------------------------------------------------------------


class Gram(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1)
    multiplier_arg: ClassVar[float] = 1e-3
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Gram], unit_vector_arg, multiplier=1e-3
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Gram], unit_vector_arg, multiplier=1e-3
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# non-SI base units --------------------------------------------------------------------


class Bit(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(bit=1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Bit], unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Bit], unit_vector_arg)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())
    is_binary_prefixed = fabll.Traits.MakeEdge(is_binary_prefixed_unit.MakeChild())


# Dimensionless scalar multiples -------------------------------------------------------


class Percent(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = _BasisVector.ORIGIN
    multiplier_arg: ClassVar[float] = 1e-2
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Percent], unit_vector_arg, multiplier=1e-2
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Percent], unit_vector_arg, multiplier=1e-2
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


class Ppm(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = _BasisVector.ORIGIN
    multiplier_arg: ClassVar[float] = 1e-6
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ppm], unit_vector_arg, multiplier=1e-6
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ppm], unit_vector_arg, multiplier=1e-6
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


# Common non-SI multiples --------------------------------------------------------------


class Degree(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1)
    multiplier_arg: ClassVar[float] = math.pi / 180.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Degree],
            unit_vector_arg,
            multiplier=math.pi / 180.0,
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Degree],
            unit_vector_arg,
            multiplier=math.pi / 180.0,
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


class ArcMinute(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1)
    multiplier_arg: ClassVar[float] = math.pi / 180.0 / 60.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.ArcMinute],
            unit_vector_arg,
            multiplier=math.pi / 180.0 / 60.0,
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.ArcMinute],
            unit_vector_arg,
            multiplier=math.pi / 180.0 / 60.0,
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


class ArcSecond(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1)
    multiplier_arg: ClassVar[float] = math.pi / 180.0 / 3600.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.ArcSecond],
            unit_vector_arg,
            multiplier=math.pi / 180.0 / 3600.0,
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.ArcSecond],
            unit_vector_arg,
            multiplier=math.pi / 180.0 / 3600.0,
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


class Minute(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)
    multiplier_arg: ClassVar[float] = 60.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Minute], unit_vector_arg, multiplier=60.0
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Minute], unit_vector_arg, multiplier=60.0
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


class Hour(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)
    multiplier_arg: ClassVar[float] = 3600.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Hour], unit_vector_arg, multiplier=3600.0
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Hour], unit_vector_arg, multiplier=3600.0
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


class Day(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)
    multiplier_arg: ClassVar[float] = 24 * 3600.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Day], unit_vector_arg, multiplier=24 * 3600.0
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Day], unit_vector_arg, multiplier=24 * 3600.0
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


class Week(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)
    multiplier_arg: ClassVar[float] = 7 * 24 * 3600.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Week],
            unit_vector_arg,
            multiplier=7 * 24 * 3600.0,
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Week],
            unit_vector_arg,
            multiplier=7 * 24 * 3600.0,
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


class Month(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)
    multiplier_arg: ClassVar[float] = (365.25 / 12) * 24 * 3600.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Month],
            unit_vector_arg,
            multiplier=(365.25 / 12) * 24 * 3600.0,
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Month],
            unit_vector_arg,
            multiplier=(365.25 / 12) * 24 * 3600.0,
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


class Year(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)
    multiplier_arg: ClassVar[float] = 365.25 * 24 * 3600.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Year],
            unit_vector_arg,
            multiplier=365.25 * 24 * 3600.0,
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Year],
            unit_vector_arg,
            multiplier=365.25 * 24 * 3600.0,
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


class Liter(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=3)
    multiplier_arg: ClassVar[float] = 1e-3
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Liter], unit_vector_arg, multiplier=1e-3
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Liter], unit_vector_arg, multiplier=1e-3
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Rpm(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1, second=-1)
    multiplier_arg: ClassVar[float] = (2 * math.pi) / 60.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Rpm],
            unit_vector_arg,
            multiplier=(2 * math.pi) / 60.0,
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Rpm],
            unit_vector_arg,
            multiplier=(2 * math.pi) / 60.0,
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())


class Byte(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(bit=1)
    multiplier_arg: ClassVar[float] = 8.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Byte], unit_vector_arg, multiplier=8.0
        )
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Byte], unit_vector_arg, multiplier=8.0
        )
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())
    is_binary_prefixed = fabll.Traits.MakeEdge(is_binary_prefixed_unit.MakeChild())


# Shortcuts for use elsewhere in the standard library ---------------------------------


class BitsPerSecond(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(bit=1, second=-1)
    multiplier_arg: ClassVar[float] = 1.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild((), unit_vector_arg)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(is_unit.MakeChild((), unit_vector_arg))
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())
    is_binary_prefixed = fabll.Traits.MakeEdge(is_binary_prefixed_unit.MakeChild())


class AmpereHour(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(ampere=1, second=1)
    multiplier_arg: ClassVar[float] = 3600.0
    offset_arg: ClassVar[float] = 0.0

    is_unit_type = fabll.Traits.MakeEdge(
        is_unit_type.MakeChild((), unit_vector_arg, multiplier=3600.0)
    ).put_on_type()
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild((), unit_vector_arg, multiplier=3600.0)
    )
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


AmpereSecond = UnitExpressionFactory(("As", "A*s"), ((Ampere, 1), (Second, 1)))
VoltsPerSecond = UnitExpressionFactory(("Vps", "V/s"), ((Volt, 1), (Second, -1)))


# Logarithmic units --------------------------------------------------------------------
# TODO: logarithmic units


@once
def register_all_units(
    g: graph.GraphView, tg: fbrk.TypeGraph
) -> dict[str, type[fabll.Node]]:
    """
    Register all unit type nodes in the typegraph.

    Note: This only creates TYPE NODES, not instances. The is_unit_type
    traits are accessible at the type level via try_get_type_trait().

    Returns symbol map of unit type by symbol.
    """
    # TODO: Solution without magic or dedicated table?
    symbol_map = {}
    for registry, symbols in _UNIT_SYMBOLS.items():
        unit_type = globals()[registry.name]
        assert isinstance(unit_type, type) and issubclass(unit_type, fabll.Node)
        fabll.TypeNodeBoundTG.get_or_create_type_in_tg(tg=tg, t=unit_type)
        for symbol in symbols:
            symbol_map[symbol] = unit_type

    symbol_map = dict(sorted(symbol_map.items(), key=lambda x: len(x[0]), reverse=True))
    return symbol_map


class BoundUnitsContext:
    def __init__(self, tg: fbrk.TypeGraph, g: graph.GraphView):
        self.tg = tg
        self.g = g
        self.literals = F.Literals.BoundLiteralContext(tg=tg, g=g)

    @property
    @once
    def NumericParameter(self) -> F.Parameters.NumericParameter:
        return F.Parameters.NumericParameter.bind_typegraph(tg=self.tg).create_instance(
            g=self.g
        )

    @property
    @once
    def Meter(self) -> Meter:
        return Meter.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Second(self) -> Second:
        return Second.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Hour(self) -> Hour:
        return Hour.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Dimensionless(self) -> Dimensionless:
        return Dimensionless.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Percent(self) -> Percent:
        return Percent.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Ppm(self) -> Ppm:
        return Ppm.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Radian(self) -> Radian:
        return Radian.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Steradian(self) -> Steradian:
        return Steradian.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def DegreeCelsius(self) -> DegreeCelsius:
        return DegreeCelsius.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Kelvin(self) -> Kelvin:
        return Kelvin.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Volt(self) -> Volt:
        return Volt.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Ohm(self) -> Ohm:
        return Ohm.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Ampere(self) -> Ampere:
        return Ampere.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Degree(self) -> Degree:
        return Degree.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Bit(self) -> Bit:
        return Bit.bind_typegraph(tg=self.tg).create_instance(g=self.g)


class _TestWithContext:
    @pytest.fixture
    def ctx(cls) -> BoundUnitsContext:
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        return BoundUnitsContext(tg=tg, g=g)


class TestIsUnit(_TestWithContext):
    @staticmethod
    def assert_commensurability(items: Sequence[is_unit]) -> is_unit:
        if not items:
            raise ValueError("At least one item is required")

        (first_unit, *other_units) = items

        for other_unit in other_units:
            if not first_unit.is_commensurable_with(other_unit):
                symbols = [unit._extract_symbols() for unit in items]
                raise UnitsNotCommensurableError(
                    "Operands have incommensurable units:\n"
                    + "\n".join(
                        f"`{item!r}` ({symbols[i]})" for i, item in enumerate(items)
                    ),
                    incommensurable_items=items,
                )

        return first_unit

    def test_assert_commensurability_empty_list(self):
        """Test that empty list raises ValueError"""
        with pytest.raises(ValueError):
            TestIsUnit.assert_commensurability([])

    def test_assert_commmensurability_single_item(self, ctx: BoundUnitsContext):
        """Test that single item list returns its unit"""
        result = TestIsUnit.assert_commensurability([ctx.Meter.is_unit.get()])
        assert result == ctx.Meter.is_unit.get()
        parent, _ = result.get_parent_force()
        assert parent.isinstance(Meter)
        assert is_unit.bind_instance(result.instance).get_symbols() == ["m"]

    def test_assert_commensurability(self, ctx: BoundUnitsContext):
        """Test that commensurable units pass validation and return first unit"""
        result = TestIsUnit.assert_commensurability(
            [
                ctx.Second.is_unit.get(),
                ctx.Hour.is_unit.get(),
            ]
        )
        parent, _ = result.get_parent_force()
        assert parent.isinstance(Second)

    def test_assert_incommensurability(self, ctx: BoundUnitsContext):
        """Test that incompatible units raise UnitsNotCommensurable"""
        with pytest.raises(UnitsNotCommensurableError):
            TestIsUnit.assert_commensurability(
                [ctx.Meter.is_unit.get(), ctx.Second.is_unit.get()]
            )

    def test_assert_commensurable_units_with_derived(self, ctx: BoundUnitsContext):
        """Test that derived units are handled correctly"""

        MetersPerSecondExpr = UnitExpressionFactory(
            ("m/s",), ((Meter, 1), (Second, -1))
        )
        KilometerExpr = UnitExpressionFactory(("km",), ((Meter, 1),), multiplier=1000)
        KilometersPerHourExpr = UnitExpressionFactory(
            ("km/h", "kph"), ((KilometerExpr, 1), (Hour, -1))
        )

        class App(fabll.Node):
            meters_per_second_expr = MetersPerSecondExpr.MakeChild()
            kilometers_per_hour_expr = KilometersPerHourExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        meters_per_second = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.meters_per_second_expr.get().instance
        )
        kilometers_per_hour = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.kilometers_per_hour_expr.get().instance
        )

        TestIsUnit.assert_commensurability(
            [
                meters_per_second.get_trait(is_unit),
                kilometers_per_hour.get_trait(is_unit),
            ]
        )

    def test_assert_commensurability_with_incommensurable_derived(
        self,
        ctx: BoundUnitsContext,
    ):
        """Test that incommensurable derived units raise UnitsNotCommensurable"""
        MetersPerSecondExpr = UnitExpressionFactory(
            ("m/s",), ((Meter, 1), (Second, -1))
        )
        MeterSecondsExpr = UnitExpressionFactory(("m*s",), ((Meter, 1), (Second, 1)))

        class App(fabll.Node):
            meters_per_second_expr = MetersPerSecondExpr.MakeChild()
            meter_seconds_expr = MeterSecondsExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        meters_per_second = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.meters_per_second_expr.get().instance
        )
        meter_seconds = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.meter_seconds_expr.get().instance
        )
        with pytest.raises(UnitsNotCommensurableError):
            TestIsUnit.assert_commensurability(
                [
                    meters_per_second.get_trait(is_unit),
                    meter_seconds.get_trait(is_unit),
                ]
            )

    def test_dimensionless_radian_steradian_incompatible(self, ctx: BoundUnitsContext):
        """
        Test that dimensionless, radian, and steradian are mutually incommensurable.
        """
        dimensionless = ctx.Dimensionless.is_unit.get()
        radian = ctx.Radian.is_unit.get()
        steradian = ctx.Steradian.is_unit.get()

        with pytest.raises(UnitsNotCommensurableError):
            TestIsUnit.assert_commensurability([dimensionless, radian])

        with pytest.raises(UnitsNotCommensurableError):
            TestIsUnit.assert_commensurability([dimensionless, steradian])

        with pytest.raises(UnitsNotCommensurableError):
            TestIsUnit.assert_commensurability([radian, steradian])

    def test_dimensionless_percent_ppm_compatible(self, ctx: BoundUnitsContext):
        """Test that dimensionless, percent, and ppm are mutually commensurable."""
        dimensionless = ctx.Dimensionless.is_unit.get()
        percent = ctx.Percent.is_unit.get()
        ppm = ctx.Ppm.is_unit.get()

        result = TestIsUnit.assert_commensurability([dimensionless, percent, ppm])
        parent, _ = result.get_parent_force()
        assert parent.isinstance(Dimensionless)

    def test_unit_multiply(self, ctx: BoundUnitsContext):
        """Test unit multiplication: Volt * Ampere produces Watt-equivalent basis."""
        volt = ctx.Volt.is_unit.get()
        ampere = ctx.Ampere.is_unit.get()

        result = volt.op_multiply(ctx.g, ctx.tg, ampere)
        assert result._extract_basis_vector() == BasisVector(
            kilogram=1, meter=2, second=-3
        )

    def test_unit_divide(self, ctx: BoundUnitsContext):
        """Test unit division: Volt / Ampere produces Ohm-equivalent basis."""
        volt = ctx.Volt.is_unit.get()
        ampere = ctx.Ampere.is_unit.get()

        result = volt.op_divide(ctx.g, ctx.tg, ampere)
        assert result._extract_basis_vector() == Ohm.unit_vector_arg

    def test_unit_power(self, ctx: BoundUnitsContext):
        """Test unit exponentiation."""
        meter = ctx.Meter.is_unit.get()

        squared = meter.op_power(ctx.g, ctx.tg, 2)
        assert squared._extract_basis_vector() == BasisVector(meter=2)

        cubed = meter.op_power(ctx.g, ctx.tg, 3)
        assert cubed._extract_basis_vector() == BasisVector(meter=3)

        inverse = meter.op_power(ctx.g, ctx.tg, -1)
        assert inverse._extract_basis_vector() == BasisVector(meter=-1)

    def test_unit_invert(self, ctx: BoundUnitsContext):
        """Test unit inversion: 1/Second has the same basis as Hertz."""
        second = ctx.Second.is_unit.get()

        result = second.op_invert(ctx.g, ctx.tg)
        assert result._extract_basis_vector() == Hertz.unit_vector_arg

    def test_get_conversion_to_scaled(self, ctx: BoundUnitsContext):
        """Test conversion between units with different multipliers."""
        _ = ctx.Meter
        meter = decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol="m")
        kilometer = decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol="km")

        scale, offset = kilometer.get_conversion_to(meter)
        assert scale == 1000.0
        assert offset == 0.0

        scale, offset = meter.get_conversion_to(kilometer)
        assert scale == 0.001
        assert offset == 0.0

    def test_get_conversion_to_affine(self, ctx: BoundUnitsContext):
        """Test conversion between affine units (DegreeCelsius <-> Kelvin)."""
        celsius = ctx.DegreeCelsius.is_unit.get()
        kelvin = ctx.Kelvin.is_unit.get()

        scale, offset = celsius.get_conversion_to(kelvin)
        assert scale == 1.0
        assert offset == 273.15

    def test_get_conversion_to_incommensurable_raises(self, ctx: BoundUnitsContext):
        """Test that conversion between incommensurable units raises error."""
        meter = ctx.Meter.is_unit.get()
        second = ctx.Second.is_unit.get()

        with pytest.raises(UnitsNotCommensurableError):
            meter.get_conversion_to(second)

    def test_is_affine(self, ctx: BoundUnitsContext):
        """Test is_affine property for affine and non-affine units."""
        celsius = ctx.DegreeCelsius.is_unit.get()
        kelvin = ctx.Kelvin.is_unit.get()
        meter = ctx.Meter.is_unit.get()

        assert celsius.is_affine
        assert not kelvin.is_affine
        assert not meter.is_affine

    def test_is_dimensionless(self, ctx: BoundUnitsContext):
        """Test is_dimensionless property."""
        dimensionless = ctx.Dimensionless.is_unit.get()
        percent = ctx.Percent.is_unit.get()
        ppm = ctx.Ppm.is_unit.get()
        meter = ctx.Meter.is_unit.get()

        assert dimensionless.is_dimensionless()
        assert percent.is_dimensionless()
        assert ppm.is_dimensionless()
        assert not meter.is_dimensionless()

    def test_is_angular(self, ctx: BoundUnitsContext):
        """Test is_angular property."""
        radian = ctx.Radian.is_unit.get()
        degree = ctx.Degree.is_unit.get()
        meter = ctx.Meter.is_unit.get()
        dimensionless = ctx.Dimensionless.is_unit.get()

        assert radian.is_angular()
        assert degree.is_angular()
        assert not meter.is_angular()
        assert not dimensionless.is_angular()

    def test_setup(self, ctx: BoundUnitsContext):
        is_unit_ = is_unit.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        is_unit_.setup(
            g=ctx.g,
            tg=ctx.tg,
            symbols=["m"],
            unit_vector=BasisVector(meter=1),
            multiplier=1.0,
            offset=0.0,
        )
        assert not_none(is_unit_._extract_symbols()) == ["m"]

        assert _BasisVector.bind_instance(
            is_unit_.basis_vector.get().deref().instance
        ).extract_vector() == BasisVector(meter=1)

        assert is_unit_._extract_multiplier() == 1.0
        assert is_unit_._extract_offset() == 0.0

    def test_to_base_units_prefixed(self, ctx: BoundUnitsContext):
        """Prefixed unit normalizes to base unit with multiplier=1."""
        _ = ctx.Meter
        kilometer = decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol="km")
        base = kilometer.to_base_units(g=ctx.g, tg=ctx.tg)

        assert base._extract_basis_vector() == BasisVector(meter=1)
        assert base._extract_multiplier() == 1.0
        assert base._extract_offset() == 0.0

    def test_to_base_units_affine(self, ctx: BoundUnitsContext):
        """Affine unit normalizes to base unit with offset=0."""
        celsius = ctx.DegreeCelsius.is_unit.get()
        base = celsius.to_base_units(g=ctx.g, tg=ctx.tg)

        assert base._extract_basis_vector() == BasisVector(kelvin=1)
        assert base._extract_multiplier() == 1.0
        assert base._extract_offset() == 0.0

    def test_to_base_units_derived(self, ctx: BoundUnitsContext):
        """Derived unit normalizes to base SI dimensions."""
        newton = Newton.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g).is_unit.get()
        base = newton.to_base_units(g=ctx.g, tg=ctx.tg)

        assert base._extract_basis_vector() == BasisVector(
            kilogram=1, meter=1, second=-2
        )
        assert base._extract_multiplier() == 1.0
        assert base._extract_offset() == 0.0

    def test_compact_repr_with_symbol(self, ctx: BoundUnitsContext):
        """Unit with symbol returns that symbol."""
        meter = ctx.Meter.is_unit.get()
        assert meter.compact_repr() == "m"

    def test_compact_repr_first_symbol(self, ctx: BoundUnitsContext):
        """Unit with multiple symbols returns the first one."""
        ohm = ctx.Ohm.is_unit.get()
        assert ohm.compact_repr() == "Ω"

    def test_compact_repr_anonymous_unit(self, ctx: BoundUnitsContext):
        """Anonymous unit renders basis vector with superscript exponents."""
        # Order follows BasisVector field order: A, s, m, kg, K, mol, cd, rad, sr, bit
        velocity_unit = is_unit.new(
            g=ctx.g,
            tg=ctx.tg,
            vector=BasisVector(meter=1, second=-1),
            multiplier=1.0,
            offset=0.0,
        )
        assert velocity_unit.compact_repr() == "s⁻¹·m"

    def test_compact_repr_dimensionless(self, ctx: BoundUnitsContext):
        """Dimensionless anonymous unit renders as empty string."""
        dimensionless_anon = is_unit.new(
            g=ctx.g,
            tg=ctx.tg,
            vector=BasisVector(),
            multiplier=1.0,
            offset=0.0,
        )
        assert dimensionless_anon.compact_repr() == ""

    def test_compact_repr_dimensionless_with_multiplier(self, ctx: BoundUnitsContext):
        """Dimensionless with multiplier renders multiplier only (no trailing ×)."""
        scaled_dimensionless = is_unit.new(
            g=ctx.g,
            tg=ctx.tg,
            vector=BasisVector(),
            multiplier=1000.0,
            offset=0.0,
        )
        assert scaled_dimensionless.compact_repr() == "1000"

    def test_compact_repr_with_multiplier(self, ctx: BoundUnitsContext):
        """Multiplier is prefixed without trailing zeros."""
        scaled_unit = is_unit.new(
            g=ctx.g,
            tg=ctx.tg,
            vector=BasisVector(meter=1),
            multiplier=1000.0,
            offset=0.0,
        )
        assert scaled_unit.compact_repr() == "1000×m"

    def test_compact_repr_with_offset(self, ctx: BoundUnitsContext):
        """Offset wraps in parentheses without trailing zeros."""
        offset_unit = is_unit.new(
            g=ctx.g,
            tg=ctx.tg,
            vector=BasisVector(kelvin=1),
            multiplier=1.0,
            offset=273.15,
        )
        assert offset_unit.compact_repr() == "(K+273.15)"

    def test_compact_repr_with_multiplier_and_offset(self, ctx: BoundUnitsContext):
        """Both multiplier and offset render correctly."""
        scaled_offset_unit = is_unit.new(
            g=ctx.g,
            tg=ctx.tg,
            vector=BasisVector(kelvin=1),
            multiplier=0.5,
            offset=100.0,
        )
        assert scaled_offset_unit.compact_repr() == "(0.5×K+100)"

    def test_is_unit_serialize_named_unit(self, ctx: BoundUnitsContext):
        """Test that is_unit.serialize() returns the expected API format."""
        serialized = ctx.Ohm.is_unit.get().serialize()
        expected = "Ω"
        assert serialized == expected

    def test_is_unit_serialize_anonymous_unit(self, ctx: BoundUnitsContext):
        """
        Test that is_unit.serialize() returns the expected format for anonymous units.
        """
        anonymous_unit = is_unit.new(
            g=ctx.g,
            tg=ctx.tg,
            vector=BasisVector(meter=1),
            multiplier=10.0,
            offset=1.0,
        )

        expected = {
            "symbols": [],
            "basis_vector": {
                "kilogram": 0,
                "meter": 1,
                "second": 0,
                "ampere": 0,
                "kelvin": 0,
                "mole": 0,
                "candela": 0,
                "radian": 0,
                "steradian": 0,
                "bit": 0,
            },
            "multiplier": 10.0,
            "offset": 1.0,
        }

        assert anonymous_unit.serialize() == expected


class TestSymbols(_TestWithContext):
    def test_decode_symbol_base_unit(self, ctx: BoundUnitsContext):
        """Decode a base unit symbol."""
        _ = ctx.Meter
        decoded = decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol="m")

        assert decoded._extract_basis_vector() == BasisVector(meter=1)
        assert decoded._extract_multiplier() == 1.0
        assert decoded._extract_offset() == 0.0

    def test_decode_symbol_prefixed_unit(self, ctx: BoundUnitsContext):
        """Decode a prefixed unit symbol."""
        _ = ctx.Meter
        decoded = decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol="km")

        assert decoded._extract_basis_vector() == BasisVector(meter=1)
        assert decoded._extract_multiplier() == 1000.0
        assert decoded._extract_offset() == 0.0

    def test_decode_symbol_not_found(self, ctx: BoundUnitsContext):
        with pytest.raises(UnitNotFoundError):
            decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol="not_found")

    def test_decode_symbol_not_a_unit(self, ctx: BoundUnitsContext):
        with pytest.raises(UnitNotFoundError):
            decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol="m/s")

    def test_decode_symbol_invalid_prefix_for_unit(self, ctx: BoundUnitsContext):
        with pytest.raises(UnitNotFoundError):
            decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol="k%")

    @pytest.mark.parametrize(
        "symbol,expected_multiplier",
        [
            ("km", 1000.0),
            ("mm", 0.001),
            ("µm", 1e-6),
            ("um", 1e-6),
            ("nm", 1e-9),
            ("pm", 1e-12),
            ("Mm", 1e6),
            ("Gm", 1e9),
        ],
    )
    def test_decode_symbol_si_prefixes(
        self, ctx: BoundUnitsContext, symbol: str, expected_multiplier: float
    ):
        """Test decoding symbols with various SI prefixes."""
        _ = ctx.Meter
        decoded = decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol=symbol)

        assert decoded._extract_basis_vector() == BasisVector(meter=1)
        assert decoded._extract_multiplier() == pytest.approx(expected_multiplier)

    @pytest.mark.parametrize(
        "symbol,expected_multiplier",
        [
            ("Kibit", 2**10),
            ("Mibit", 2**20),
            ("Gibit", 2**30),
            ("Tibit", 2**40),
        ],
    )
    def test_decode_symbol_binary_prefixes(
        self, ctx: BoundUnitsContext, symbol: str, expected_multiplier: float
    ):
        """Test decoding symbols with binary prefixes for units that support them."""
        _ = Bit.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        decoded = decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol=symbol)

        assert decoded._extract_basis_vector() == BasisVector(bit=1)
        assert decoded._extract_multiplier() == pytest.approx(expected_multiplier)

    @pytest.mark.parametrize(
        "symbol,expected_multiplier",
        [
            ("KiB", 8 * 2**10),
            ("MiB", 8 * 2**20),
            ("GiB", 8 * 2**30),
            ("TiB", 8 * 2**40),
        ],
    )
    def test_decode_symbol_binary_prefixes_dervied(
        self, ctx: BoundUnitsContext, symbol: str, expected_multiplier: float
    ):
        """
        Test decoding symbols with binary prefixes for derived units that support them.
        """
        _ = Byte.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        decoded = decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol=symbol)

        assert decoded._extract_basis_vector() == BasisVector(bit=1)
        assert decoded.get_conversion_to(ctx.Bit.is_unit.get()) == (
            expected_multiplier,
            0.0,
        )
        assert decoded._extract_multiplier() == pytest.approx(expected_multiplier)

    def test_decode_symbol_invalid_binary_prefix_for_si_only(
        self, ctx: BoundUnitsContext
    ):
        """Test that SI-only units reject binary prefixes."""
        _ = ctx.Meter
        # Meter supports SI prefixes but not binary prefixes
        with pytest.raises(UnitNotFoundError):
            decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol="Kim")

    def test_decode_symbol_invalid_prefix_for_non_prefixed_unit(
        self, ctx: BoundUnitsContext
    ):
        """Test that units without prefix traits reject all prefixes."""
        _ = ctx.Degree
        # Degree does not have SI or binary prefix traits
        with pytest.raises(UnitNotFoundError):
            decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol="kdeg")
        with pytest.raises(UnitNotFoundError):
            decode_symbol_runtime(g=ctx.g, tg=ctx.tg, symbol="mdeg")


class TestUnitExpressions(_TestWithContext):
    def test_affine_unit_in_expression_raises(self, ctx: BoundUnitsContext):
        """
        Test that affine units (non-zero offset) raise error in compound expressions.
        Error is raised during UnitExpressionFactory creation (early detection).
        """
        celsius = ctx.DegreeCelsius.is_unit.get()
        assert celsius.is_affine

        # Error should be raised during factory creation, not at runtime
        with pytest.raises(UnitExpressionError):
            UnitExpressionFactory(("degC·m",), ((DegreeCelsius, 1), (Meter, 1)))

    def test_resolve_basic_unit(self, ctx: BoundUnitsContext):
        """Test that a simple unit expression (Meter^1) resolves correctly."""
        MeterExpr = UnitExpressionFactory(("m", "meter"), ((Meter, 1),))

        class App(fabll.Node):
            meter_expr = MeterExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        resolved = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.meter_expr.get().instance
        )

        unit = resolved.get_trait(is_unit)
        assert unit._extract_basis_vector() == BasisVector(meter=1)
        assert unit._extract_multiplier() == 1.0

    def test_resolve_derived_unit(self, ctx: BoundUnitsContext):
        """Test that derived units (Meter * Second^-1) resolve correctly."""
        VelocityExpr = UnitExpressionFactory(("m/s",), ((Meter, 1), (Second, -1)))

        class App(fabll.Node):
            velocity_expr = VelocityExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        resolved = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.velocity_expr.get().instance
        )

        unit = resolved.get_trait(is_unit)
        assert unit._extract_basis_vector() == BasisVector(meter=1, second=-1)
        assert unit._extract_multiplier() == 1.0

    def test_resolve_scaled_unit(self, ctx: BoundUnitsContext):
        """Test that expressions with scaled units resolve with correct multiplier."""
        KilometerExpr = UnitExpressionFactory(("km",), ((Meter, 1),), multiplier=1000.0)

        class App(fabll.Node):
            km_expr = KilometerExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        resolved = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.km_expr.get().instance
        )

        unit = resolved.get_trait(is_unit)
        assert unit._extract_basis_vector() == BasisVector(meter=1)
        assert unit._extract_multiplier() == 1000.0

    def test_resolve_compound_prefixed_unit(self, ctx: BoundUnitsContext):
        """Test expressions mixing prefixed and base units (km/h)."""
        KilometerExpr = UnitExpressionFactory(("km",), ((Meter, 1),), multiplier=1000.0)
        KilometersPerHourExpr = UnitExpressionFactory(
            ("km/h", "kph"), ((KilometerExpr, 1), (Hour, -1))
        )

        class App(fabll.Node):
            kmh_expr = KilometersPerHourExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        resolved = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.kmh_expr.get().instance
        )

        unit = resolved.get_trait(is_unit)
        assert unit._extract_basis_vector() == BasisVector(meter=1, second=-1)
        # km/h = 1000m / 3600s
        assert unit._extract_multiplier() == pytest.approx(1000.0 / 3600.0)

    def test_resolve_manual_divide(self, ctx: BoundUnitsContext):
        """Test that manually constructed Divide expressions resolve correctly."""
        divide = (
            F.Expressions.Divide.bind_typegraph(tg=ctx.tg)
            .create_instance(g=ctx.g)
            .setup(ctx.Meter, ctx.Second)  # type: ignore[arg-type]
        )

        result = _UnitExpressionResolver(g=ctx.g, tg=ctx.tg).visit_divide(divide)
        assert result._extract_basis_vector() == BasisVector(meter=1, second=-1)
        assert result._extract_multiplier() == 1.0

    def test_resolve_manual_power(self, ctx: BoundUnitsContext):
        """Test that manually constructed Power expressions resolve correctly."""
        exponent_param = ctx.NumericParameter.setup(
            is_unit=ctx.Dimensionless.is_unit.get()
        )

        exponent_param.alias_to_literal(
            g=ctx.g,
            value=ctx.literals.Numbers.setup_from_singleton(
                value=2.0, unit=ctx.Dimensionless.is_unit.get()
            ),
        )

        power = (
            F.Expressions.Power.bind_typegraph(tg=ctx.tg)
            .create_instance(g=ctx.g)
            .setup(ctx.Meter, exponent_param)  # type: ignore[arg-type]
        )

        result = _UnitExpressionResolver(g=ctx.g, tg=ctx.tg).visit_power(power)
        assert result._extract_basis_vector() == BasisVector(meter=2)
        assert result._extract_multiplier() == 1.0

    def test_unit_expression_multiplier(self, ctx: BoundUnitsContext):
        """Test that multiplier on UnitExpression is correctly applied."""
        ScaledMeterExpr = UnitExpressionFactory(
            ("km",), ((Meter, 1),), multiplier=1000.0
        )

        class App(fabll.Node):
            scaled_expr = ScaledMeterExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        resolved = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.scaled_expr.get().instance
        )

        assert resolved.get_trait(is_unit)._extract_multiplier() == 1000.0

    def test_resolve_unit_expression_with_offset_raises(self, ctx: BoundUnitsContext):
        """Test that UnitExpression with non-zero offset raises error."""
        OffsetExpr = UnitExpressionFactory(("m", "meter"), ((Meter, 1),), offset=10.0)

        class App(fabll.Node):
            offset_expr = OffsetExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)

        with pytest.raises(UnitExpressionError):
            resolve_unit_expression(
                tg=ctx.tg, g=ctx.g, expr=app.offset_expr.get().instance
            )

    def test_resolve_non_integer_exponent_raises(self, ctx: BoundUnitsContext):
        """Test that non-integer exponents raise UnitExpressionError."""
        exponent_param = ctx.NumericParameter.setup(
            is_unit=ctx.Dimensionless.is_unit.get()
        )
        exponent_param.alias_to_literal(
            g=ctx.g,
            value=ctx.literals.Numbers.setup_from_singleton(
                value=1.5, unit=ctx.Dimensionless.is_unit.get()
            ),
        )

        power = (
            F.Expressions.Power.bind_typegraph(tg=ctx.tg)
            .create_instance(g=ctx.g)
            .setup(base=ctx.Meter, exponent=exponent_param)  # type: ignore[arg-type]
        )

        resolver = _UnitExpressionResolver(g=ctx.g, tg=ctx.tg)
        with pytest.raises(UnitExpressionError):
            resolver.visit_power(power)

    def test_resolve_dimensionless_expression(self, ctx: BoundUnitsContext):
        """Test that dimensionless results (e.g., Meter / Meter) are handled."""
        MeterOverMeterExpr = UnitExpressionFactory(("m/m",), ((Meter, 1), (Meter, -1)))

        class App(fabll.Node):
            dimensionless_expr = MeterOverMeterExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        resolved = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.dimensionless_expr.get().instance
        )

        unit = resolved.get_trait(is_unit)
        assert unit._extract_basis_vector() == _BasisVector.ORIGIN
        assert unit.is_dimensionless()


class TestResolvePendingParameterUnits(_TestWithContext):
    """Tests for instance-level unit inference."""

    def test_resolve_param_unit_from_literal(self, ctx: BoundUnitsContext):
        """Test resolving unit from a literal constraint."""
        param = ctx.NumericParameter

        # Initially no has_unit on the parameter
        # (Note: In real use, parameter would be created without unit)
        # For this test, we verify the resolver can find and attach units

        # Create a literal with Volt unit
        lit = ctx.literals.Numbers.setup_from_singleton(
            value=5.0, unit=ctx.Volt.is_unit.get()
        )

        # Constrain param to literal via Is
        F.Expressions.Is.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g).setup(
            param.can_be_operand.get(),
            lit.is_literal.get().as_operand.get(),
            assert_=True,
        )

        # The literal should have has_unit
        assert lit.try_get_trait(has_unit) is not None

    def test_resolve_add_expression_units(self, ctx: BoundUnitsContext):
        """Test that Add expressions return commensurable unit."""
        resolver = _UnitExpressionResolver(g=ctx.g, tg=ctx.tg)

        add_expr = (
            F.Expressions.Add.bind_typegraph(tg=ctx.tg)
            .create_instance(g=ctx.g)
            .setup(ctx.Meter, ctx.Meter)  # type: ignore[arg-type]
        )

        result = resolver.visit_additive(add_expr)
        assert result._extract_basis_vector() == BasisVector(meter=1)

    def test_resolve_add_incommensurable_raises(self, ctx: BoundUnitsContext):
        """Test that Add with incommensurable units raises error."""
        resolver = _UnitExpressionResolver(g=ctx.g, tg=ctx.tg)

        add_expr = (
            F.Expressions.Add.bind_typegraph(tg=ctx.tg)
            .create_instance(g=ctx.g)
            .setup(ctx.Meter, ctx.Second)  # type: ignore[arg-type]
        )

        with pytest.raises(UnitsNotCommensurableError):
            resolver.visit_additive(add_expr)
