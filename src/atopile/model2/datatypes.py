"""
Datatypes used in the model.
"""
import logging
from typing import Any, Iterable, Mapping, Optional, Type


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Ref(tuple[str | int]):
    """Shell class to provide basic utils for a reference."""

    @classmethod
    def from_one(cls, name: str | int) -> "Ref":
        """Return a Ref with a single item."""
        return cls((name,))


class KeyOptItem(tuple[Optional[Ref], Any]):
    """A class representing anf optionally-named thing."""

    @property
    def ref(self) -> Optional[Ref]:
        """Return the name of this item, if it has one."""
        return self[0]

    @property
    def value(self) -> Any:
        """Return the value of this item."""
        return self[1]

    @classmethod
    def from_kv(cls, key: Optional[Ref], value: Any) -> "KeyOptItem":
        """Return a KeyOptItem with a single item."""
        return KeyOptItem((key, value))


class KeyOptMap(tuple[KeyOptItem]):
    """A class representing a set of optionally-named things."""

    def get_named_items(self) -> Mapping[Ref, Any]:
        """Return all the named items in this set, ignoring the unnamed ones."""
        return dict(filter(lambda x: x.ref is not None, self))

    def get_items_by_type(
        self, types: Iterable[Type]
    ) -> Mapping[Type, "KeyOptMap"]:
        """Return a mapping of items in this set by type."""
        return {
            t: filter(lambda x: isinstance(x.value, t), self) for t in types
        }

    def get_unnamed_items(self) -> Iterable[Any]:
        """Return an interable of all the unnamed items in this set."""
        return map(lambda x: x.value, filter(lambda x: x.ref is None, self))

    def keys(self) -> Iterable[Ref]:
        """Return an iterable of all the names in this set."""
        return map(lambda x: x.ref, filter(lambda x: x.ref is not None, self))

    def values(self) -> Iterable[Any]:
        """Return an iterable of all the values in this set."""
        return map(lambda x: x.value, self)

    @classmethod
    def from_item(cls, item: KeyOptItem) -> "KeyOptMap":
        """Return a KeyOptMap with a single item."""
        return KeyOptMap((item,))

    @classmethod
    def from_kv(cls, key: Optional[Ref], value: Any) -> "KeyOptMap":
        """Return a KeyOptMap with a single item."""
        return cls.from_item(KeyOptItem.from_kv(key, value))
