# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class can_attach_to_footprint_via_pinmap(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    # TODO: Forward this trait to parent
    _can_attach_to_footprint = fabll.ChildField(F.can_attach_to_footprint)

    pinmap_ = F.Collections.PointerSet.MakeChild()

    def attach(self, footprint: F.Footprint):
        # TODO: Forward this trait to parent*2
        has_footprint = fabll.Traits.create_and_add_instance_to(
            node=self, trait=F.has_footprint
        )
        has_footprint.set_footprint(footprint)

        footprint.get_trait(F.can_attach_via_pinmap).attach(self.pinmap)

    @property
    def pinmap(self) -> dict[str, F.Electrical | None]:
        pinmap = {}
        pointers = self.pinmap_.get().as_list()
        for pointer in pointers:
            tuple = F.Collections.PointerTuple.bind_instance(pointer.instance)
            pinmap[tuple.get_literals_as_list()[0]] = tuple.deref_pointer()
        return pinmap

    @classmethod
    def MakeChild(
        cls,
        pinmap: dict[str, fabll.ChildField[F.Electrical] | None]
        | dict[str, fabll.ChildField[F.Electrical]],
    ) -> fabll.ChildField:
        out = fabll.ChildField(cls)
        for pin_str, electrical in pinmap.items():
            # Tuple
            pin_tuple = F.Collections.PointerTuple.MakeChild()
            out.add_dependant(pin_tuple)
            # Add tuple to pinmap set
            out.add_dependant(
                F.Collections.PointerSet.EdgeField(
                    [out, cls.pinmap_],
                    [pin_tuple],
                )
            )
            # Pin Str
            lit = F.Literals.Strings.MakeChild(value=pin_str)
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
        return out
