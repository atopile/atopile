# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import TYPE_CHECKING, TypeGuard, cast

from faebryk.core.node import Node, NodeException
from faebryk.libs.util import KeyErrorAmbiguous, KeyErrorNotFound, cast_assert

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from faebryk.core.graph import Graph


class TraitNotFound(NodeException):
    def __init__(self, node: Node, trait: type["Trait"], *args: object) -> None:
        super().__init__(
            node,
            *args,
            f"Trait `{trait.__qualname__}` not found in "
            f"`{type(node).__qualname__}[{node}]`",
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
            f"Trait `{trait_type.__qualname__}` already exists in "
            f"`{node}`: `{node.get_trait(trait_type)}`"
            f", trying to add `{trait.__qualname__}`",
        )
        self.trait = trait


class TraitUnbound(NodeException):
    def __init__(self, node: Node, *args: object) -> None:
        super().__init__(node, *args, f"Trait `{node}` is not bound to a node")


class Trait(Node):
    __decless_trait__: bool = False

    if TYPE_CHECKING:
        TraitT: type["TraitT"]

    # TODO once
    @classmethod
    def impl[T: "Trait"](cls: type[T]):
        # Implements TraitImpl
        class _Impl(cls):
            __trait__: type[Trait] = cls

            @property
            def obj(self) -> Node:
                p = self.get_parent()
                if not p:
                    raise TraitUnbound(self)
                return cast_assert(Node, p[0])

            def get_obj[TN: Node](self, type: type[TN]) -> TN:
                return cast_assert(type, self.obj)

            def cmp(self, new_t: "TraitImpl") -> tuple[bool, "TraitImpl"]:
                assert TraitImpl.is_traitimpl(new_t)

                # If new same or more specific
                if new_t.implements(self.__trait__):
                    return True, new_t

                # hack type (ghetto protocol)
                traitimpl = cast(TraitImpl, self)

                # If we are more specific
                if self.implements(new_t.__trait__):
                    return True, traitimpl

                return False, traitimpl

            def implements(self, trait: type[Trait]):
                return trait.is_traitimpl(self)

            # Overwriteable ------------------------------------------------------------

            def _handle_added_to_parent(self):
                from faebryk.library.is_lazy import is_lazy

                # deferred to later
                if self.has_trait(is_lazy):
                    return
                self.on_obj_set()

            def on_obj_set(self): ...

            def handle_duplicate(self, old: "TraitImpl", node: Node) -> bool:
                assert old is not self
                _, candidate = old.cmp(cast(TraitImpl, self))
                if candidate is not self:
                    # raise TraitAlreadyExists(node, self)
                    return False

                node.del_trait(old.__trait__)
                return True

            # override this to implement a dynamic trait
            def is_implemented(self):
                return True

        # this should be outside the class def to prevent
        # __init_subclass__ from overwriting it
        _Impl.__trait__ = cls
        _Impl.__name__ = f"{cls.__name__}Impl"
        _Impl.__original_init__ = cls.__init__  # type: ignore

        return _Impl

    def __new__(cls, *args, **kwargs):
        if not TraitImpl.is_traitimpl_type(cls):
            raise TypeError(f"Don't instantiate Trait [{cls}] use Trait.impl instead")

        return super().__new__(cls, *args, **kwargs)  # type: ignore

    @classmethod
    def decless(cls):
        class _Trait(cls): ...

        _Trait.__decless_trait__ = True

        return _Trait.impl()

    @classmethod
    def is_traitimpl(cls, obj: "Trait") -> TypeGuard["TraitImpl"]:
        assert issubclass(cls, Trait)
        if not TraitImpl.is_traitimpl(obj):
            return False
        return issubclass(obj.__trait__, cls)

    # TODO check subclasses implementing abstractmethods (use subclass_init)

    @classmethod
    def find_unique(cls, G: "Graph"):
        from faebryk.core.graph import GraphFunctions

        matches = GraphFunctions(G).nodes_with_trait(cls)
        if len(matches) != 1:
            if len(matches) == 0:
                raise KeyErrorNotFound(cls)
            else:
                raise KeyErrorAmbiguous(matches, cls)
        return matches[0][1]


# Hack, using this as protocol
# Can't use actual protocol because CNode doesn't allow multiple inheritance
class TraitImpl(Node):
    """
    Warning: Do not instancecheck against this type!
    """

    __trait__: type[Trait]

    @property
    def obj(self) -> Node: ...
    def get_obj[T: Node](self, type: type[T]) -> T: ...
    def cmp(self, other: "TraitImpl") -> tuple[bool, "TraitImpl"]: ...
    def implements(self, trait: type[Trait]): ...

    # Overwriteable --------------------------------------------------------------------
    def _handle_added_to_parent(self): ...
    def on_obj_set(self): ...
    def handle_duplicate(self, old: "TraitImpl", node: Node) -> bool:
        """
        Returns True if the duplicate was handled, False if the trait should be skipped
        """
        ...

    def is_implemented(self): ...

    @staticmethod
    def is_traitimpl(obj) -> TypeGuard["TraitImpl"]:
        if not isinstance(obj, Trait):
            return False
        return getattr(obj, "__trait__", None) is not None

    @staticmethod
    def is_traitimpl_type(obj) -> TypeGuard[type["TraitImpl"]]:
        if not issubclass(obj, Trait):
            return False
        return getattr(obj, "__trait__", None) is not None


class TraitT(Trait): ...


Trait.TraitT = TraitT
