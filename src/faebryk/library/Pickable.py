# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, StrEnum, auto
from typing import TYPE_CHECKING, Self

import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none

if TYPE_CHECKING:
    from faebryk.libs.picker.picker import PickedPart

logger = logging.getLogger(__name__)


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


class is_pickable(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def get_pickable_node(self) -> fabll.Node:
        """
        Gets the node associate with the is_pickable trait.
        This is a little weird as is_pickable_by_type etc
        have a trait instance of is_pickable, not the node itself.
        """
        owner_trait = fabll.Traits(self).get_obj_raw()
        pickable_node = fabll.Traits(owner_trait).get_obj_raw()
        return pickable_node


class is_pickable_by_type(fabll.Node):
    """
    Marks a module as being parametrically selectable using the given parameters.

    Must map to an existing API endpoint.

    Should be named "pickable" to aid overriding by subclasses.
    """

    class Endpoint(StrEnum):
        """Query endpoints known to the API."""

        RESISTORS = "resistors"
        CAPACITORS = "capacitors"
        INDUCTORS = "inductors"

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    endpoint_ = F.Parameters.EnumParameter.MakeChild(enum_t=Endpoint)
    params_ = F.Collections.PointerSet.MakeChild()
    # TODO: Forward this trait to parent
    _is_pickable = fabll.Traits.MakeEdge(is_pickable.MakeChild())

    def get_params(self) -> "list[F.Parameters.is_parameter]":
        param_tuples = self.params_.get().as_list()
        parameters = [
            F.Collections.PointerTuple.bind_instance(param_tuple.instance)
            .deref_pointer()
            .get_trait(F.Parameters.is_parameter)
            for param_tuple in param_tuples
        ]

        return parameters

    def get_param(self, param_name: str) -> "F.Parameters.is_parameter":
        param_tuples = self.params_.get().as_list()
        for param_tuple in param_tuples:
            bound_param_tuple = F.Collections.PointerTuple.bind_instance(
                param_tuple.instance
            )
            p_name = bound_param_tuple.get_literals_as_list()[0]
            if p_name == param_name:
                return bound_param_tuple.deref_pointer().get_trait(
                    F.Parameters.is_parameter
                )
        raise ValueError(f"Param {param_name} not found")

    @property
    def endpoint(self) -> str:
        return str(self.endpoint_.get().force_extract_literal().get_single())

    @property
    def pick_type(self) -> graph.BoundNode:
        parent_info = self.get_parent()
        if parent_info is None:
            raise Exception("is_pickable_by_type has no parent")
        parent, _ = parent_info
        return not_none(parent.get_type_node())

    @classmethod
    def MakeChild(cls, endpoint: Endpoint, params: dict[str, fabll._ChildField]):
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
                [out, cls.endpoint_], endpoint
            )
        )
        for param_name, param_ref in params.items():
            # Create tuple
            param_tuple = F.Collections.PointerTuple.MakeChild()
            out.add_dependant(param_tuple)
            # Add tuple to params_ set
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge(
                    [out, cls.params_],
                    [param_tuple],
                )
            )
            # Add string to tuple
            lit = F.Literals.Strings.MakeChild(param_name)
            out.add_dependant(lit)
            out.add_dependant(
                F.Collections.PointerTuple.AppendLiteral(
                    tup_ref=[param_tuple], elem_ref=[lit]
                )
            )
            # Add param reference to tuple
            out.add_dependant(
                F.Collections.PointerTuple.SetPointer(
                    tup_ref=[param_tuple], elem_ref=[param_ref]
                )
            )
        return out


class is_pickable_by_supplier_id(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    supplier_part_id_ = fabll._ChildField(F.Parameters.StringParameter)
    supplier_ = fabll._ChildField(F.Parameters.StringParameter)
    # TODO: Forward this trait to parent
    _is_pickable = fabll.Traits.MakeEdge(is_pickable.MakeChild())

    class Supplier(Enum):
        LCSC = auto()

    def get_supplier_part_id(self) -> str:
        return str(self.supplier_part_id_.get().force_extract_literal().get_values()[0])

    def get_supplier(self) -> str:
        return str(self.supplier_.get().force_extract_literal().get_values()[0])

    def setup(
        self, supplier_part_id: str, supplier: "is_pickable_by_supplier_id.Supplier"
    ) -> Self:
        self.supplier_part_id_.get().alias_to_literal(supplier_part_id)
        self.supplier_.get().alias_to_literal(supplier.name)
        return self

    @classmethod
    def MakeChild(
        cls, supplier_part_id: str, supplier: Supplier = Supplier.LCSC
    ) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.supplier_part_id_], supplier_part_id
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.supplier_], supplier.name
            )
        )
        return out


class is_pickable_by_part_number(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    manufacturer_ = fabll._ChildField(F.Parameters.StringParameter)
    partno_ = fabll._ChildField(F.Parameters.StringParameter)

    # TODO: Forward this trait to parent
    _is_pickable = fabll.Traits.MakeEdge(is_pickable.MakeChild())

    @classmethod
    def try_check_or_convert(cls, module: fabll.is_module) -> Self | None:
        if pbpn := module.try_get_sibling_trait(cls):
            return pbpn

        if (mfr_t := module.try_get_sibling_trait(has_mfr_assigned)) and (
            mpn_t := module.try_get_sibling_trait(has_mpn_assigned)
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
        from faebryk.libs.picker.lcsc import PickedPartLCSC

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

        if (
            not (
                supplier_id := self.supplier_id.get().try_extract_constrained_literal()
            )
            or not supplier_id.is_singleton()
            or supplier_id.get_single() != "lcsc"
        ):
            raise ValueError(f"Supplier {supplier_id} not supported")
        return PickedPartLCSC(
            manufacturer=manufacturer,
            partno=partno,
            supplier_partno=supplier_partno,
        )

    @property
    def removed(self) -> bool:
        return self.has_trait(F.has_part_removed)

    @classmethod
    def MakeChild(
        cls,
        supplier_id: str,
        supplier_partno: str,
        manufacturer: str,
        partno: str,
    ) -> fabll._ChildField[Self]:
        """Create a child field with part info constraints."""
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.manufacturer], manufacturer
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.partno], partno)
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.supplier_partno], supplier_partno
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.supplier_id], supplier_id
            )
        )
        return out

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


# ----------------------------------------
#    Tests
# ----------------------------------------


def test_get_pickable_node():
    import faebryk.core.faebrykpy as fbrk
    from faebryk.library.Resistor import Resistor

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        r1 = Resistor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Get pickable trait instance of r1
    pickable_trait = app.r1.get().get_trait(is_pickable_by_type).get_trait(is_pickable)

    assert pickable_trait is not None
    pickable_node = pickable_trait.get_pickable_node()
    assert pickable_node.get_full_name() == app.r1.get().get_full_name()
