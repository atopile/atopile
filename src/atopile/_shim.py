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
from atopile.errors import UserNotImplementedError
from faebryk.core.trait import TraitImpl, TraitNotFound
from faebryk.libs.exceptions import downgrade
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
        self.pinmap: dict[str, F.Electrical | None] = {}

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
        from atopile.front_end import DeprecatedException

        if value.lower() == "dnp":
            raise DeprecatedException(
                f"`mpn = {value}` is deprecated. "
                "Use `exclude_from_bom = True` instead."
            )

        # handles duplicates gracefully
        self.add(
            F.has_descriptive_properties_defined({DescriptiveProperties.partno: value})
        )

        # TODO: @v0.4: remove this - mpn != lcsc id
        if re.match(r"C[0-9]+", value):
            self.add(F.has_descriptive_properties_defined({"LCSC": value}))

            raise DeprecatedException(
                "`mpn` is deprecated for assignment of LCSC IDs. Use `lcsc_id` instead."
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

    # TODO: do not place
    # See: https://github.com/atopile/atopile/pull/424/files#diff-63194bff2019ade91098b68b1c47e10ce94fb03258923f8c77f66fc5707a0c96
    @write_only_property
    def exclude_from_bom(self, value: bool):
        raise UserNotImplementedError(
            "`exclude_from_bom` is not yet implemented. "
            "This should not currently affect your design, "
            "however may throw spurious warnings.\n"
            "See: https://github.com/atopile/atopile/issues/755"
        )

    def override_net_name(self, name: str):
        self.add(F.has_net_name(name, level=F.has_net_name.Level.EXPECTED))


def _handle_footprint_shim(module: L.Module, value: str):
    from atopile.front_end import DeprecatedException

    if value.startswith(("R", "C")):
        value = value[1:]
        with downgrade(DeprecatedException):
            raise DeprecatedException(
                "`footprint` is deprecated for assignment of package. "
                f"Use: `package = '{value}'`"
            )
        GlobalShims.package.fset(module, value)
        return

    GlobalShims.footprint.fset(module, value)


@_register_shim("generics/resistors.ato:Resistor", "import Resistor")
class ShimResistor(F.Resistor):
    """Temporary shim to translate `value` to `resistance`."""

    @property
    def value(self):
        return self.resistance

    @value.setter
    def value(self, value: L.Range):
        self.resistance.constrain_subset(value)

    @write_only_property
    def footprint(self, value: str):
        _handle_footprint_shim(self, value)

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

    @L.rt_field
    def has_ato_cmp_attrs_(self) -> has_ato_cmp_attrs:
        trait = has_ato_cmp_attrs()
        trait.pinmap["1"] = self.p1
        trait.pinmap["2"] = self.p2
        return trait


class _CommonCap(F.Capacitor):
    class has_power(L.Trait.decless()):
        """
        This trait is used to add power interfaces to
        capacitors who use them, keeping the interfaces
        off caps which don't use it.

        Caps have power-interfaces when used with them.
        """

        def __init__(self, power: F.ElectricPower) -> None:
            super().__init__()
            self.power = power

    @property
    def value(self):
        return self.capacitance

    @value.setter
    def value(self, value: L.Range):
        self.capacitance.constrain_subset(value)

    @write_only_property
    def footprint(self, value: str):
        _handle_footprint_shim(self, value)

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
class ShimCapacitor(_CommonCap):
    """Temporary shim to translate `value` to `capacitance`."""

    @L.rt_field
    def has_ato_cmp_attrs_(self) -> has_ato_cmp_attrs:
        trait = has_ato_cmp_attrs()
        trait.pinmap["1"] = self.p1
        trait.pinmap["2"] = self.p2
        return trait

    @property
    def power(self) -> F.ElectricPower:
        if self.has_trait(self.has_power):
            power = self.get_trait(self.has_power).power
        else:
            power = F.ElectricPower()
            power.hv.connect_via(self, power.lv)
            self.add(self.has_power(power))

        return power


@_register_shim(
    "generics/capacitors.ato:CapacitorElectrolytic", "import CapacitorElectrolytic"
)
class ShimCapacitorElectrolytic(_CommonCap):
    """Temporary shim to translate capacitors."""

    anode: F.Electrical
    cathode: F.Electrical

    pickable = None

    @property
    def power(self) -> F.ElectricPower:
        if self.has_trait(self.has_power):
            power = self.get_trait(self.has_power).power
        else:
            power = F.ElectricPower()
            power.hv.connect(self.anode)
            power.lv.connect(self.cathode)
            self.add(self.has_power(power))

        return power


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

    @L.rt_field
    def has_ato_cmp_attrs_(self) -> has_ato_cmp_attrs:
        trait = has_ato_cmp_attrs()
        trait.pinmap["1"] = self.p1
        trait.pinmap["2"] = self.p2
        return trait


@_register_shim("generics/leds.ato:LED", "import LED")
class ShimLED(F.LED):
    """Temporary shim to translate LEDs."""

    @property
    def v_f(self):
        return self.forward_voltage

    @property
    def i_max(self):
        return self.max_current


@_register_shim("generics/interfaces.ato:Power", "import ElectricPower")
class ShimPower(F.ElectricPower):
    """Temporary shim to translate `value` to `power`."""

    @property
    def vcc(self) -> F.Electrical:
        return self.hv

    @property
    def gnd(self) -> F.Electrical:
        return self.lv

    @property
    def current(self):
        return self.max_current
