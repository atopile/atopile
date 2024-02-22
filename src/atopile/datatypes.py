"""
Datatypes used in the model.
"""

import logging
from contextlib import contextmanager
from typing import (
    Callable,
    Generic,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Type,
    TypeVar,
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Ref(tuple[str]):
    """Shell class to provide basic utils for a reference."""

    def add_name(self, name: str | int) -> "Ref":
        """Return a new Ref with the given name."""
        return Ref((*self, name))

    def __str__(self) -> str:
        return ".".join(map(str, self))

    @classmethod
    def empty(cls) -> "Ref":
        """Return an empty Ref."""
        return cls(())

    @classmethod
    def from_one(cls, name: str | int) -> "Ref":
        """Return a Ref with a single item."""
        return cls((name,))


T = TypeVar("T")


class KeyOptItem(tuple[Optional[Ref], T], Generic[T]):
    """A class representing anf optionally-named thing."""

    @property
    def ref(self) -> Optional[Ref]:
        """Return the name of this item, if it has one."""
        return self[0]

    @property
    def value(self) -> T:
        """Return the value of this item."""
        return self[1]

    @classmethod
    def from_kv(cls, key: Optional[Ref], value: T) -> "KeyOptItem[T]":
        """Return a KeyOptItem with a single item."""
        return KeyOptItem((key, value))


class KeyOptMap(tuple[KeyOptItem[T]]):
    """A class representing a set of optionally-named things."""

    def named_items(self) -> Mapping[Ref, T]:
        """Return all the named items in this set, ignoring the unnamed ones."""
        return dict(filter(lambda x: x.ref is not None, self))

    def map_items_by_type(
        self, types: Iterable[Type | Iterable[Type]]
    ) -> Mapping[Type, "KeyOptMap[T]"]:
        """Return a mapping of items in this set by type."""
        return {t: tuple(self.filter_items_by_type(t)) for t in types}

    def unnamed_items(self) -> Iterable[T]:
        """Return an interable of all the unnamed items in this set."""
        return map(lambda x: x.value, filter(lambda x: x.ref is None, self))

    def filter_items_by_type(self, types: Type | Iterable[Type]) -> Iterator[T]:
        """Helper function to filter by type."""
        return filter(lambda x: isinstance(x.value, types), self)

    def keys(self) -> Iterable[Ref]:
        """Return an iterable of all the names in this set."""
        return map(lambda x: x.ref, filter(lambda x: x.ref is not None, self))

    def values(self) -> Iterable[T]:
        """Return an iterable of all the values in this set."""
        return map(lambda x: x.value, self)

    def strain(self) -> "Strainer[KeyOptItem[T]]":
        """Return a Strainer for this KeyOptMap."""
        return Strainer(self)

    @classmethod
    def from_item(cls, item: KeyOptItem[T]) -> "KeyOptMap[T]":
        """Return a KeyOptMap with a single item."""
        return KeyOptMap((item,))

    @classmethod
    def from_kv(cls, key: Optional[Ref], value: T) -> "KeyOptMap[T]":
        """Return a KeyOptMap with a single item."""
        return cls.from_item(KeyOptItem.from_kv(key, value))

    @classmethod
    def empty(cls) -> "KeyOptMap[T]":
        """Return an empty KeyOptMap."""
        return cls(())


class Strainer(list[T]):
    """A class to pop filtered things from a list."""

    def __init__(self, items: Iterable[T]) -> None:
        super().__init__(items)

    def iter_strain(self, filter_: Callable[[T], bool]) -> Iterator[T]:
        """Yield items that pass the filter, removing them from the list."""
        idx = 0
        while idx < len(self):
            item = self[idx]
            if filter_(item):
                yield self.pop(idx)
            else:
                idx += 1

    def strain(self, filter_: Callable[[T], bool]) -> list[T]:
        """Return a list of items that pass the filter, removing them from the list."""
        return list(self.iter_strain(filter_))


class StackList(list[T]):
    """Manages context while compiling ato code."""
    def __init__(self) -> None:
        super().__init__([])

    @contextmanager
    def enter(self, context: T) -> None:
        """Enter a context."""
        self.append(context)
        try:
            yield
        finally:
            self.pop()

    @property
    def top(self) -> T:
        """Return the current context."""
        return self[-1]


class DotDict(dict):
    """A dict you can dot"""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as ex:
            raise AttributeError(f"Attribute {name} not found", name) from ex
