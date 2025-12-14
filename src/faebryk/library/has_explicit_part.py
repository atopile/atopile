# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_explicit_part(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    mfr_ = F.Parameters.StringParameter.MakeChild()
    partno_ = F.Parameters.StringParameter.MakeChild()
    supplier_id_ = F.Parameters.StringParameter.MakeChild()
    supplier_partno_ = F.Parameters.StringParameter.MakeChild()
    pinmap_ = F.Collections.PointerSet.MakeChild()
    override_footprint_ = F.Collections.PointerTuple.MakeChild()

    as_pickable_by_supplier_id: fabll.Traits.OptionalImpliedTrait[
        "F.is_pickable_by_supplier_id"
    ] = fabll.Traits.OptionalImpliedTrait(lambda: F.is_pickable_by_supplier_id)

    as_pickable_by_part_number: fabll.Traits.OptionalImpliedTrait[
        "F.is_pickable_by_part_number"
    ] = fabll.Traits.OptionalImpliedTrait(lambda: F.is_pickable_by_part_number)

    def setup_by_mfr(
        self,
        mfr: str,
        partno: str,
        pinmap: dict[str, F.Electrical | None] | None = None,
        override_footprint: tuple[F.Footprints.is_footprint, str] | None = None,
    ) -> Self:
        self.mfr_.get().alias_to_literal(mfr)
        self.partno_.get().alias_to_literal(partno)
        # TODO: handle pinmap and override_footprint for instance setup
        return self

    def setup_by_supplier(
        self,
        supplier_partno: str,
        supplier_id: str = "lcsc",
        pinmap: dict[str, F.Electrical | None] | None = None,
        override_footprint: tuple[F.Footprints.is_footprint, str] | None = None,
    ) -> Self:
        if supplier_id != "lcsc":
            raise NotImplementedError(f"Supplier {supplier_id} not supported")
        self.supplier_id_.get().alias_to_literal(supplier_id)
        self.supplier_partno_.get().alias_to_literal(supplier_partno)
        # TODO: handle pinmap and override_footprint for instance setup
        return self

    @property
    def mfr(self) -> str | None:
        literal = self.mfr_.get().try_extract_constrained_literal()
        return None if literal is None else str(literal)

    @property
    def partno(self) -> str | None:
        literal = self.partno_.get().try_extract_constrained_literal()
        return None if literal is None else str(literal)

    @property
    def supplier_id(self) -> str | None:
        literal = self.supplier_id_.get().try_extract_constrained_literal()
        return None if literal is None else str(literal)

    @property
    def supplier_partno(self) -> str | None:
        literal = self.supplier_partno_.get().try_extract_constrained_literal()
        return None if literal is None else str(literal)

    @property
    def pinmap(self) -> dict[str, F.Electrical | None]:
        pinmap = {}
        pointers = self.pinmap_.get().as_list()
        for pointer in pointers:
            tuple = F.Collections.PointerTuple.bind_instance(pointer.instance)
            pinmap[tuple.get_literals_as_list()[0]] = tuple.deref_pointer()
        return pinmap

    @property
    def override_footprint(
        self,
    ) -> tuple[fabll._ChildField[F.Footprints.is_footprint], str] | None:
        literal = F.Collections.PointerTuple.bind_instance(
            self.override_footprint_.get().instance
        ).get_literals_as_list()
        footprint = F.Collections.PointerTuple.bind_instance(
            self.override_footprint_.get().instance
        ).deref_pointer()
        return (footprint, literal)  # type: ignore

    @classmethod
    def MakeChild(
        cls,
        mfr: str | None,
        partno: str | None,
        supplier_id: str | None,
        supplier_partno: str | None,
        pinmap: dict[str, fabll._ChildField[F.Electrical] | None] | None,
        override_footprint: tuple[fabll._ChildField[F.Footprints.is_footprint], str]
        | None = None,
    ):
        out = fabll._ChildField(cls)
        # Literals
        if mfr is not None:
            out.add_dependant(
                F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.mfr_], mfr)
            )
        if partno is not None:
            out.add_dependant(
                F.Literals.Strings.MakeChild_ConstrainToLiteral(
                    [out, cls.partno_], partno
                )
            )
        if supplier_id is not None:
            out.add_dependant(
                F.Literals.Strings.MakeChild_ConstrainToLiteral(
                    [out, cls.supplier_id_], supplier_id
                )
            )
        if supplier_partno is not None:
            out.add_dependant(
                F.Literals.Strings.MakeChild_ConstrainToLiteral(
                    [out, cls.supplier_partno_], supplier_partno
                )
            )
        # Pinmap
        if pinmap is not None:
            for pin_str, electrical in pinmap.items():
                # Tuple
                pin_tuple = F.Collections.PointerTuple.MakeChild()
                out.add_dependant(pin_tuple)
                # Add tuple to pinmap set
                out.add_dependant(
                    F.Collections.PointerSet.MakeEdge(
                        [out, cls.pinmap_],
                        [pin_tuple],
                    )
                )
                # Pin Str
                lit = F.Literals.Strings.MakeChild(pin_str)
                out.add_dependant(lit)
                out.add_dependant(
                    F.Collections.PointerTuple.AppendLiteral(
                        tup_ref=[pin_tuple], elem_ref=[lit]
                    )
                )
                # Electrical
                if electrical is None:
                    continue
                out.add_dependant(
                    F.Collections.PointerTuple.SetPointer(
                        tup_ref=[pin_tuple], elem_ref=[electrical]
                    )
                )
        # Override footprint
        if override_footprint is not None:
            # Footprint Str
            lit = F.Literals.Strings.MakeChild(override_footprint[1])
            out.add_dependant(lit)
            out.add_dependant(
                F.Collections.PointerTuple.AppendLiteral(
                    tup_ref=[out, cls.override_footprint_], elem_ref=[lit]
                )
            )
            # Footprint
            fp = F.Literals.Strings.MakeChild(override_footprint[1])
            out.add_dependant(fp)
            out.add_dependant(
                F.Collections.PointerTuple.SetPointer(
                    tup_ref=[out, cls.override_footprint_], elem_ref=[fp]
                )
            )
        return out
