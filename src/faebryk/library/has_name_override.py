import faebryk.core.node as fabll
import faebryk.library._F as F


class has_name_override(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    name = F.Literals.Strings.MakeChild()
    detail = F.Literals.Strings.MakeChild()

    def setup(self, name: str, detail: str | None = None) -> fabll.Node:
        self.name.get().setup_from_values(name)
        self.detail.get().setup_from_values(detail or "")
        return self

    def get_name(self, with_detail: bool = False) -> str:
        return self.name.get().get_single() + (
            f"{self.detail.get().get_single()}" if with_detail else ""
        )
