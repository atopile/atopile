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
from typing import ClassVar, Self

import pytest
from dataclasses_json import DataClassJsonMixin

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.core.zig.gen.faebryk import typegraph
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.libs.util import not_none, once


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


class _BasisVector(fabll.Node):
    ORIGIN: ClassVar[BasisVector] = BasisVector()

    @classmethod
    def MakeChild(cls, vector: BasisVector) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
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

    def setup(  # type: ignore[invalid-method-override]
        self, vector: BasisVector
    ) -> Self:
        from faebryk.library.Literals import Counts

        g = self.g
        tg = self.tg

        for field_name in BasisVector.__dataclass_fields__.keys():
            child = Counts.bind_typegraph(tg=tg).create_instance(g=g)
            child.setup_from_values(values=[getattr(vector, field_name)])
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


class is_unit(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    _symbol_identifier: ClassVar[str] = "symbol"
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
    """
    Multiplier to apply when converting to SI base units.
    """

    _offset_identifier: ClassVar[str] = "offset"
    """
    Offset to apply when converting to SI base units.
    """

    @classmethod
    def MakeChild(  # type: ignore[invalid-method-override]
        cls,
        symbols: list[str],
        unit_vector: BasisVector,
        multiplier: float = 1.0,
        offset: float = 0.0,
    ) -> fabll._ChildField[Self]:
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
    def MakeChild_Empty(cls) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
        return fabll._ChildField(cls)

    def _extract_multiplier(self) -> float:
        multiplier_numeric = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._multiplier_identifier
        )
        assert multiplier_numeric is not None
        from faebryk.library.Literals import NumericInterval

        return NumericInterval.bind_instance(multiplier_numeric).get_single()

    def _extract_offset(self) -> float:
        offset_numeric = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._offset_identifier
        )
        assert offset_numeric is not None
        from faebryk.library.Literals import NumericInterval

        return NumericInterval.bind_instance(offset_numeric).get_single()

    def _extract_symbols(self) -> list[str]:
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

    def setup(  # type: ignore[invalid-method-override]
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
            .setup_from_singleton(value=multiplier)
        )
        _ = EdgeComposition.add_child(
            bound_node=self.instance,
            child=multiplier_numeric.instance.node(),
            child_identifier=self._multiplier_identifier,
        )
        offset_numeric = (
            NumericInterval.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_singleton(value=offset)
        )
        _ = EdgeComposition.add_child(
            bound_node=self.instance,
            child=offset_numeric.instance.node(),
            child_identifier=self._offset_identifier,
        )
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

        return unit.is_unit.get()

    def scaled_copy(
        self, g: graph.GraphView, tg: graph.TypeGraph, multiplier: float
    ) -> "is_unit":
        return self.new(
            g=g,
            tg=tg,
            vector=self._extract_basis_vector(),
            multiplier=multiplier * self._extract_multiplier(),
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
    unit = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(cls, unit: type[fabll.NodeT]) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
        out = fabll._ChildField(cls)
        unit_field = unit.MakeChild()
        out.add_dependant(unit_field)
        out.add_dependant(F.Collections.Pointer.MakeEdge([out, cls.unit], [unit_field]))
        return out

    def setup(self, unit: is_unit) -> Self:  # type: ignore[invalid-method-override]
        unit_node = fabll.Traits(unit).get_obj_raw()
        self.unit.get().point(unit_node)
        return self

    def get_is_unit(self) -> is_unit:
        return self.unit.get().deref().get_trait(is_unit)


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


def decode_symbol(g: graph.GraphView, tg: typegraph.TypeGraph, symbol: str) -> is_unit:
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


_UNIT_SYMBOLS: dict[_UnitRegistry, list[str]] = {
    # prefereed unit for display comes first (must be valid with prefixes)
    _UnitRegistry.Dimensionless: ["dimensionless"],  # TODO: allow None?
    _UnitRegistry.Percent: ["%"],
    _UnitRegistry.Ppm: ["ppm"],
    _UnitRegistry.Ampere: ["A", "ampere"],
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
    _UnitRegistry.Watt: ["W", "watt"],
    _UnitRegistry.Coulomb: ["C"],
    _UnitRegistry.Volt: ["V", "volt"],
    _UnitRegistry.Farad: ["F", "farad"],
    _UnitRegistry.Ohm: ["Ω", "ohm"],
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
    _UnitRegistry.Bit: ["b", "bit"],
    _UnitRegistry.Byte: ["B", "byte"],
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
    _UnitRegistry.Rpm: ["rpm", "RPM"],
}


class Dimensionless(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = _BasisVector.ORIGIN

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Dimensionless], unit_vector_arg)
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
    _multiplier_identifier: ClassVar[str] = "multiplier"
    _offset_identifier: ClassVar[str] = "offset"

    _unit_vector_arg: ClassVar[tuple[tuple[type[fabll.Node], int], ...]] = ()
    _multiplier_arg: ClassVar[float] = 1.0
    _offset_arg: ClassVar[float] = 0.0

    expr = F.Collections.Pointer.MakeChild()

    def get_expr(self) -> fabll.Node:
        return self.expr.get().deref()

    def get_multiplier(self) -> float:
        multiplier_child = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._multiplier_identifier
        )
        return F.Literals.Numbers.bind_instance(not_none(multiplier_child)).get_single()

    def get_offset(self) -> float:
        offset_child = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._offset_identifier
        )
        return F.Literals.Numbers.bind_instance(not_none(offset_child)).get_single()

    def setup(self, expr_type: type["UnitExpression"]) -> Self:  # type: ignore[invalid-method-override]
        from faebryk.library.Expressions import Multiply, Power

        g = self.g
        tg = self.tg

        term_nodes: list[fabll.Node] = []
        for unit_type, exponent in expr_type._unit_vector_arg:
            unit_instance = unit_type.bind_typegraph(tg=tg).create_instance(g=g)

            exponent_param = (
                F.Parameters.NumericParameter.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .setup(
                    units=Dimensionless.bind_typegraph(tg=tg)
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
                .setup(base=unit_instance, exponent=exponent_param)  # type: ignore[arg-type]
            )
            term_nodes.append(power_node)

        multiply_node = Multiply.bind_typegraph(tg=tg).create_instance(g=g)
        multiply_node.operands.get().append(*term_nodes)

        self.expr.get().point(multiply_node)

        return self

    @classmethod
    def MakeChild(cls) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
        from faebryk.library.Expressions import Multiply, Power

        out = fabll._ChildField(cls)
        term_fields = []

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
            exponent_is_expr = F.Expressions.Is.MakeChild_Constrain(
                [[exponent_field], [exponent_lit]]
            )
            exponent_is_expr.add_dependant(exponent_lit, identifier="lit", before=True)
            out.add_dependant(exponent_is_expr)

            term_field = Power.MakeChild_FromOperands(unit_field, exponent_field)
            out.add_dependant(term_field)
            term_fields.append(term_field)

        expr_field = Multiply.MakeChild_FromOperands(*term_fields)
        out.add_dependant(expr_field)
        out.add_dependant(F.Collections.Pointer.MakeEdge([out, cls.expr], [expr_field]))

        return out


@once
def UnitExpressionFactory(
    unit_vector: UnitVectorT, multiplier: float = 1.0, offset: float = 0.0
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

    return ConcreteUnitExpr


class _AnonymousUnit(fabll.Node):
    is_unit = fabll.Traits.MakeEdge(is_unit.MakeChild_Empty())

    def setup(  # type: ignore[invalid-method-override]
        self, vector: BasisVector, multiplier: float = 1.0, offset: float = 0.0
    ) -> Self:
        self.is_unit.get().setup(
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

        exponent_val = exponent_lit.cast(F.Literals.Numbers).get_single()

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


# SI base units ------------------------------------------------------------------------


class Ampere(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(ampere=1)

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Ampere], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Meter(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=1)

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Meter], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Kilogram(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1)

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Kilogram], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())


