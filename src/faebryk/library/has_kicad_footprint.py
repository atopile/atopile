# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_kicad_footprint(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    kicad_identifier_ = F.Parameters.StringParameter.MakeChild()
    pinmap_ = F.Collections.PointerSet.MakeChild()

    def get_kicad_footprint(self) -> str | None:
        literal = self.kicad_identifier_.get().try_extract_constrained_literal()
        return None if literal is None else literal.get_value()

    def get_pin_names(self) -> dict[F.Pad, str]:
        pin_names = {}
        pointers = self.pinmap_.get().as_list()
        for pointer in pointers:
            tuple = F.Collections.PointerTuple.bind_instance(pointer.instance)
            pin_names[tuple.deref_pointer()] = tuple.get_literals_as_list()[0]
        return pin_names

    @classmethod
    def MakeChild(
        cls, kicad_identifier: str, pinmap: dict[fabll._ChildField[F.Pad], str]
    ) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.kicad_identifier_], kicad_identifier
            )
        )

        for pad, pad_str in pinmap.items():
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
            # Pad Str
            lit = F.Literals.Strings.MakeChild(pad_str)
            out.add_dependant(lit)
            out.add_dependant(
                F.Collections.PointerTuple.AppendLiteral(
                    tup_ref=[pin_tuple], elem_ref=[lit]
                )
            )
            # Electrical
            if pad is None:
                continue
            out.add_dependant(
                F.Collections.PointerTuple.SetPointer(
                    tup_ref=[pin_tuple], elem_ref=[pad]
                )
            )
        return out

    def setup(self, kicad_identifier: str, pinmap: dict[F.Pad, str]) -> Self:
        self.kicad_identifier_.get().constrain_to_single(
            g=self.instance.g(), value=kicad_identifier
        )
        for pad, pad_str in pinmap.items():
            # Create pin_tuple instance
            pin_tuple = F.Collections.PointerTuple.bind_typegraph(
                tg=self.tg
            ).create_instance(g=self.instance.g())
            pin_tuple.pointer.get().point(pad)
            pin_tuple.append_literal(pad_str)
            self.pinmap_.get().append(pin_tuple)
        return self
