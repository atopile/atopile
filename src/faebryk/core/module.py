# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import TYPE_CHECKING, Callable, Iterable

from faebryk.core.moduleinterface import GraphInterfaceModuleSibling
from faebryk.core.node import Node, NodeException, f_field
from faebryk.core.trait import Trait
from faebryk.libs.util import unique_ref

if TYPE_CHECKING:
    from faebryk.core.moduleinterface import ModuleInterface

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
            for specialer_gif in self.specialized.get_direct_connections()
            if (specialer := specialer_gif.node) is not self
            and isinstance(specialer, Module)
        }
        if not specialers:
            return self

        specialest_next = unique_ref(
            specialer.get_most_special() for specialer in specialers
        )

        assert (
            len(specialest_next) == 1
        ), f"Ambiguous specialest {specialest_next} for {self}"
        return next(iter(specialest_next))

    def get_children_modules[T: Module](
        self: Node,
        types: type[T] | tuple[type[T], ...],
        most_special: bool = True,
        direct_only: bool = False,
        include_root: bool = False,
        f_filter: Callable[[T], bool] | None = None,
        sort: bool = True,
        special_filter: bool = True,
    ) -> set[T]:
        out = self.get_children(
            direct_only=direct_only,
            types=types,
            include_root=include_root,
            f_filter=f_filter,
            sort=sort,
        )
        if most_special:
            out = {n.get_most_special() for n in out}
            if special_filter and f_filter:
                out = {n for n in out if f_filter(n)}

        return out

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

        for src, dst in matrix:
            if src is None:
                continue
            if dst is None:
                raise Exception(f"Special module misses interface: {src.get_name()}")
            src.specialize(dst)

        for src, dst in param_matrix:
            if src is None:
                continue
            if dst is None:
                raise Exception(f"Special module misses parameter: {src.get_name()}")
            dst.alias_is(src)

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
                attach_to.add(special, container=attach_to.specialized_nodes)
            else:
                gen_parent = self.get_parent()
                if gen_parent:
                    gen_parent[0].add(special, name=f"{gen_parent[1]}_specialized")

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
                if src_m is None or dst_m is None:
                    if not allow_partial:
                        raise Exception(f"Node with name {k} not present in both")
                    continue
                src_m.connect(dst_m)

    def connect_interfaces_by_name(self, *dst: "Module", allow_partial: bool = False):
        type(self).connect_all_interfaces_by_name(
            self, dst, allow_partial=allow_partial
        )
