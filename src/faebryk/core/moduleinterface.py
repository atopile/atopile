# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable, Self, Sequence

from faebryk.core.node import Node
from faebryk.core.trait import Trait
from faebryk.libs.util import ConfigFlag

if TYPE_CHECKING:
    from faebryk.core.link import Link

logger = logging.getLogger(__name__)


IMPLIED_PATHS = ConfigFlag("IMPLIED_PATHS", default=False, descr="Use implied paths")

type Bridgable[T: "ModuleInterface"] = Node | T


class _ModuleInterfaceEdgeStub:
    def __init__(self, owner: "ModuleInterface", kind: str) -> None:
        self._owner = owner
        self._kind = kind

    def _fail(self, operation: str) -> None:
        raise NotImplementedError(
            f"TODO: Zig core migration – ModuleInterface.{self._kind}.{operation} "
            "is not implemented"
        )

    def connect(self, *args, **kwargs):
        self._fail("connect")

    def is_connected_to(self, *args, **kwargs):
        self._fail("is_connected_to")

    def get_connected_nodes(self, *args, **kwargs):
        self._fail("get_connected_nodes")

    def __getattr__(self, name: str):
        self._fail(name)

    def __repr__(self) -> str:
        return (
            f"<ModuleInterfaceEdgeStub kind={self._kind} "
            f"owner={type(self._owner).__name__}>"
        )


class ModuleInterface(Node):
    class TraitT(Trait): ...

    def __preinit__(self) -> None: ...

    @classmethod
    def LinkDirectShallow(cls):
        raise NotImplementedError(
            "TODO: Zig core migration – ModuleInterface.LinkDirectShallow is not "
            "available"
        )

    @property
    def specializes(self) -> _ModuleInterfaceEdgeStub:
        return self._get_edge_stub("specializes")

    @property
    def specialized(self) -> _ModuleInterfaceEdgeStub:
        return self._get_edge_stub("specialized")

    @property
    def connected(self) -> _ModuleInterfaceEdgeStub:
        return self._get_edge_stub("connected")

    def _get_edge_stub(self, name: str) -> _ModuleInterfaceEdgeStub:
        attr = f"_{name}_stub"
        if not hasattr(self, attr):
            setattr(self, attr, _ModuleInterfaceEdgeStub(owner=self, kind=name))
        return getattr(self, attr)

    def connect(
        self: Self, *other: Self, link: type["Link"] | "Link" | None = None
    ) -> Self:
        raise NotImplementedError(
            "TODO: Zig core migration – ModuleInterface.connect is not implemented"
        )

    def connect_via(
        self,
        bridge: Bridgable[Self] | Sequence[Bridgable[Self]],
        *other: Self,
        link=None,
    ):
        raise NotImplementedError(
            "TODO: Zig core migration – ModuleInterface.connect_via is not implemented"
        )

    def connect_shallow(self, *other: Self) -> Self:
        raise NotImplementedError(
            "TODO: Zig core migration – ModuleInterface.connect_shallow is not implemented"
        )

    def get_connected(self, include_self: bool = False) -> dict[Self, object]:
        raise NotImplementedError(
            "TODO: Zig core migration – ModuleInterface.get_connected is not implemented"
        )

    def is_connected_to(self, other: "ModuleInterface") -> list[object]:
        raise NotImplementedError(
            "TODO: Zig core migration – ModuleInterface.is_connected_to is not implemented"
        )

    def specialize[T: ModuleInterface](self, special: T) -> T:
        raise NotImplementedError(
            "TODO: Zig core migration – ModuleInterface.specialize is not implemented"
        )

    @staticmethod
    def _path_with_least_conditionals(paths: list[object]) -> object:
        raise NotImplementedError(
            "TODO: Zig core migration – ModuleInterface path resolution is not implemented"
        )

    def _connect_via_implied_paths(self, other: Self, paths: list[object]):
        raise NotImplementedError(
            "TODO: Zig core migration – ModuleInterface implied path hookup is not "
            "implemented"
        )

    @staticmethod
    def _group_into_buses[T: ModuleInterface](mifs: Iterable[T]) -> dict[T, set[T]]:
        raise NotImplementedError(
            "TODO: Zig core migration – ModuleInterface bus grouping is not implemented"
        )

    # TODO get rid of this abomination
    @property
    def reference_shim(self):
        from faebryk.library.has_single_electric_reference import (
            has_single_electric_reference,
        )

        return self.get_trait(has_single_electric_reference).get_reference()
