# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import override

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.picker.picker import has_part_picked_remove


class has_explicit_part(Module.TraitT.decless()):
    mfr: str
    partno: str
    supplier_id: str
    supplier_partno: str
    kicad_identifier: str
    pinmap: dict[str, F.Electrical | None] | None

    @classmethod
    def by_mfr(
        cls,
        mfr: str,
        partno: str,
        pinmap: dict[str, F.Electrical | None] | None = None,
    ):
        out = cls()
        out.mfr = mfr
        out.partno = partno
        out.pinmap = pinmap
        return out

    @classmethod
    def by_supplier(
        cls,
        supplier_partno: str,
        supplier_id: str = "lcsc",
        pinmap: dict[str, F.Electrical | None] | None = None,
    ):
        if supplier_id != "lcsc":
            raise NotImplementedError(f"Supplier {supplier_id} not supported")
        out = cls()
        out.supplier_id = supplier_id
        out.supplier_partno = supplier_partno
        out.pinmap = pinmap
        return out

    @classmethod
    def from_kicad_library(
        cls, kicad_identifier: str, pinmap: dict[str, F.Electrical | None] | None = None
    ):
        out = cls()
        out.kicad_identifier = kicad_identifier
        out.pinmap = pinmap
        return out

    @override
    def on_obj_set(self):
        # TODO later get rid oof this when we deprecate using DescriptiveProperties
        # directly

        from faebryk.libs.picker.picker import DescriptiveProperties

        super().on_obj_set()
        obj = self.get_obj(type=Module)

        properties = {}

        if hasattr(self, "mfr"):
            assert self.partno
            properties[DescriptiveProperties.manufacturer] = self.mfr
            properties[DescriptiveProperties.partno] = self.partno
        if hasattr(self, "supplier_partno"):
            assert self.supplier_id == "lcsc"
            properties["LCSC"] = self.supplier_partno

        if self.pinmap:
            obj.add(F.can_attach_to_footprint_via_pinmap(self.pinmap))

        if hasattr(self, "kicad_identifier"):
            if not obj.has_trait(F.can_attach_to_footprint):
                raise ValueError(
                    f"Need to either supply pinmap or have F.can_attach_to_footprint "
                    f"for module {obj}"
                )
            obj.get_trait(F.can_attach_to_footprint).attach(
                F.KicadFootprint.from_library(self.kicad_identifier)
            )
            obj.add(has_part_picked_remove())

        obj.add(F.has_descriptive_properties_defined(properties))
