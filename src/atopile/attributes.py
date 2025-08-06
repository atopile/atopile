"""
This file defines what attributes are available in `ato`.
"""

import logging
import re
from typing import Type

import faebryk.core.parameter as fab_param
import faebryk.library._F as F
import faebryk.libs.library.L as L
from atopile import address
from atopile.errors import UserBadParameterError, UserNotImplementedError
from faebryk.core.trait import TraitImpl
from faebryk.libs.exceptions import downgrade
from faebryk.libs.smd import SMDSize
from faebryk.libs.util import md_list, not_none

log = logging.getLogger(__name__)


shim_map: dict[address.AddrStr, tuple[Type[L.Node], str]] = {}


def _register_shim(addr: str | address.AddrStr, preferred: str):
    def _wrapper[T: Type[L.Node]](cls: T) -> T:
        shim_map[address.AddrStr(addr)] = cls, preferred
        return cls

    return _wrapper


class _has_local_kicad_footprint_named_defined(F.has_footprint_impl):
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

    def get_footprint(self) -> F.Footprint:
        if fp := self.try_get_footprint():
            return fp
        else:
            fp = F.KicadFootprint(
                pin_names=list(self.pinmap.keys()),
            )
            fp.add(F.KicadFootprint.has_kicad_identifier(self.lib_reference))
            fp.get_trait(F.can_attach_via_pinmap).attach(self.pinmap)  # type: ignore
            self.set_footprint(fp)
            return fp

    def handle_duplicate(
        self, old: "_has_local_kicad_footprint_named_defined", _: fab_param.Node
    ) -> bool:
        if old.try_get_footprint():
            raise RuntimeError("Too late to set footprint")

        # Update the existing trait...
        old.lib_reference = self.lib_reference
        # ... and we don't need to attach the new
        assert old.pinmap is self.pinmap, "Pinmap reference mismatch"
        return False


class _has_ato_cmp_attrs(L.Module.TraitT.decless()):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pinmap: dict[str, F.Electrical | None] = {}

    def on_obj_set(self):
        self.module = self.get_obj(L.Module)
        self.module.add(F.can_attach_to_footprint_via_pinmap(self.pinmap))
        self.module.add(F.has_designator_prefix(F.has_designator_prefix.Prefix.U))

    def add_pin(self, pinname: str, pyname: str) -> F.Electrical:
        mif = self.module.add(F.Electrical(), name=pyname)

        self.pinmap[pinname] = mif
        return mif

    def handle_duplicate(self, old: TraitImpl, node: fab_param.Node) -> bool:
        # Don't replace the existing ato trait on addition
        return False


