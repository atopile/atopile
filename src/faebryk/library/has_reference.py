import faebryk.core.node as fabll

# from faebryk.core.reference import Reference
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer


class has_reference(fabll.Node):
    """Trait-attached reference"""

    @classmethod
    def MakeChild(cls, reference: fabll.ChildField[fabll.Node]):
        out = fabll.ChildField(cls)
        field = fabll.EdgeField(
            [out],
            [reference],
            edge=EdgePointer.build(identifier="reference", order=None),
        )
        out.add_dependant(field)
        return out

    @property
    def reference(self) -> fabll.Node:
        bound_node = EdgePointer.get_pointed_node_by_identifier(
            bound_node=self.instance, identifier="reference"
        )
        if bound_node is None:
            raise ValueError("has_reference is not bound")
        return fabll.Node.bind_instance(
            bound_node
        )  # TODO: Change return to reference type
