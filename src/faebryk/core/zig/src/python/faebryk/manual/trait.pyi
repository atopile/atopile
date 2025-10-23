from typing import Callable

from faebryk.core.zig.gen.graph.graph import BoundNode

class Trait:
    @staticmethod
    def add_trait_to(*, target: BoundNode, trait_type: BoundNode) -> BoundNode: ...
    @staticmethod
    def mark_as_trait(*, trait_type: BoundNode) -> None: ...
    @staticmethod
    def try_get_trait(
        *, target: BoundNode, trait_type: BoundNode
    ) -> BoundNode | None: ...
    @staticmethod
    def visit_implementers[T](
        *, trait_type: BoundNode, ctx: T, f: Callable[[T, BoundNode], None]
    ) -> None: ...
