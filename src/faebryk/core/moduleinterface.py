# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Self, Sequence

from faebryk.core.node import Node
from faebryk.core.trait import Trait
from faebryk.libs.util import ConfigFlag

if TYPE_CHECKING:
    from faebryk.core.link import Link


IMPLIED_PATHS = ConfigFlag("IMPLIED_PATHS", default=False, descr="Use implied paths")

type Bridgable[T: "ModuleInterface"] = Node | T
LiteralValue = int | float | str | bool


class ModuleInterface(Node):
    class TraitT(Trait): ...

    def __preinit__(self) -> None: ...

    def __init__(self) -> None:
        super().__init__()
        self._connections: set["ModuleInterface"] = set()
        # TODO: Zig-backed specialization wiring to be implemented in typegraph build
        self._pending_specializations: list["ModuleInterface"] = []
        self._connection_link_types: dict["ModuleInterface", set[type["Link"]]] = {}
        self._connection_directional: dict["ModuleInterface", bool] = {}

    @staticmethod
    def _format_link_type_name(link_type: type["Link"]) -> str:
        module = getattr(link_type, "__module__", "")
        qualname = getattr(
            link_type, "__qualname__", getattr(link_type, "__name__", str(link_type))
        )
        if module and module not in {"__main__", "builtins"}:
            return f"{module}.{qualname}"
        return qualname

    # Internal helpers ----------------------------------------------------------------

    @staticmethod
    def _normalize_link_type(link: type["Link"] | "Link" | None) -> type["Link"] | None:
        if link is None:
            return None
        if isinstance(link, type):
            return link
        return type(link)

    def _record_link_type(
        self, other: "ModuleInterface", link_type: type["Link"] | None
    ) -> None:
        if link_type is None:
            return
        buckets = self._connection_link_types.get(other)
        if buckets is None:
            buckets = set()
            self._connection_link_types[other] = buckets
        buckets.add(link_type)
        if self._is_directional_link_type(link_type):
            self._connection_directional[other] = True

    def _get_recorded_link_types(self) -> dict["ModuleInterface", set[type["Link"]]]:
        return {
            neighbour: set(types)
            for neighbour, types in self._connection_link_types.items()
        }

    @Node._collection_only
    def _get_connection_attributes(
        self, other: "ModuleInterface"
    ) -> dict[str, LiteralValue]:
        """
        Aggregate link metadata recorded between this interface and `other`.

        Returns a mapping suitable for Zig edge dynamic attributes,
        using only Literal-compatible value types.
        """

        def collect(
            source: "ModuleInterface", target: "ModuleInterface"
        ) -> set[type["Link"]]:
            return source._connection_link_types.get(target, set())

        link_types = set(collect(self, other))
        link_types.update(collect(other, self))

        if not link_types:
            return {}

        formatted = sorted(
            self._format_link_type_name(link_type) for link_type in link_types
        )

        return {
            "link_type_count": len(formatted),
            "link_types": ", ".join(formatted),
        }

    @Node._collection_only
    def _is_connection_directional(self, other: "ModuleInterface") -> bool:
        if self._connection_directional.get(other):
            return True
        reciprocal = getattr(other, "_connection_directional", {}).get(self)
        return bool(reciprocal)

    @staticmethod
    def _is_directional_link_type(link_type: type["Link"]) -> bool:
        if getattr(link_type, "DIRECTIONAL", False):
            return True

        name = getattr(link_type, "__qualname__", link_type.__name__)
        # TODO: the link should specify
        known_directional = {
            "LinkPointer",
            "LinkSibling",
            "LinkParent",
            "LinkNamedParent",
        }
        if name in known_directional or name.split(".")[-1] in known_directional:
            return True

        try:
            from faebryk.core.link import (
                LinkNamedParent,
                LinkParent,
                LinkPointer,
                LinkSibling,
            )
        except Exception:
            return False

        try:
            return issubclass(
                link_type, (LinkPointer, LinkSibling, LinkParent, LinkNamedParent)
            )
        except TypeError:
            return False

    @Node._runtime_only
    def _find_connected(self) -> set["ModuleInterface"]:
        # TODO: Implement in Zig pathfinder module
        # This requires porting the pathfinding logic to Zig core
        # Cannot query connections without instance graph

        # Always require instance binding for graph queries
        _ = self._ensure_instance_bound()

        # TODO: Replace with Zig pathfinder traversal
        # For now, return empty set as mock
        return set()

    @classmethod
    def LinkDirectShallow(cls):
        raise NotImplementedError("TODO: Zig core migration")

    @property
    def specializes(self):
        raise NotImplementedError("TODO: Zig core migration")

    @property
    def specialized(self):
        raise NotImplementedError("TODO: Zig core migration")

    @property
    def connected(self) -> "ModuleInterface":
        return self

    @Node._collection_only
    def connect(
        self: Self, *other: Self, link: type["Link"] | "Link" | None = None
    ) -> Self:
        if not other:
            return self

        link_type = self._normalize_link_type(link)

        for candidate in other:
            if not isinstance(candidate, ModuleInterface):
                raise TypeError(
                    f"Expected ModuleInterface, got {type(candidate).__name__}"
                )
            if candidate is self:
                continue
            self._connections.add(candidate)
            candidate._connections.add(self)
            self._record_link_type(candidate, link_type)
            candidate._record_link_type(self, link_type)

        return other[-1]

    def connect_via(
        self,
        bridge: Bridgable[Self] | Sequence[Bridgable[Self]],
        *other: Self,
        link=None,
    ):
        raise NotImplementedError("TODO: Zig core migration")

    def connect_shallow(self, *other: Self) -> Self:
        raise NotImplementedError("TODO: Zig core migration")

    @Node._runtime_only
    def get_connected(
        self,
        include_self: bool = False,
    ) -> dict[Self, object]:
        # TODO: Zig pathfinder for transitive connections
        # Currently returns direct connections only
        reachable = self._find_connected()
        if not include_self:
            reachable.discard(self)
        return {iface: None for iface in reachable}

    @Node._runtime_only
    def get_connected_nodes(
        self,
        include_self: bool = False,
    ) -> dict["ModuleInterface", object]:
        return self.get_connected(include_self=include_self)

    @Node._runtime_only
    def is_connected_to(self, other: "ModuleInterface") -> list[object]:
        # TODO: Implement path-based checking in Zig pathfinder module
        # Requires instance graph to query connections
        _ = other  # Unused until pathfinder is implemented

        # Ensure instance bound
        _ = self._ensure_instance_bound()

        # TODO: Replace with Zig pathfinder path checking
        # For now, return empty list (no paths found)
        return []

    @Node._collection_only
    def specialize[T: ModuleInterface](self, special: T) -> T:
        raise NotImplementedError("TODO: Zig core migration")

    @staticmethod
    def _path_with_least_conditionals(paths: list[object]) -> object:
        raise NotImplementedError("TODO: Zig core migration")

    def _connect_via_implied_paths(self, other: Self, paths: list[object]):
        raise NotImplementedError("TODO: Zig core migration")

    @staticmethod
    def _group_into_buses[T: ModuleInterface](mifs: Iterable[T]) -> dict[T, set[T]]:
        items = list(mifs)
        to_check = set(items)
        buses: dict[T, set[T]] = {}

        while to_check:
            interface = to_check.pop()
            reachable = interface._find_connected()
            buses[interface] = reachable
            to_check.difference_update(reachable)

        return buses

    # TODO get rid of this abomination
    @property
    def reference_shim(self):
        from faebryk.library.has_single_electric_reference import (
            has_single_electric_reference,
        )

        return self.get_trait(has_single_electric_reference).get_reference()
