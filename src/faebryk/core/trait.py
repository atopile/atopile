# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

from faebryk.core.node import Node, NodeException
from faebryk.libs.util import cast_assert

logger = logging.getLogger(__name__)


class TraitNotFound(NodeException):
    def __init__(self, node: Node, trait: type["Trait"], *args: object) -> None:
        super().__init__(
            node, *args, f"Trait {trait} not found in {type(node)}[{node}]"
        )
        self.trait = trait


class TraitImplementationConfusedWithTrait(NodeException):
    def __init__(self, node: Node, trait: type["Trait"], *args: object) -> None:
        super().__init__(
            node,
            *args,
            "Implementation or trait was used where the other was expected.",
        )
        self.trait = trait


class TraitAlreadyExists(NodeException):
    def __init__(self, node: Node, trait: "TraitImpl", *args: object) -> None:
        trait_type = trait.__trait__
        super().__init__(
            node,
            *args,
            f"Trait {trait_type} already exists in {node}: {node.get_trait(trait_type)}"
            f", trying to add {trait}",
        )
        self.trait = trait


class TraitUnbound(NodeException):
    def __init__(self, node: Node, *args: object) -> None:
        super().__init__(node, *args, f"Trait {node} is not bound to a node")


class Trait(Node):
    __decless_trait__: bool = False

    @classmethod
    def impl[T: "Trait"](cls: type[T]):
        class _Impl(TraitImpl, cls): ...

        # this should be outside the class def to prevent
        # __init_subclass__ from overwriting it
        _Impl.__trait__ = cls

        return _Impl

    def __new__(cls, *args, **kwargs):
        if not issubclass(cls, TraitImpl):
            raise TypeError("Don't instantiate Trait use Trait.impl instead")

        return super().__new__(cls)

    @classmethod
    def decless(cls):
        class _Trait(cls): ...

        _Trait.__decless_trait__ = True

        return _Trait.impl()


class TraitImpl(Node):
    __trait__: type[Trait] = None

    @property
    def obj(self) -> Node:
        p = self.get_parent()
        if not p:
            raise TraitUnbound(self)
        return p[0]

    def get_obj[T: Node](self, type: type[T]) -> T:
        return cast_assert(type, self.obj)

    def cmp(self, other: "TraitImpl") -> tuple[bool, "TraitImpl"]:
        assert type(other), TraitImpl

        # If other same or more specific
        if other.implements(self.__trait__):
            return True, other

        # If we are more specific
        if self.implements(other.__trait__):
            return True, self

        return False, self

    def implements(self, trait: type[Trait]):
        assert issubclass(trait, Trait)

        return issubclass(self.__trait__, trait)

    # Overwriteable --------------------------------------------------------------------

    def _handle_added_to_parent(self):
        self.on_obj_set()

    def on_obj_set(self): ...

    def handle_duplicate(self, other: "TraitImpl", node: Node) -> bool:
        assert other is not self
        _, candidate = other.cmp(self)
        if candidate is not self:
            return False

        node.del_trait(other.__trait__)
        return True

        # raise TraitAlreadyExists(node, self)

    # override this to implement a dynamic trait
    def is_implemented(self):
        return True
