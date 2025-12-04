from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.exporters.netlist.netlist import FBRKNetlist


def ensure_ref_and_value(c: fabll.Node) -> tuple[str, str]:
    value = (
        c.get_trait(F.has_simple_value_representation).get_value()
        if c.has_trait(F.has_simple_value_representation)
        else type(c).__name__
    )

    # At this point, all components MUST have a designator
    return c.get_trait(F.has_designator).get_designator(), value


class can_represent_kicad_footprint(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    kicad_footprint = FBRKNetlist.Component

    component_ = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(cls, component: fabll._ChildField):
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.component_],
                [component],
            )
        )

    def setup(self, component: fabll.Node) -> Self:
        self.component_.get().point(component)
        return self

    def get_name_and_value(self) -> tuple[str, str]:
        return ensure_ref_and_value(self.component_.get().deref())

    def get_pin_name(self, pin: F.Pad) -> str:
        return (
            self.component_.get()
            .deref()
            .get_trait(F.is_kicad_footprint)
            .get_pin_names()[pin]
        )

    def get_kicad_obj(self) -> FBRKNetlist.Component:
        fp = self.component_.get().deref().get_trait(F.has_footprint).get_footprint()

        kicad_footprint = fp.get_trait(
            F.is_kicad_footprint
        ).get_kicad_footprint_identifier()

        if kicad_footprint is None:
            raise ValueError("Kicad footprint is not set")

        properties = {"footprint": kicad_footprint}

        # # TODO not sure this is needed, also doing similar stuff elsewhere
        # for c in [fp, self.component]:
        #     if c.has_trait(F.has_descriptive_properties):
        #         properties.update(
        #             c.get_trait(F.has_descriptive_properties).get_properties()
        #         )

        properties["atopile_address"] = self.component_.get().deref().get_full_name()

        name, value = self.get_name_and_value()

        return FBRKNetlist.Component(
            name=name,
            properties=properties,
            value=value,
        )