class Second(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Second], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Kelvin(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kelvin=1)

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Kelvin], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Mole(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(mole=1)

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Mole], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Candela(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(candela=1)

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Candela], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# SI coherent derived units ------------------------------------------------------------


class Radian(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Radian], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Steradian(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(steradian=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Steradian], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Hertz(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=-1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Hertz], unit_vector_arg)
    )
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Newton(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1, meter=1, second=-2)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Newton], unit_vector_arg)
    )
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Pascal(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=-1, second=-2
    )

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Pascal], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Joule(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1, meter=2, second=-2)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Joule], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Watt(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1, meter=2, second=-3)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Watt], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Coulomb(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(ampere=1, second=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Coulomb], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Volt(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-3, ampere=-1
    )

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Volt], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Farad(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=-1, meter=-2, second=4, ampere=2
    )

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Farad], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Ohm(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-3, ampere=-2
    )

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Ohm], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Siemens(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=-1, meter=-2, second=3, ampere=2
    )

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Siemens], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Weber(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-2, ampere=-1
    )

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Weber], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Tesla(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, second=-2, ampere=-1
    )

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Tesla], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Henry(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        kilogram=1, meter=2, second=-2, ampere=-2
    )

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Henry], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    _is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class DegreeCelsius(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kelvin=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.DegreeCelsius],
            unit_vector_arg,
            offset=273.15,
        )
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Lumen(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(candela=1, steradian=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Lumen], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Lux(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(
        candela=1, steradian=1, meter=-2
    )

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Lux], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# TODO: prevent mixing with Hertz via context/domain tagging system?
class Becquerel(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=-1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Becquerel], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Gray(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=2, second=-2)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Gray], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Sievert(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=2, second=-2)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Sievert], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class Katal(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(mole=1, second=-1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Katal], unit_vector_arg)
    )
    is_si_unit = fabll.Traits.MakeEdge(is_si_unit.MakeChild())
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# SI patches ---------------------------------------------------------------------------


