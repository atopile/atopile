# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import TYPE_CHECKING, Self

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none

if TYPE_CHECKING:
    from faebryk.libs.picker.picker import PickedPart

logger = logging.getLogger(__name__)


class has_part_picked(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    # Manual storage of the PickedPart dataclass
    manufacturer = F.Parameters.StringParameter.MakeChild()
    partno = F.Parameters.StringParameter.MakeChild()
    supplier_partno = F.Parameters.StringParameter.MakeChild()
    supplier_id = F.Parameters.StringParameter.MakeChild()

    def get_part(self) -> "PickedPart":
        return not_none(self.try_get_part())

    def try_get_part(self) -> "PickedPart | None":
        from faebryk.libs.picker.picker import PickedPart, PickSupplier

        class DummyPickSupplier(PickSupplier):
            if (
                supplier_id_literal
                := self.supplier_id.get().try_extract_constrained_literal()
            ):
                supplier_id = supplier_id_literal.get_values()[0]
            else:
                supplier_id = ""

            def attach(self, *args, **kwargs):
                return None

        if manufacturer := self.manufacturer.get().try_extract_constrained_literal():
            manufacturer = manufacturer.get_values()[0]
        else:
            return None

        if partno := self.partno.get().try_extract_constrained_literal():
            partno = partno.get_values()[0]
        else:
            return None

        if (
            supplier_partno
            := self.supplier_partno.get().try_extract_constrained_literal()
        ):
            supplier_partno = supplier_partno.get_values()[0]
        else:
            return None

        return PickedPart(
            manufacturer=manufacturer,
            partno=partno,
            supplier_partno=supplier_partno,
            supplier=DummyPickSupplier(),
        )

    @property
    def removed(self) -> bool:
        return self.has_trait(F.has_part_removed)

    @classmethod
    def MakeChild(cls, picked_part: "PickedPart") -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.manufacturer], picked_part.manufacturer
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.partno], picked_part.partno
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.supplier_partno], picked_part.supplier_partno
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.supplier_id], picked_part.supplier.supplier_id
            )
        )
        return out

    @classmethod
    def MakeChild_by_supplier(
        cls, supplier_id: str, supplier_partno: str, manufacturer: str, partno: str
    ) -> fabll._ChildField[Self]:
        from faebryk.libs.picker.lcsc import PickedPartLCSC

        match supplier_id:
            case "lcsc":
                return cls.MakeChild(
                    PickedPartLCSC(
                        manufacturer=manufacturer,
                        partno=partno,
                        supplier_partno=supplier_partno,
                    )
                )
            case _:
                raise ValueError(f"Unknown supplier: {supplier_id}")

    def setup(self, picked_part: "PickedPart") -> Self:
        self.manufacturer.get().alias_to_single(value=picked_part.manufacturer)
        self.partno.get().alias_to_single(value=picked_part.partno)
        self.supplier_partno.get().alias_to_single(value=picked_part.supplier_partno)
        self.supplier_id.get().alias_to_single(value=picked_part.supplier.supplier_id)
        return self

    def by_supplier(
        self, supplier_id: str, supplier_partno: str, manufacturer: str, partno: str
    ) -> Self:
        """
        Instance method alternative to the classmethod factory.
        Used by AtoCodeParse when parsing traits from ato files.
        """
        self.manufacturer.get().alias_to_single(value=manufacturer)
        self.partno.get().alias_to_single(value=partno)
        self.supplier_partno.get().alias_to_single(value=supplier_partno)
        self.supplier_id.get().alias_to_single(value=supplier_id)
        return self
