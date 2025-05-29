# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self, override

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.core.trait import TraitImpl


class has_explicit_part(Module.TraitT.decless()):
    mfr: str
    partno: str
    supplier_id: str
    supplier_partno: str
    pinmap: dict[str, F.Electrical | None] | None
    override_footprint: tuple[F.Footprint, str] | None = None

    @classmethod
    def by_mfr(
        cls,
        mfr: str,
        partno: str,
        pinmap: dict[str, F.Electrical | None] | None = None,
        override_footprint: tuple[F.Footprint, str] | None = None,
    ) -> Self:
        out = cls()
        out.mfr = mfr
        out.partno = partno
        out.pinmap = pinmap
        out.override_footprint = override_footprint
        return out

    @classmethod
    def by_supplier(
        cls,
        supplier_partno: str,
        supplier_id: str = "lcsc",
        pinmap: dict[str, F.Electrical | None] | None = None,
        override_footprint: tuple[F.Footprint, str] | None = None,
    ) -> Self:
        if supplier_id != "lcsc":
            raise NotImplementedError(f"Supplier {supplier_id} not supported")
        out = cls()
        out.supplier_id = supplier_id
        out.supplier_partno = supplier_partno
        out.pinmap = pinmap
        out.override_footprint = override_footprint
        return out

    @override
    def on_obj_set(self):
        super().on_obj_set()
        obj = self.get_obj(type=Module)

        if hasattr(self, "mfr"):
            assert self.partno
            obj.add(F.is_pickable_by_part_number(self.mfr, self.partno))
        if hasattr(self, "supplier_partno"):
            assert self.supplier_id == "lcsc"
            obj.add(
                F.is_pickable_by_supplier_id(
                    self.supplier_partno,
                    supplier=F.is_pickable_by_supplier_id.Supplier.LCSC,
                )
            )

        if self.pinmap:
            obj.add(F.can_attach_to_footprint_via_pinmap(self.pinmap))

        if self.override_footprint:
            fp, fp_kicad_id = self.override_footprint
            fp.add(F.KicadFootprint.has_kicad_identifier(fp_kicad_id))
            obj.get_trait(F.can_attach_to_footprint).attach(fp)

    def _merge(self, overlay: "has_explicit_part"):
        attrs = [
            "mfr",
            "partno",
            "supplier_id",
            "supplier_partno",
            "pinmap",
            "override_footprint",
        ]
        changed = False
        for attr in attrs:
            if not hasattr(overlay, attr):
                continue
            v = getattr(overlay, attr)
            if getattr(self, attr, None) == v:
                continue
            setattr(self, attr, v)
            changed = True

        if not changed:
            return

        self.on_obj_set()

    @override
    def handle_duplicate(self, old: TraitImpl, node: Node) -> bool:
        assert isinstance(old, has_explicit_part)
        old._merge(self)
        return False
