# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import TYPE_CHECKING, Callable, Iterable

from faebryk.core.cpp import GraphInterfaceModuleSibling
from faebryk.core.node import Node, NodeException, f_field
from faebryk.core.trait import Trait
from faebryk.libs.exceptions import accumulate
from faebryk.libs.util import cast_assert, unique_ref

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

    specializes = f_field(GraphInterfaceModuleSibling)(is_parent=False)
    specialized = f_field(GraphInterfaceModuleSibling)(is_parent=True)

    def get_most_special(self) -> "Module":
        specialers = {
            specialer
            for specialer_gif in self.specialized.get_gif_edges()
            if (specialer := specialer_gif.node) is not self
            and isinstance(specialer, Module)
        }
        if not specialers:
            return self

        specialest_next = unique_ref(
            specialer.get_most_special() for specialer in specialers
        )

        assert len(specialest_next) == 1, (
            f"Ambiguous specialest {specialest_next} for {self}"
        )
        return next(iter(specialest_next))

    def get_children_modules[T: Module](
        self: Node,
        types: type[T] | tuple[type[T], ...],
        most_special: bool = True,
        direct_only: bool = False,
        include_root: bool = False,
        f_filter: Callable[[T], bool] | None = None,
        sort: bool = True,
    ) -> set[T]:
        out = self.get_children(
            direct_only=direct_only,
            types=types,
            include_root=include_root,
            f_filter=f_filter,
            sort=sort,
        )
        out_specialized = {
            n.get_most_special()
            for n in self.get_children(
                direct_only=direct_only,
                types=Module,
                include_root=include_root,
                f_filter=lambda x: x.get_most_special() != x,
                sort=sort,
            )
        }
        if most_special:
            special_out = set()
            todo = out_specialized
            # TODO can be done more efficiently by just allowing in the graph search
            # specialize edges
            for n in out:
                # Filter out children of specialized modules
                has_specialized_parent = n.get_parent_f(
                    lambda x: isinstance(x, Module) and x.get_most_special() != x
                )
                if has_specialized_parent:
                    continue
                n_special = n.get_most_special()
                # Non-special can just pass
                if n_special is n:
                    special_out.add(n_special)
                    continue
                # Already processed
                if n_special in out | special_out:
                    continue
                # To process children
                todo.add(n)

            for n_special in todo:
                special_out.update(
                    n_special.get_children_modules(
                        types=types,
                        most_special=True,
                        direct_only=direct_only,
                        include_root=True,
                        f_filter=f_filter,
                        sort=sort,
                    )
                )
            out = special_out

        return out

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
        from faebryk.core.moduleinterface import ModuleInterface
        from faebryk.core.parameter import Parameter

        logger.debug(f"Specializing Module {self} with {special}" + " " + "=" * 20)

        def get_node_prop_matrix[N: Node](sub_type: type[N]):
            return list(self.zip_children_by_name_with(special, sub_type).values())

        if matrix is None:
            matrix = get_node_prop_matrix(ModuleInterface)

        # TODO add warning if not all src interfaces used
        param_matrix = get_node_prop_matrix(Parameter)

        err_acc = accumulate(self.InvalidSpecializationError)

        for src, dst in matrix:
            with err_acc.collect():
                if src is None:
                    continue
                if dst is None:
                    raise self.InvalidSpecializationError(
                        f"Special module misses interface: {src.get_name()}",
                        module=self,
                        special=special,
                    )
                src.specialize(dst)

        for src, dst in param_matrix:
            with err_acc.collect():
                if src is None:
                    continue
                if dst is None:
                    raise self.InvalidSpecializationError(
                        f"Special module misses parameter: {src.get_name()}",
                        module=self,
                        special=special,
                    )
                dst.alias_is(src)

        err_acc.raise_errors()

        # TODO this cant work
        # for t in self.traits:
        #    # TODO needed?
        #    if special.has_trait(t.trait):
        #        continue
        #    special.add(t)

        self.specialized.connect(special.specializes)

        # Attach to new parent
        has_parent = special.get_parent() is not None
        assert not has_parent or attach_to is None
        if not has_parent:
            if attach_to:
                attach_to.add(special, container=attach_to.specialized_)
            else:
                gen_parent = self.get_parent()
                if gen_parent:
                    cast_assert(Node, gen_parent[0]).add(
                        special, name=f"{gen_parent[1]}_specialized"
                    )

        return special

    @staticmethod
    def connect_all_interfaces_by_name(
        src: Iterable["Module"] | "Module",
        dst: Iterable["Module"] | "Module",
        allow_partial: bool = False,
    ):
        from faebryk.core.moduleinterface import ModuleInterface

        if isinstance(src, Module):
            src = [src]
        if isinstance(dst, Module):
            dst = [dst]

        for src_, dst_ in zip(src, dst):
            for k, (src_m, dst_m) in src_.zip_children_by_name_with(
                dst_, ModuleInterface
            ).items():
                # TODO: careful this also connects runtime children
                # for now skip stuff prefixed with _
                if k.startswith("_"):
                    continue
                if src_m is None or dst_m is None:
                    if not allow_partial:
                        raise Exception(f"Node with name {k} not present in both")
                    continue
                src_m.connect(dst_m)

    def connect_interfaces_by_name(self, *dst: "Module", allow_partial: bool = False):
        type(self).connect_all_interfaces_by_name(
            self, dst, allow_partial=allow_partial
        )

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
