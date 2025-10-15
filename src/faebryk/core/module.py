# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import TYPE_CHECKING, Callable

from deprecated import deprecated

from faebryk.core.node import Node, NodeException
from faebryk.core.trait import Trait

if TYPE_CHECKING:
    from faebryk.core.moduleinterface import ModuleInterface
    from faebryk.core.parameter import Parameter

logger = logging.getLogger(__name__)


class ModuleException(NodeException):
    def __init__(self, module: "Module", *args: object) -> None:
        self.module = module
        super().__init__(module, *args)


class Module(Node):
    class TraitT(Trait): ...

    def get_children_modules[T: Module](
        self: Node,
        types: type[T] | tuple[type[T], ...],
        most_special: bool = True,
        direct_only: bool = False,
        include_root: bool = False,
        f_filter: Callable[[T], bool] | None = None,
        sort: bool = True,
    ) -> set[T]:
        return set(
            self.get_children(
                direct_only=direct_only,
                types=types,
                include_root=include_root,
                f_filter=f_filter,
                sort=sort,
            )
        )

    class InvalidSpecializationError(Exception):
        """Cannot specialize module with special"""

        def __init__(
            self, message: str, *args, module: "Module", special: "Module", **kwargs
        ):
            self.message = message
            self.module = module
            self.special = special
            super().__init__(message, *args, **kwargs)

    @Node._collection_only
    def specialize[T: Module](
        self,
        special: T,
        matrix: list[tuple["ModuleInterface", "ModuleInterface"]] | None = None,
        attach_to: Node | None = None,
    ) -> T:
        if not isinstance(special, Module):
            raise TypeError(
                "Expected Module specialization target, got "
                f"{type(special).__qualname__}"
            )
        pending = getattr(self, "_pending_specializations", None)
        if pending is None:
            pending = []
            setattr(self, "_pending_specializations", pending)

        matrix_copy: list[tuple["ModuleInterface", "ModuleInterface"]] | None = None
        if matrix is not None:
            matrix_copy = [tuple(pair) for pair in matrix]

        pending.append(
            {
                "special": special,
                "matrix": matrix_copy,
                "attach_to": attach_to,
            }
        )
        if special not in self.specialized_:
            self.specialized_.append(special)
        # TODO: emit Zig-backed specialization edges when TypeGraph supports them.
        return special

    @deprecated("TODO: static helper function")
    def get_parameters(self) -> list["Parameter"]:
        from faebryk.core.parameter import Parameter

        return list(self.get_children(types=Parameter, direct_only=True))

    # TODO get rid of this abomination
    @property
    def reference_shim(self):
        from faebryk.library.has_single_electric_reference import (
            has_single_electric_reference,
        )

        return self.get_trait(has_single_electric_reference).get_reference()
