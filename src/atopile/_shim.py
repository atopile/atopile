"""
This file exists to tide designs over from v0.2 to v0.3.

It will be removed in v0.4.
"""

import logging
import re
from typing import Type

from more_itertools import first

import faebryk.core.parameter as fab_param
import faebryk.library._F as F
import faebryk.libs.library.L as L
from atopile import address
from faebryk.libs.exceptions import DeprecatedException, downgrade
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P
from faebryk.libs.util import has_attr_or_property, write_only_property

# Helpers for auto-upgrading on merge of the https://github.com/atopile/atopile/pull/522
try:
    from faebryk.libs.units import UnitCompatibilityError, dimensionless  # type: ignore
except ImportError:

    class UnitCompatibilityError(Exception):
        """Placeholder Exception"""

    dimensionless = P.dimensionless

try:
    from faebryk.libs.library.L import Range  # type: ignore
except ImportError:
    from faebryk.library._F import Range  # type: ignore

try:
    from faebryk.library import Single  # type: ignore  # noqa: F401
except ImportError:
    pass  # type: ignore


log = logging.getLogger(__name__)


def _alias_is(lh, rh):
    try:
        return lh.alias_is(rh)
    except AttributeError:
        return lh.merge(rh)


shim_map: dict[address.AddrStr, tuple[Type[L.Module], str]] = {}


def _register_shim(addr: address.AddrStr, preferred: str):
    def _wrapper(cls: Type[L.Module]):
        shim_map[addr] = cls, preferred
        return cls

    return _wrapper


def _is_int(name: str) -> bool:
    try:
        int(name)
    except ValueError:
        return False
    return True


class _has_kicad_footprint_name_defined(F.has_footprint_impl):
    """
    This trait defers footprint creation until it's needed,
    which means we can construct the underlying pin map
    """

    def __init__(self, lib_reference: str, pinmap: dict[str, F.Electrical]):
        super().__init__()
        if ":" not in lib_reference:
            # TODO: default to a lib reference starting with "lib:"
            # for backwards compatibility with old footprints
            lib_reference = f"lib:{lib_reference}"
        self.lib_reference = lib_reference
        self.pinmap = pinmap

    def _try_get_footprint(self) -> F.Footprint | None:
        if fps := self.obj.get_children(direct_only=True, types=F.Footprint):
            return first(fps)
        else:
            return None

    def get_footprint(self) -> F.Footprint:
        if fp := self._try_get_footprint():
            return fp
        else:
            fp = F.KicadFootprint(
                self.lib_reference,
                pin_names=list(self.pinmap.keys()),
            )
            fp.get_trait(F.can_attach_via_pinmap).attach(self.pinmap)
            self.set_footprint(fp)
            return fp

    def handle_duplicate(
        self, old: "_has_kicad_footprint_name_defined", _: fab_param.Node
    ) -> bool:
        if old._try_get_footprint():
            raise RuntimeError("Too late to set footprint")

        # Update the existing trait...
        old.lib_reference = self.lib_reference
        # ... and we don't need to attach the new
        assert old.pinmap is self.pinmap, "Pinmap reference mismatch"
        return False


class Component(L.Module):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pinmap = {}

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(self.pinmap)

    @L.rt_field
    def has_designator_prefix(self):
        return F.has_designator_prefix_defined(F.has_designator_prefix.Prefix.U)

    def add_pin(self, name: str) -> F.Electrical:
        if _is_int(name):
            py_name = f"_{name}"
        else:
            py_name = name

        # TODO: @v0.4: remove this
        if has_attr_or_property(self, py_name):
            log.warning(
                f"Deprecated: Pin {name} already exists, skipping."
                " In the future this will be an error."
            )
            mif = getattr(self, py_name)
        elif py_name in self.runtime:
            mif = self.runtime[py_name]
        else:
            mif = self.add(F.Electrical(), name=py_name)

        self.pinmap[name] = mif
        return mif

    @write_only_property
    def mpn(self, value: str):
        # handles duplicates gracefully
        self.add(
            F.has_descriptive_properties_defined({DescriptiveProperties.partno: value})
        )

        # TODO: @v0.4: remove this - mpn != lcsc id
        if re.match(r"C[0-9]+", value):
            self.add(F.has_descriptive_properties_defined({"LCSC": value}))
            with downgrade(DeprecatedException):
                raise DeprecatedException(
                    "mpn is deprecated for assignment of LCSC IDs, use lcsc_id instead"
                )

    @write_only_property
    def footprint(self, value: str):
        self.add(_has_kicad_footprint_name_defined(value, self.pinmap))


