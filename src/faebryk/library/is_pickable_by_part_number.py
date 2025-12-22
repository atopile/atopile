# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_mpn_assigned(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    mpn_ = fabll._ChildField(F.Parameters.StringParameter)

    @classmethod
    def MakeChild(cls, mpn: str) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.mpn_], mpn)
        )
        return out

    def get_mpn(self) -> str:
        return self.mpn_.get().force_extract_literal().get_single()


class has_mfr_assigned(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    mfr_ = fabll._ChildField(F.Parameters.StringParameter)

    @classmethod
    def MakeChild(cls, mfr: str) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.mfr_], mfr)
        )
        return out

    def get_manufacturer(self) -> str:
        return self.mfr_.get().force_extract_literal().get_single()


class is_pickable_by_part_number(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    manufacturer_ = fabll._ChildField(F.Parameters.StringParameter)
    partno_ = fabll._ChildField(F.Parameters.StringParameter)

    # TODO: Forward this trait to parent
    _is_pickable = fabll.Traits.MakeEdge(F.is_pickable.MakeChild())

    @classmethod
    def try_check_or_convert(cls, module: fabll.is_module) -> Self | None:
        if pbpn := module.try_get_sibling_trait(cls):
            return pbpn

        if (mfr_t := module.try_get_sibling_trait(F.has_mfr_assigned)) and (
            mpn_t := module.try_get_sibling_trait(F.has_mpn_assigned)
        ):
            return fabll.Traits.create_and_add_instance_to(
                fabll.Traits(module).get_obj_raw(), cls
            ).setup(
                manufacturer=mfr_t.get_manufacturer(),
                partno=mpn_t.get_mpn(),
            )

        return None

    def get_manufacturer(self) -> str:
        return self.manufacturer_.get().force_extract_literal().get_values()[0]

    def get_partno(self) -> str:
        return self.partno_.get().force_extract_literal().get_values()[0]

    def setup(self, manufacturer: str, partno: str) -> Self:
        self.manufacturer_.get().alias_to_literal(manufacturer)
        self.partno_.get().alias_to_literal(partno)
        return self

    @classmethod
    def MakeChild(cls, manufacturer: str, partno: str) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.manufacturer_], manufacturer
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.partno_], partno)
        )
        return out
