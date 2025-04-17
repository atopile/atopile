"""
Datatypes used in the model.
"""

import logging
from contextlib import contextmanager
from typing import Iterable

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class TypeRef(tuple[str]):
    """Shell class to provide basic utils for a reference."""

    def add_name(self, name: str | int) -> "TypeRef":
        """Return a new Ref with the given name."""
        return TypeRef((*self, str(name)))

    def __str__(self) -> str:
        return ".".join(map(str, self))

    @classmethod
    def empty(cls) -> "TypeRef":
        """Return an empty Ref."""
        return cls(())

    @classmethod
    def from_one(cls, name: str | int) -> "TypeRef":
        """Return a Ref with a single item."""
        return cls((str(name),))

    @classmethod
    def from_path_str(cls, path: str) -> "TypeRef":
        """Return a Ref from a path string."""
        return cls(path.split("."))


KeyType = str | int
ReferencePartType = tuple[str, KeyType | None]


class FieldRef(tuple[ReferencePartType]):
    """
    A class representing a field reference.
    e.g app.modules[multiresistor].resistors[0].unnamed[1]
    """

    def __str__(self) -> str:
        return ".".join(
            f"{name}[{key}]" if key is not None else name for name, key in self
        )

    def to_type_ref(self) -> TypeRef | None:
        if any(key is not None for _, key in self):
            return None
        return TypeRef(map(lambda x: x[0], self))

    @classmethod
    def from_type_ref(cls, type_ref: TypeRef) -> "FieldRef":
        """Return a FieldRef from a TypeRef."""
        return cls(map(lambda x: (x, None), type_ref))


class KeyOptItem[V](tuple[TypeRef | None, V]):
    """A class representing anf optionally-named thing."""

    @property
    def ref(self) -> TypeRef | None:
        """Return the name of this item, if it has one."""
        return self[0]

    @property
    def value(self) -> V:
        """Return the value of this item."""
        return self[1]

    @classmethod
    def from_kv(cls, key: TypeRef | None, value: V) -> "KeyOptItem[V]":
        """Return a KeyOptItem with a single item."""
        return KeyOptItem((key, value))


class KeyOptMap[V](tuple[KeyOptItem[V]]):
    """A class representing a set of optionally-named things."""

    def keys(self) -> Iterable[TypeRef | None]:
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
    def from_kv(cls, key: TypeRef | None, value: V) -> "KeyOptMap[V]":
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