class Gram(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(kilogram=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Gram], unit_vector_arg, multiplier=1e-3
        )
    )
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


# non-SI base units --------------------------------------------------------------------


class Bit(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(bit=1)

    is_base_unit = fabll.Traits.MakeEdge(is_base_unit.MakeChild())
    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Bit], unit_vector_arg)
    )
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())
    is_binary_prefixed = fabll.Traits.MakeEdge(is_binary_prefixed_unit.MakeChild())


# Dimensionless scalar multiples -------------------------------------------------------


class Percent(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = _BasisVector.ORIGIN

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Percent], unit_vector_arg, multiplier=1e-2
        )
    )


class Ppm(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = _BasisVector.ORIGIN

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ppm], unit_vector_arg, multiplier=1e-6
        )
    )


# Common non-SI multiples --------------------------------------------------------------


class Degree(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Degree],
            unit_vector_arg,
            multiplier=math.pi / 180.0,
        )
    )


class ArcMinute(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.ArcMinute],
            unit_vector_arg,
            multiplier=math.pi / 180.0 / 60.0,
        )
    )


class ArcSecond(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.ArcSecond],
            unit_vector_arg,
            multiplier=math.pi / 180.0 / 3600.0,
        )
    )


class Minute(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Minute], unit_vector_arg, multiplier=60.0
        )
    )


class Hour(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Hour], unit_vector_arg, multiplier=3600.0
        )
    )


class Day(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Day], unit_vector_arg, multiplier=24 * 3600.0
        )
    )


class Week(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Week],
            unit_vector_arg,
            multiplier=7 * 24 * 3600.0,
        )
    )


class Month(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Month],
            unit_vector_arg,
            multiplier=(365.25 / 12) * 24 * 3600.0,
        )
    )


class Year(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(second=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Year],
            unit_vector_arg,
            multiplier=365.25 * 24 * 3600.0,
        )
    )


class Liter(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(meter=3)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Liter], unit_vector_arg, multiplier=1e-3
        )
    )
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


class RPM(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(radian=1, second=-1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Rpm],
            unit_vector_arg,
            multiplier=(2 * math.pi) / 60.0,
        )
    )


class Byte(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(bit=1)

    is_unit = is_unit.MakeChild(
        _UNIT_SYMBOLS[_UnitRegistry.Byte], unit_vector_arg, multiplier=8.0
    )
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())
    is_binary_prefixed = fabll.Traits.MakeEdge(is_binary_prefixed_unit.MakeChild())


# Shortcuts for use elsewhere in the standard library ---------------------------------


class BitsPerSecond(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(bit=1, second=-1)

    is_unit = fabll.Traits.MakeEdge(is_unit.MakeChild([], unit_vector_arg))
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())
    is_binary_prefixed = fabll.Traits.MakeEdge(is_binary_prefixed_unit.MakeChild())


class AmpereHour(fabll.Node):
    unit_vector_arg: ClassVar[BasisVector] = BasisVector(ampere=1, second=1)

    is_unit = fabll.Traits.MakeEdge(
        is_unit.MakeChild([], unit_vector_arg, multiplier=3600.0)
    )
    is_si_prefixed = fabll.Traits.MakeEdge(is_si_prefixed_unit.MakeChild())


VoltsPerSecond = UnitExpressionFactory(((Volt, 1), (Second, -1)))


