"""
Datatypes used in the model.
"""

import logging
from contextlib import contextmanager
from typing import Iterable

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Ref(tuple[str]):
    """Shell class to provide basic utils for a reference."""

    def add_name(self, name: str | int) -> "Ref":
        """Return a new Ref with the given name."""
        return Ref((*self, str(name)))

    def __str__(self) -> str:
        return ".".join(map(str, self))

    @classmethod
    def empty(cls) -> "Ref":
        """Return an empty Ref."""
        return cls(())

    @classmethod
    def from_one(cls, name: str | int) -> "Ref":
        """Return a Ref with a single item."""
        return cls((str(name),))


class KeyOptItem[V](tuple[Ref | None, V]):
    """A class representing anf optionally-named thing."""

    @property
    def ref(self) -> Ref | None:
        """Return the name of this item, if it has one."""
        return self[0]

    @property
    def value(self) -> V:
        """Return the value of this item."""
        return self[1]

    @classmethod
    def from_kv(cls, key: Ref | None, value: V) -> "KeyOptItem[V]":
        """Return a KeyOptItem with a single item."""
        return KeyOptItem((key, value))


class KeyOptMap[V](tuple[KeyOptItem[V]]):
    """A class representing a set of optionally-named things."""

    def keys(self) -> Iterable[Ref | None]:
        """Return an iterable of all the names in this set."""
        return map(lambda x: x.ref, filter(lambda x: x.ref is not None, self))

    def values(self) -> Iterable[V]:
        """Return an iterable of all the values in this set."""
        return map(lambda x: x.value, self)

    @classmethod
    def from_item(cls, item: KeyOptItem[V]) -> "KeyOptMap[V]":
        """Return a KeyOptMap with a single item."""
        return KeyOptMap((item,))

    @classmethod
    def from_kv(cls, key: Ref | None, value: V) -> "KeyOptMap[V]":
        """Return a KeyOptMap with a single item."""
        return cls.from_item(KeyOptItem.from_kv(key, value))

    @classmethod
    def empty(cls) -> "KeyOptMap[V]":
        """Return an empty KeyOptMap."""
        return cls(())


class StackList[V](list[V]):
    """Manages context while compiling ato code."""

    def __init__(self) -> None:
        super().__init__([])

    @contextmanager
    def enter(self, context: V):
        """Enter a context."""
        self.append(context)
        try:
            yield
        finally:
            self.pop()

    @property
    def top(self) -> V:
        """Return the current context."""
        return self[-1]
