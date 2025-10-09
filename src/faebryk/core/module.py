# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import TYPE_CHECKING, Callable, Iterable

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

    def specialize[T: Module](
        self,
        special: T,
        matrix: list[tuple["ModuleInterface", "ModuleInterface"]] | None = None,
        attach_to: Node | None = None,
    ) -> T:
        raise NotImplementedError("zig core - specialization is not implemented")

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
