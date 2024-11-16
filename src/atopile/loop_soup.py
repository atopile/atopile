"""
A loop provides us a means to efficiently find connectedness between objects,
while only having access to a series of connections.
"""

import collections.abc
from typing import Callable, Hashable, Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")


class LoopItem(collections.abc.Iterable[T]):
    """
    Express a loop of objects, where each represents something and just points to the next
    """

    def __init__(self, represents: T):
        self.represents = represents
        self.prev = self
        self.next = self

    def iter_loop(self, limit: Optional[int] = None) -> Iterator["LoopItem[T]"]:
        """Iterate over the loop"""
        current = self
        count = 0
        yield current
        while current.next is not self:
            current = current.next
            count += 1
            if limit is not None and count >= limit:
                raise RuntimeError(f"Loop is too long, limit is {limit}")
            yield current

    def iter_values(self, limit: Optional[int] = None) -> Iterator[T]:
        """Iterate over the values in the loop"""
        for i in self.iter_loop(limit):
            yield i.represents

    def __iter__(self) -> Iterator[T]:
        yield from self.iter_values()

    def __repr__(self) -> str:
        if self.next is self:
            return f"<Loop {repr(self.represents)} -> {repr(self.represents)}>"
        return f"<Loop {repr(self.prev.represents)} -> {repr(self.represents)} -> {repr(self.next.represents)}>"

    @staticmethod
    def join(a: "LoopItem", b: "LoopItem") -> None:
        """Join loops together"""
        # if they're the same, do nothing
        if a is b:
            return

        # if they're both lonely, make them friends
        if a.next is a and b.next is b:
            assert a.prev is a
            assert b.prev is b
            a.next = b
            a.prev = b
            b.next = a
            b.prev = a

        # if one is lonely, make it friends with the other
        elif a.next is a:
            assert a.prev is a
            old_next = b.next
            b.next = a
            a.prev = b
            a.next = old_next
            old_next.prev = a
        elif b.next is b:
            assert b.prev is b
            old_next = a.next
            a.next = b
            b.prev = a
            b.next = old_next
            old_next.prev = b

        # if neither is lonely, check if they are already joined
        # If not, join them
        else:
            a_loop_items = list(a.iter_loop())
            if b not in a_loop_items:
                a_old_next = a.next
                b_old_prev = b.prev
                a.next = b
                b.prev = a
                b_old_prev.next = a_old_next
                a_old_next.prev = b_old_prev


def _simple_return(x: T) -> T:
    return x


class LoopSoup:
    """
    Helper function to associate data with the loop class
    """

    def __init__(self, key_func: Callable[[T], Hashable] = _simple_return):
        self.key_func = key_func
        self._map: dict[Hashable, LoopItem[T]] = {}

    def get_loop(self, thing: T) -> LoopItem[T]:
        """Get the loop for a thing"""
        return self._map[self.key_func(thing)]

    def add(self, thing: T) -> LoopItem[T]:
        """Add a thing to the loop pool"""
        key = self.key_func(thing)
        if key in self._map:
            raise KeyError(f"Key {key} for {repr(thing)} already occupied")
        loop_item = LoopItem(thing)
        self._map[key] = loop_item
        return loop_item

    def join(self, a: T, b: T) -> None:
        """Join two things together"""
        LoopItem.join(self.get_loop(a), self.get_loop(b))

    def join_multiple(self, things: Iterable[T]) -> None:
        """Join multiple things together"""
        things = list(things)
        if not things:
            return
        for b in things[1:]:
            self.join(things[0], b)

    def groups(self) -> Iterator[tuple[T]]:
        """Return an iterator of groups of things that are connected together"""
        seen = set()

        for k, v in self._map.items():
            if k in seen:
                continue

            # we can't do this bit lazily because we need to know
            # which values we would see if we went through the whole group
            values = tuple(v.iter_values())
            seen.update(self.key_func(i) for i in values)
            yield values

    def __len__(self) -> int:
        return len(self._map)

    def __bool__(self) -> bool:
        return bool(self._map)

    def __iter__(self) -> Iterator[T]:
        return iter(li.represents for li in self._map.values())

    def __contains__(self, item: T) -> bool:
        return self.key_func(item) in self._map
