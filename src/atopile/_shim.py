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
from faebryk.core.trait import TraitImpl, TraitNotFound
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.util import write_only_property

log = logging.getLogger(__name__)


shim_map: dict[address.AddrStr, tuple[Type[L.Node], str]] = {}


def _register_shim(addr: str | address.AddrStr, preferred: str):
    def _wrapper[T: Type[L.Node]](cls: T) -> T:
        shim_map[address.AddrStr(addr)] = cls, preferred
        return cls

    return _wrapper


def _is_int(name: str) -> bool:
    try:
        int(name)
    except ValueError:
        return False
    return True


class has_local_kicad_footprint_named_defined(F.has_footprint_impl):
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
        self, old: "has_local_kicad_footprint_named_defined", _: fab_param.Node
    ) -> bool:
        if old._try_get_footprint():
            raise RuntimeError("Too late to set footprint")

        # Update the existing trait...
        old.lib_reference = self.lib_reference
        # ... and we don't need to attach the new
        assert old.pinmap is self.pinmap, "Pinmap reference mismatch"
        return False


class has_ato_cmp_attrs(L.Module.TraitT.decless()):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pinmap = {}

    def on_obj_set(self):
        self.module = self.get_obj(L.Module)
        self.module.add(F.can_attach_to_footprint_via_pinmap(self.pinmap))
        self.module.add(
            F.has_designator_prefix_defined(F.has_designator_prefix.Prefix.U)
        )

    def add_pin(self, name: str) -> F.Electrical:
        if _is_int(name):
            py_name = f"_{name}"
        else:
            py_name = name

        mif = self.module.add(F.Electrical(), name=py_name)

        self.pinmap[name] = mif
        return mif

    def handle_duplicate(self, old: TraitImpl, node: fab_param.Node) -> bool:
        # Don't replace the existing ato trait on addition
        return False


# FIXME: this would ideally be some kinda of mixin,
# however, we can't have multiple bases for Nodes
class GlobalShims(L.Module):
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

    @property
    def mpn(self) -> str:
        try:
            return self.get_trait(F.has_descriptive_properties).get_properties()[
                DescriptiveProperties.partno
            ]
        except (TraitNotFound, KeyError):
            raise AttributeError(name="mpn", obj=self)

    @mpn.setter
    def mpn(self, value: str):
        # handles duplicates gracefully
        self.add(
            F.has_descriptive_properties_defined({DescriptiveProperties.partno: value})
        )

        # TODO: @v0.4: remove this - mpn != lcsc id
        if re.match(r"C[0-9]+", value):
            self.add(F.has_descriptive_properties_defined({"LCSC": value}))
            from atopile.front_end import DeprecatedException

            raise DeprecatedException(
                "mpn is deprecated for assignment of LCSC IDs, use lcsc_id instead"
            )

    @write_only_property
    def designator_prefix(self, value: str):
        self.add(F.has_designator_prefix_defined(value))

    @write_only_property
    def package(self, value: str):
        self.add(F.has_package_requirement(value))

    @write_only_property
    def footprint(self, value: str):
        self.add(
            has_local_kicad_footprint_named_defined(
                value, self.get_trait(has_ato_cmp_attrs).pinmap
            )
        )


@_register_shim("generics/resistors.ato:Resistor", "import Resistor")
class ShimResistor(F.Resistor):
    """Temporary shim to translate `value` to `resistance`."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def value(self):
        return self.resistance

    @value.setter
    def value(self, value: L.Range):
        self.resistance.constrain_subset(value)

    @write_only_property
    def footprint(self, value: str):
        if value.startswith("R"):
            value = value[1:]
        GlobalShims.package.fset(self, value)

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
class ShimCapacitor(F.Capacitor):
    """Temporary shim to translate `value` to `capacitance`."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class has_power(L.ModuleInterface.TraitT.decless()):
        power: F.ElectricPower

    @property
    def value(self):
        return self.capacitance

    @value.setter
    def value(self, value: L.Range):
        self.capacitance.constrain_subset(value)

    @write_only_property
    def footprint(self, value: str):
        if value.startswith("C"):
            value = value[1:]
        GlobalShims.package.fset(self, value)

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


@_register_shim("generics/inductors.ato:Inductor", "import Inductor")
class ShimInductor(F.Inductor):
    """Temporary shim to translate inductors."""

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


@_register_shim("generics/leds.ato:LED", "import LED")
class ShimLED(F.LED):
    """Temporary shim to translate LEDs."""

    @property
    def v_f(self):
        return self.forward_voltage

    @property
    def i_max(self):
        return self.max_current


@_register_shim(
    "generics/capacitors.ato:CapacitorElectrolytic", "import CapacitorElectrolytic"
)
class ShimCapacitorElectrolytic(F.Capacitor):
    """Temporary shim to translate capacitors."""

    anode: F.Electrical
    cathode: F.Electrical


@_register_shim("generics/interfaces.ato:Power", "import ElectricPower")
class ShimPower(F.ElectricPower):
    """Temporary shim to translate `value` to `power`."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def vcc(self) -> F.Electrical:
        return self.hv

    @property
    def gnd(self) -> F.Electrical:
        return self.lv

    @property
    def current(self):
        return self.max_current
