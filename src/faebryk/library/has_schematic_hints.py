# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Callable, Self

from faebryk.libs.library import L


class _UnsetDefault:
    """Sentinel class for default value"""


def _hint[R, T: Callable[["has_schematic_hints"], R]](default: T) -> "property[R]":
    """A decorator for hint properties."""
    name = default.__name__

    def hint_getter(self: "has_schematic_hints") -> T:
        return self._hints.get(name, default(self))

    def hint_setter(self: "has_schematic_hints", value: T) -> None:
        self._hints[name] = value

    return property(hint_getter, hint_setter)


class has_schematic_hints(L.Module.TraitT.decless()):
    """
    Hints for the schematic exporter.
    """

    @_hint
    def lock_rotation_certainty(self) -> float:
        """The certainty we need to have before we lock a symbol's rotation."""
        return 0.6

    @_hint
    def symbol_rotation(self) -> int | None:
        """The rotation to apply to symbols."""
        return None

    def __init__(
        self,
        **hints,
    ):
        super().__init__()
        self._hints = hints

    def handle_duplicate(self, other: Self, node: L.Node) -> bool:
        assert other is not self

        _, narrowest_hint = other.cmp(self)

        if narrowest_hint is self:
            node.del_trait(other.__trait__)
            hints = other._hints
            hints.update(self._hints)
            self._hints = hints
            return True

        node.del_trait(self.__trait__)
        hints = self._hints
        hints.update(other._hints)
        other._hints = hints
        return False
