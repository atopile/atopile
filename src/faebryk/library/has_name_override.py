import faebryk.core.node as fabll
import faebryk.library._F as F


class has_name_override(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    name = F.Literals.Strings.MakeChild()

    def setup(self, name: str) -> fabll.Node:
        self.name.get().setup_from_values(name)
        return self

    def get_name(self) -> str:
        return self.name.get().get_single()