# FIXME: this would ideally be some kinda of mixin,
# however, we can't have multiple bases for Nodes
class ModuleShims(L.Module):
    @write_only_property
    def lcsc_id(self, value: str):
        # handles duplicates gracefully
        self.add(F.has_descriptive_properties_defined({"LCSC": value}))

    @write_only_property
    def manufacturer(self, value: str):
        # handles duplicates gracefully
        self.add(
            F.has_descriptive_properties_defined(
                {DescriptiveProperties.manufacturer: value}
            )
        )

    @write_only_property
    def mpn(self, value: str):
        # handles duplicates gracefully
        self.add(
            F.has_descriptive_properties_defined({DescriptiveProperties.partno: value})
        )

    @write_only_property
    def designator_prefix(self, value: str):
        self.add(F.has_designator_prefix_defined(value))

    @write_only_property
    def package(self, value: str):
        self.add(F.has_footprint_requirement_defined(footprint=value))


@_register_shim("generics/resistors.ato:Resistor", "import Resistor")
class _ShimResistor(F.Resistor):
    """Temporary shim to translate `value` to `resistance`."""

    def __init__(self, *args, **kwargs):
        log.warning(
            "Deprecated: generics/resistors.ato:Resistor is deprecated, use"
            ' "import Resistor" instead.'
        )
        super().__init__(*args, **kwargs)

    @property
    def value(self) -> Range:
        return self.resistance

    @value.setter
    def value(self, value: Range):
        _alias_is(self.resistance, value)

    @write_only_property
    def footprint(self, value: str):
        if value.startswith("R"):
            value = value[1:]
        self.package = value

    @write_only_property
    def package(self, value: str):
        reqs = [(value, 2)]  # package, pin-count
        self.add(F.has_footprint_requirement_defined(reqs))

    @property
    def p1(self) -> F.Electrical:
        return self.unnamed[0]

    @property
    def p2(self) -> F.Electrical:
        return self.unnamed[1]

    @property
    def _1(self) -> F.Electrical:
        return self.unnamed[0]

    @property
    def _2(self) -> F.Electrical:
        return self.unnamed[1]


@_register_shim("generics/capacitors.ato:Capacitor", "import Capacitor")
class _ShimCapacitor(F.Capacitor):
    """Temporary shim to translate `value` to `capacitance`."""

    def __init__(self, *args, **kwargs):
        log.warning(
            "Deprecated: generics/capacitors.ato:Capacitor is deprecated, use"
            ' "import Capacitor" instead.'
        )
        super().__init__(*args, **kwargs)

    class has_power(L.ModuleInterface.TraitT.decless()):
        power: F.ElectricPower

    @property
    def value(self) -> Range:
        return self.capacitance

    @value.setter
    def value(self, value: Range):
        _alias_is(self.capacitance, value)

    @write_only_property
    def footprint(self, value: str):
        if value.startswith("C"):
            value = value[1:]
        self.package = value

    @write_only_property
    def package(self, value: str):
        reqs = [(value, 2)]  # package, pin-count
        self.add(F.has_footprint_requirement_defined(reqs))

    @property
    def p1(self) -> F.Electrical:
        return self.unnamed[0]

    @property
    def p2(self) -> F.Electrical:
        return self.unnamed[1]

    @property
    def _1(self) -> F.Electrical:
        return self.unnamed[0]

    @property
    def _2(self) -> F.Electrical:
        return self.unnamed[1]

    @property
    def power(self) -> F.ElectricPower:
        if trait := self.try_get_trait(self.has_power):
            return trait.power
        else:
            return self.add(self.has_power()).power


@_register_shim("generics/interfaces.ato:Power", "import ElectricPower")
class _ShimPower(F.ElectricPower):
    """Temporary shim to translate `value` to `power`."""

    def __init__(self, *args, **kwargs):
        log.warning(
            "Deprecated: generics/interfaces.ato:Power is deprecated, use"
            ' "import ElectricPower" instead.'
        )
        super().__init__(*args, **kwargs)

    @property
    def vcc(self) -> F.Electrical:
        return self.hv

    @property
    def gnd(self) -> F.Electrical:
        return self.lv
