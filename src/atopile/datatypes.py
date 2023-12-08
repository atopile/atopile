"""
Datatypes used in the model.
"""
import logging
from typing import Generic, Iterable, Iterator, Mapping, Optional, Type, TypeVar

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