# Logarithmic units --------------------------------------------------------------------
# TODO: logarithmic units


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
                        f"`{item.__repr__()}` ({symbols[i]})"
                        for i, item in enumerate(items)
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

        MetersPerSecondExpr = UnitExpressionFactory(((Meter, 1), (Second, -1)))
        KilometerExpr = UnitExpressionFactory(((Meter, 1),), multiplier=1000)
        KilometersPerHourExpr = UnitExpressionFactory(((KilometerExpr, 1), (Hour, -1)))

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
        MetersPerSecondExpr = UnitExpressionFactory(((Meter, 1), (Second, -1)))
        MeterSecondsExpr = UnitExpressionFactory(((Meter, 1), (Second, 1)))

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
        meter = decode_symbol(g=ctx.g, tg=ctx.tg, symbol="m")
        kilometer = decode_symbol(g=ctx.g, tg=ctx.tg, symbol="km")

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
        kilometer = decode_symbol(g=ctx.g, tg=ctx.tg, symbol="km")
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
        decoded = decode_symbol(g=ctx.g, tg=ctx.tg, symbol="m")

        assert decoded._extract_basis_vector() == BasisVector(meter=1)
        assert decoded._extract_multiplier() == 1.0
        assert decoded._extract_offset() == 0.0

    def test_decode_symbol_prefixed_unit(self, ctx: BoundUnitsContext):
        """Decode a prefixed unit symbol."""
        _ = ctx.Meter
        decoded = decode_symbol(g=ctx.g, tg=ctx.tg, symbol="km")

        assert decoded._extract_basis_vector() == BasisVector(meter=1)
        assert decoded._extract_multiplier() == 1000.0
        assert decoded._extract_offset() == 0.0

    def test_decode_symbol_not_found(self, ctx: BoundUnitsContext):
        with pytest.raises(UnitNotFoundError):
            decode_symbol(g=ctx.g, tg=ctx.tg, symbol="not_found")

    def test_decode_symbol_not_a_unit(self, ctx: BoundUnitsContext):
        with pytest.raises(UnitNotFoundError):
            decode_symbol(g=ctx.g, tg=ctx.tg, symbol="m/s")

    def test_decode_symbol_invalid_prefix_for_unit(self, ctx: BoundUnitsContext):
        with pytest.raises(UnitNotFoundError):
            decode_symbol(g=ctx.g, tg=ctx.tg, symbol="k%")

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
        decoded = decode_symbol(g=ctx.g, tg=ctx.tg, symbol=symbol)

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
        decoded = decode_symbol(g=ctx.g, tg=ctx.tg, symbol=symbol)

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
        decoded = decode_symbol(g=ctx.g, tg=ctx.tg, symbol=symbol)

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
            decode_symbol(g=ctx.g, tg=ctx.tg, symbol="Kim")

    def test_decode_symbol_invalid_prefix_for_non_prefixed_unit(
        self, ctx: BoundUnitsContext
    ):
        """Test that units without prefix traits reject all prefixes."""
        _ = ctx.Degree
        # Degree does not have SI or binary prefix traits
        with pytest.raises(UnitNotFoundError):
            decode_symbol(g=ctx.g, tg=ctx.tg, symbol="kdeg")
        with pytest.raises(UnitNotFoundError):
            decode_symbol(g=ctx.g, tg=ctx.tg, symbol="mdeg")


class TestUnitExpressions(_TestWithContext):
    def test_affine_unit_in_expression_raises(self, ctx: BoundUnitsContext):
        """
        Test that affine units (non-zero offset) raise error in compound expressions.
        """
        celsius = ctx.DegreeCelsius.is_unit.get()
        assert celsius.is_affine

        CelsiusExpr = UnitExpressionFactory(((DegreeCelsius, 1),))

        class App(fabll.Node):
            celsius_expr = CelsiusExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)

        with pytest.raises(UnitExpressionError):
            resolve_unit_expression(
                tg=ctx.tg, g=ctx.g, expr=app.celsius_expr.get().instance
            )

    def test_resolve_basic_unit(self, ctx: BoundUnitsContext):
        """Test that a simple unit expression (Meter^1) resolves correctly."""
        MeterExpr = UnitExpressionFactory(((Meter, 1),))

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
        VelocityExpr = UnitExpressionFactory(((Meter, 1), (Second, -1)))

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
        KilometerExpr = UnitExpressionFactory(((Meter, 1),), multiplier=1000.0)

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
        KilometerExpr = UnitExpressionFactory(((Meter, 1),), multiplier=1000.0)
        KilometersPerHourExpr = UnitExpressionFactory(((KilometerExpr, 1), (Hour, -1)))

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
            units=ctx.Dimensionless.is_unit.get()
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
        ScaledMeterExpr = UnitExpressionFactory(((Meter, 1),), multiplier=1000.0)

        class App(fabll.Node):
            scaled_expr = ScaledMeterExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        resolved = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.scaled_expr.get().instance
        )

        assert resolved.get_trait(is_unit)._extract_multiplier() == 1000.0

    def test_resolve_unit_expression_with_offset_raises(self, ctx: BoundUnitsContext):
        """Test that UnitExpression with non-zero offset raises error."""
        OffsetExpr = UnitExpressionFactory(((Meter, 1),), offset=10.0)

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
            units=ctx.Dimensionless.is_unit.get()
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
        MeterOverMeterExpr = UnitExpressionFactory(((Meter, 1), (Meter, -1)))

        class App(fabll.Node):
            dimensionless_expr = MeterOverMeterExpr.MakeChild()

        app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
        resolved = resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.dimensionless_expr.get().instance
        )

        unit = resolved.get_trait(is_unit)
        assert unit._extract_basis_vector() == _BasisVector.ORIGIN
        assert unit.is_dimensionless()
