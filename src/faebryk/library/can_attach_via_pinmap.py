# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class can_attach_via_pinmap(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge((fabll.ImplementsTrait.MakeChild())).put_on_type()
    pin_list_ = F.Collections.PointerSet.MakeChild()

    def attach(self, pinmap: dict[str, F.Electrical | None]):
        for no, intf in pinmap.items():
            if intf is None:
                continue
            assert no in self.pin_list, (
                f"Pin {no} not in pin list: {self.pin_list.keys()}"
            )
            self.pin_list[no].attach(intf)

    @property
    def pin_list(self) -> dict[str, F.Pad]:
        pin_list = {}
        pointers = self.pin_list_.get().as_list()
        for pointer in pointers:
            tuple = F.Collections.PointerTuple.bind_instance(pointer.instance)
            pin_list[tuple.get_literals_as_list()[0]] = tuple.deref_pointer()
        return pin_list

    @classmethod
    def MakeChild(
        cls, pin_list: dict[str, fabll._ChildField[F.Pad]]
    ) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        for pad_str, pad in pin_list.items():
            # Make tuple
            pin_tuple = F.Collections.PointerTuple.MakeChild()
            out.add_dependant(pin_tuple)
            # Add tuple to pin list
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge(
                    [out, cls.pin_list_],
                    [pin_tuple],
                )
            )
            # Add pad str to tuple
            out.add_dependant(
                F.Collections.PointerTuple.AppendLiteral(
                    tup_ref=[pin_tuple], elem_ref=[pad_str]
                )
            )
            # Set pointer to pad
            out.add_dependant(
                F.Collections.PointerTuple.SetPointer(
                    tup_ref=[pin_tuple], elem_ref=[pad]
                )
            )
        return out
