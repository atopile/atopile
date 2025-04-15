import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.libs.util import KeyErrorNotFound, cast_assert


class crosses_footprint_boundary(ModuleInterface.TraitT.decless()):
    def __init__(self):
        super().__init__()

    def _get_parent(self, node: Node) -> Node | None:
        if (maybe_parent := node.get_parent()) is None:
            return None

        parent, _ = maybe_parent
        return cast_assert(Node, parent)

    def check(self) -> bool:
        """
        Determine if the provided interface forms a connection between two modules
        with distinct containingfootprints.
        """
        obj = self.get_obj(ModuleInterface)

        try:
            footprint = obj.get_parent_with_trait(F.has_footprint)
        except KeyErrorNotFound:
            # checked from the other side
            return False

        for mif, _ in obj.get_connected().items():
            try:
                connected_footprint = mif.get_parent_with_trait(F.has_footprint)
            except KeyErrorNotFound:
                connected_footprint = None

            if footprint != connected_footprint:
                return True

        return False
