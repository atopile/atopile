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
from faebryk.core.solver.solver import Solver
from faebryk.core.trait import TraitNotFound
from faebryk.libs.exceptions import DeprecatedException, downgrade
from faebryk.libs.picker.picker import (
    DescriptiveProperties,
    Part,
    PickerOption,
    Supplier,
    has_part_picked_defined,
)
from faebryk.libs.util import has_attr_or_property, write_only_property

log = logging.getLogger(__name__)


shim_map: dict[address.AddrStr, tuple[Type[L.Module], str]] = {}


def _register_shim(addr: str | address.AddrStr, preferred: str):
    def _wrapper(cls: Type[L.Module]):
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


class CornerStore(Supplier):
    def attach(self, module: L.Module, part: PickerOption):
        assert isinstance(part.part, LocalPart)
        # Ensures the footprint etc... is attached
        # TODO: consider where the footprint logic should live
        module.get_trait(F.has_footprint).get_footprint()

        # TODO: consider converting all the attached params as "alias_is"
        # This would mean that we're stating that all the params ARE
        # the values provided in the design, rather than just having to
        # fall within it


_corner_store = CornerStore()


class LocalPart(Part):
    def __init__(self, partno: str) -> None:
        super().__init__(partno=partno, supplier=_corner_store)


class Component(L.Module):
    class _Picker(F.has_multi_picker.Picker):
        def pick(self, module: L.Module, solver: Solver):
            part = LocalPart(getattr(module, "mpn"))
            module.add(has_part_picked_defined(part))

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pinmap = {}

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(self.pinmap)

    @L.rt_field
    def has_designator_prefix(self):
        return F.has_designator_prefix_defined(F.has_designator_prefix.Prefix.U)

    @L.rt_field
    def has_backup_pick(self):
        return F.has_multi_picker(
            100,  # Super low-prio
            self._Picker(),
        )

    def add_pin(self, name: str) -> F.Electrical:
        if _is_int(name):
            py_name = f"_{name}"
        else:
            py_name = name

        # TODO: @v0.4: remove this
        if has_attr_or_property(self, py_name):
            log.warning(
                f"Pin {name} already exists, skipping."
                " In the future this will be an error."
            )
            mif = getattr(self, py_name)
        elif py_name in self.runtime:
            mif = self.runtime[py_name]
        else:
            mif = self.add(F.Electrical(), name=py_name)

        self.pinmap[name] = mif
        return mif

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
            with downgrade(DeprecatedException):
                raise DeprecatedException(
                    "mpn is deprecated for assignment of LCSC IDs, use lcsc_id instead"
                )

    @write_only_property
    def footprint(self, value: str):
        self.add(has_local_kicad_footprint_named_defined(value, self.pinmap))


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

        # TODO: @v0.4: remove this - mpn != lcsc id
        if re.match(r"C[0-9]+", value):
            self.add(F.has_descriptive_properties_defined({"LCSC": value}))
            with downgrade(DeprecatedException):
                raise DeprecatedException(
                    "mpn is deprecated for assignment of LCSC IDs, use lcsc_id instead"
                )

    @write_only_property
    def designator_prefix(self, value: str):
        self.add(F.has_designator_prefix_defined(value))

    @write_only_property
    def package(self, value: str):
        self.add(F.has_package_requirement(value))


@_register_shim("generics/resistors.ato:Resistor", "import Resistor")
class _ShimResistor(F.Resistor):
    """Temporary shim to translate `value` to `resistance`."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def value(self) -> L.Range:
        return self.resistance

    @value.setter
    def value(self, value: L.Range):
        self.resistance.constrain_subset(value)

    @write_only_property
    def footprint(self, value: str):
        if value.startswith("R"):
            value = value[1:]
        self.package = value

    @write_only_property
    def package(self, value: str):
        self.add(F.has_package_requirement(value))

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
        super().__init__(*args, **kwargs)

    class has_power(L.ModuleInterface.TraitT.decless()):
        power: F.ElectricPower

    @property
    def value(self) -> L.Range:
        return self.capacitance

    @value.setter
    def value(self, value: L.Range):
        self.capacitance.constrain_subset(value)

    @write_only_property
    def footprint(self, value: str):
        if value.startswith("C"):
            value = value[1:]
        self.package = value

    @write_only_property
    def package(self, value: str):
        self.add(F.has_package_requirement(value))

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
        super().__init__(*args, **kwargs)

    @property
    def vcc(self) -> F.Electrical:
        return self.hv

    @property
    def gnd(self) -> F.Electrical:
        return self.lv
