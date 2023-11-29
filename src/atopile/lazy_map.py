"""
A mapping that lazily builds its values.
"""

import collections.abc
from typing import Callable, Hashable, Iterable, TypeVar, Mapping


K = TypeVar("K", bound=Hashable)  # the keys must be hashable
V = TypeVar("V")


class EMPTY_SENTINEL:  # pylint: disable=invalid-name,too-few-public-methods
    """A sentinel for the empty value."""

    def __repr__(self) -> str:
        return "EMPTY_SENTINEL"


class LazyMap(collections.abc.MutableMapping[K, V]):
    """A mapping that lazily builds its values."""

    def __init__(
        self,
        builder: Callable[[K], V],
        known_keys: Iterable[K],
        initial_values: Mapping[K, V],
    ) -> None:
        self.builder = builder
        self._map: dict[K, V] = {k: EMPTY_SENTINEL for k in known_keys}
        self._map.update(initial_values)

    def __getitem__(self, key: K):
        if self._map[key] is EMPTY_SENTINEL:
            self._map[key] = self.builder(key)

        return self._map[key]

    def __setitem__(self, key: K, value: V) -> None:
        self._map[key] = value

    def __delitem__(self, key: K) -> None:
        del self._map[key]

    def __iter__(self) -> Iterable:
        return iter(self._map)

    def __len__(self) -> int:
        return len(self._map)
