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
    manufacturer_ = F.Parameters.StringParameter.MakeChild()
    partno_ = F.Parameters.StringParameter.MakeChild()
    supplier_partno_ = F.Parameters.StringParameter.MakeChild()
    supplier_id_ = F.Parameters.StringParameter.MakeChild()

    def get_part(self) -> "PickedPart":
        return not_none(self.try_get_part())

    def try_get_part(self) -> "PickedPart | None":
        from faebryk.libs.picker.picker import PickedPart, PickSupplier

        class DummyPickSupplier(PickSupplier):
            supplier_id = not_none(
                not_none(self.supplier_id_.get().try_extract_constrained_literal())
            ).get_single()

            def attach(self, *args, **kwargs):
                return None

        return PickedPart(
            manufacturer=not_none(
                self.manufacturer_.get().try_extract_constrained_literal()
            ).get_single(),
            partno=not_none(
                self.partno_.get().try_extract_constrained_literal()
            ).get_single(),
            supplier_partno=not_none(
                self.supplier_partno_.get().try_extract_constrained_literal()
            ).get_single(),
            supplier=DummyPickSupplier(),
        )

    @property
    def part(self) -> "PickedPart | None":
        return self.try_get_part()

    @property
    def removed(self) -> bool:
        return self.has_trait(F.has_part_removed)

    @classmethod
    def MakeChild(cls, picked_part: "PickedPart") -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.manufacturer_], picked_part.manufacturer
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.partno_], picked_part.partno
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.supplier_partno_], picked_part.supplier_partno
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.supplier_id_], picked_part.supplier.supplier_id
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
        self.manufacturer_.get().alias_to_single(value=picked_part.manufacturer)
        self.partno_.get().alias_to_single(value=picked_part.partno)
        self.supplier_partno_.get().alias_to_single(value=picked_part.supplier_partno)
        self.supplier_id_.get().alias_to_single(value=picked_part.supplier.supplier_id)
        return self

    def by_supplier(
        self, supplier_id: str, supplier_partno: str, manufacturer: str, partno: str
    ) -> Self:
        """
        Instance method alternative to the classmethod factory.
        Used by AtoCodeParse when parsing traits from ato files.
        """
        self.manufacturer_.get().alias_to_single(value=manufacturer)
        self.partno_.get().alias_to_single(value=partno)
        self.supplier_partno_.get().alias_to_single(value=supplier_partno)
        self.supplier_id_.get().alias_to_single(value=supplier_id)
        return self