# FIXME: this would ideally be some kinda of mixin,
# however, we can't have multiple bases for Nodes
class GlobalAttributes(L.Module):
    """
    These attributes are available to all modules and interfaces in a design.
    """

    @property
    def lcsc_id(self):
        """
        Assign the LCSC ID of the module.

        If set, this will tell the picker to select that part from LCSC for this block.
        """
        raise AttributeError("write-only")

    @lcsc_id.setter
    def lcsc_id(self, value: str):
        # handles duplicates gracefully
        self.add(
            F.has_explicit_part.by_supplier(supplier_partno=value, supplier_id="lcsc")
        )

    def check_mpn_complete(self):
        mpn = getattr(self, "__shim_mpn__", None)
        manufacturer = getattr(self, "__shim_manufacturer__", None)
        if mpn is None or manufacturer is None:
            return
        self.add(F.has_explicit_part.by_mfr(mfr=manufacturer, partno=mpn))

    @property
    def manufacturer(self) -> str:
        """
        This module's manufacturer name, as a string.

        Only exact matches on the manufacturer's name will be found by the picker.
        It's recommended to fill this information based on what `ato create component`
        provides.
        """
        raise AttributeError("write-only")

    @manufacturer.setter
    def manufacturer(self, value: str):
        setattr(self, "__shim_manufacturer__", value)
        GlobalAttributes.check_mpn_complete(self)

    @property
    def mpn(self) -> str:
        """
        This module's manufacturer part number, as a string.

        For the picker to select the correct part from the manufacturer,
        this must be set.
        """
        raise AttributeError("write-only")

    @mpn.setter
    def mpn(self, value: str):
        from atopile.front_end import DeprecatedException

        if value.lower() == "dnp":
            raise DeprecatedException(
                f"`mpn = {value}` is deprecated. Use `exclude_from_bom = True` instead."
            )

        # TODO: @v0.4: remove this - mpn != lcsc id
        if re.match(r"C[0-9]+", value):
            not_none(GlobalAttributes.lcsc_id.fset)(self, value)

            raise DeprecatedException(
                "`mpn` is deprecated for assignment of LCSC IDs. Use `lcsc_id` instead."
            )

        setattr(self, "__shim_mpn__", value)
        GlobalAttributes.check_mpn_complete(self)

    @property
    def datasheet_url(self) -> str:
        """
        The URL of the datasheet for this component.
        """
        raise AttributeError("write-only")

    @datasheet_url.setter
    def datasheet_url(self, value: str):
        self.add(F.has_datasheet_defined(value))

    @property
    def designator_prefix(self):
        """
        The prefix used for automatically-generated designators on this module.
        """
        raise AttributeError("write-only")

    @designator_prefix.setter
    def designator_prefix(self, value: str):
        self.add(F.has_designator_prefix(value))

    @property
    def package(self) -> str:
        """
        The package of the module.

        This drives which components can be selected, and what footprint is used.

        Must exactly match a known package name.
        """
        raise AttributeError("write-only")

    @package.setter
    def package(self, value: str):
        GlobalAttributes._handle_package_size(self, value)

    @staticmethod
    def _handle_package_size(module: L.Module, value: str):
        match module:
            case F.Resistor():
                value = re.sub(r"^R", "I", value)
            case F.Capacitor():
                value = re.sub(r"^C", "I", value)
            case F.Inductor():
                value = re.sub(r"^L", "I", value)
            case _:
                pass

        # assume imperial
        if re.match(r"^[0-9]+$", value):
            value = f"I{value}"

        if value not in {s.name for s in SMDSize}:
            raise UserBadParameterError(
                f"Invalid package: `{value}`. Valid packages are:\n"
                f"{md_list(s.name for s in SMDSize)}"
            )

        module.add(F.has_package_requirements(size=SMDSize[value]))

    @property
    def footprint(self) -> str:
        """
        Explicitly set the footprint to be used for this module.

        Setting this will cause this component to be selected and placed on the PCB.

        The footprint should be a string, naming the KiCAD ID of the footprint.
        """
        raise AttributeError("write-only")

    @footprint.setter
    def footprint(self, value: str):
        self.add(
            _has_local_kicad_footprint_named_defined(
                value, self.get_trait(_has_ato_cmp_attrs).pinmap
            )
        )

    # TODO: do not place
    @property
    def exclude_from_bom(self):
        raise AttributeError("write-only")

    # See: https://github.com/atopile/atopile/pull/424/files#diff-63194bff2019ade91098b68b1c47e10ce94fb03258923f8c77f66fc5707a0c96
    @exclude_from_bom.setter
    def exclude_from_bom(self, value: bool):
        raise UserNotImplementedError(
            "`exclude_from_bom` is not yet implemented. "
            "This should not currently affect your design, "
            "however may throw spurious warnings.\n"
            "See: https://github.com/atopile/atopile/issues/755"
        )

    @property
    def override_net_name(self):
        """
        When set on an interface, this will override the net name of the interface.

        This is useful for renaming nets which are automatically generated.
        """
        raise AttributeError("write-only")

    @override_net_name.setter
    def override_net_name(self, name: str):
        self.add(F.has_net_name(name, level=F.has_net_name.Level.EXPECTED))

    @property
    def suggest_net_name(self):
        """
        Suggested net name which will have a higher priority than generated net names.
        """
        raise AttributeError("write-only")

    @suggest_net_name.setter
    def suggest_net_name(self, name: str):
        """
        Suggested net name which will have a higher priority than generated net names.
        """
        self.add(F.has_net_name(name, level=F.has_net_name.Level.SUGGESTED))

    @property
    def required(self):
        """
        Only for ModuleInterfaces.
        If set to `True`, require that interface is connected to something outside
        of the module it's defined in.
        """
        raise AttributeError("write-only")

    @required.setter
    def required(self, value: bool):
        if not value:
            self.del_trait(F.requires_external_usage)
            return
        self.add(F.requires_external_usage())


@_register_shim("generics/resistors.ato:Resistor", "import Resistor")
class Resistor(F.Resistor):
    """
    This resistor is replaces `generics/resistors.ato:Resistor`
    every times it's referenced.
    """

    @property
    def value(self):
        """Represents the resistance of the resistor."""
        return self.resistance

    @value.setter
    def value(self, value: L.Range):
        self.resistance.constrain_subset(value)

    @property
    def footprint(self):
        """See `GlobalAttributes.footprint`"""
        raise AttributeError("write-only")

    @footprint.setter
    def footprint(self, value: str):
        from atopile.front_end import DeprecatedException

        if value.startswith("R"):
            try:
                GlobalAttributes._handle_package_size(self, value[1:])
            except UserBadParameterError:
                pass
            else:
                with downgrade(DeprecatedException):
                    raise DeprecatedException(
                        "`footprint` is deprecated for assignment of package. "
                        f"Use: `package = '{value[1:]}'`"
                    )
                # Return here, to avoid additionally setting the footprint
                return

        not_none(GlobalAttributes.footprint.fset)(self, value)

    @property
    def _1(self) -> F.Electrical:
        return self.unnamed[0]

    @property
    def _2(self) -> F.Electrical:
        return self.unnamed[1]

    @L.rt_field
    def has_ato_cmp_attrs_(self) -> _has_ato_cmp_attrs:
        """Ignore this field."""
        trait = _has_ato_cmp_attrs()
        trait.pinmap["1"] = self.p1
        trait.pinmap["2"] = self.p2
        return trait


class CommonCapacitor(F.Capacitor):
    """
    These attributes are common to both electrolytic and non-electrolytic capacitors.
    """

    @property
    def value(self):
        """Represents the capacitance of the capacitor."""
        return self.capacitance

    @value.setter
    def value(self, value: L.Range):
        self.capacitance.constrain_subset(value)

    @property
    def footprint(self):
        """See `GlobalAttributes.footprint`"""
        raise AttributeError("write-only")

    @footprint.setter
    def footprint(self, value: str):
        from atopile.front_end import DeprecatedException

        if value.startswith("C"):
            try:
                GlobalAttributes._handle_package_size(self, value[1:])
            except UserBadParameterError:
                pass
            else:
                with downgrade(DeprecatedException):
                    raise DeprecatedException(
                        "`footprint` is deprecated for assignment of package. "
                        f"Use: `package = '{value[1:]}'`"
                    )
                # Return here, to avoid additionally setting the footprint
                return

        not_none(GlobalAttributes.footprint.fset)(self, value)

    @property
    def _1(self) -> F.Electrical:
        return self.unnamed[0]

    @property
    def _2(self) -> F.Electrical:
        return self.unnamed[1]


@_register_shim("generics/capacitors.ato:Capacitor", "import Capacitor")
class Capacitor(CommonCapacitor):
    """
    This capacitor is replaces `generics/capacitors.ato:Capacitor`
    every times it's referenced.
    """

    @L.rt_field
    def has_ato_cmp_attrs_(self) -> _has_ato_cmp_attrs:
        """Ignore this field."""
        trait = _has_ato_cmp_attrs()
        trait.pinmap["1"] = self.p1
        trait.pinmap["2"] = self.p2
        return trait


@_register_shim(
    "generics/capacitors.ato:CapacitorElectrolytic", "import CapacitorElectrolytic"
)
class CapacitorElectrolytic(CommonCapacitor):
    """Temporary shim to translate capacitors."""

    anode: F.Electrical
    cathode: F.Electrical

    pickable = None  # type: ignore

    # Overrides the default implementation in F.Capacitor
    @property
    def power(self) -> F.ElectricPower:
        if self.has_trait(self._has_power):
            power = self.get_trait(self._has_power).power
        else:
            power = F.ElectricPower()
            self.add(power, name="power_shim")
            power.hv.connect(self.anode)
            power.lv.connect(self.cathode)
            self.add(self._has_power(power))

        return power


@_register_shim("generics/inductors.ato:Inductor", "import Inductor")
class Inductor(F.Inductor):
    """
    This inductor is replaces `generics/inductors.ato:Inductor`
    every times it's referenced.
    """

    @property
    def _1(self) -> F.Electrical:
        return self.unnamed[0]

    @property
    def _2(self) -> F.Electrical:
        return self.unnamed[1]

    @L.rt_field
    def has_ato_cmp_attrs_(self) -> _has_ato_cmp_attrs:
        """Ignore this field."""
        trait = _has_ato_cmp_attrs()
        trait.pinmap["1"] = self.p1
        trait.pinmap["2"] = self.p2
        return trait


@_register_shim("generics/leds.ato:LED", "import LED")
class LED(F.LED):
    """Temporary shim to translate LEDs."""

    @property
    def v_f(self):
        return self.forward_voltage

    @property
    def i_max(self):
        return self.max_current


@_register_shim("generics/interfaces.ato:Power", "import ElectricPower")
class Power(F.ElectricPower):
    """Temporary shim to translate `value` to `power`."""

    @property
    def current(self):
        """
        Maximum current the power interface can provide.

        Negative is current draw.
        """
        return self.max_current


@_register_shim("generics/interfaces.ato:I2C", "import I2C")
class I2C(F.I2C):
    """Temporary shim to translate I2C interfaces."""

    @property
    def gnd(self):
        return self.single_electric_reference.get_reference().gnd
