import collections.abc
from typing import TypeVar, Optional, Iterator, Callable, Hashable

T = TypeVar("T")

class Loop(collections.abc.Iterable):  # TODO: is a pure iterable the best thing
    """
    Helper class to extract connected nets from a list of connections
    """
    def __init__(
        self,
        represents: T
    ):
        self.represents = represents
        self.prev = self
        self.next = self

    def __next__(self) -> "Loop":
        return self.next

    def __iter__(self) -> Iterator["Loop"]:
        def __loop_until_returned():
            current = self
            yield current
            while current.next is not self:
                current = next(current)
                yield current
        return __loop_until_returned()

    def __repr__(self) -> str:
        if self.next is self:
            return f"<Loop {repr(self.represents)} -> {repr(self.represents)}>"
        return f"<Loop {repr(self.prev.represents)} -> {repr(self.represents)} -> {repr(self.next.represents)}>"

    @staticmethod
    def join(a: "Loop", b: "Loop") -> None:
        """TODO:"""
        if a.next is a and b.next is b:
            assert a.prev is a
            assert b.prev is b
            a.next = b
            a.prev = b
            b.next = a
            b.prev = a
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
        else:
            a_old_next = a.next
            b_old_prev = b.prev
            a.next = b
            b.prev = a
            b_old_prev.next = a_old_next
            a_old_next.prev = b_old_prev


class LoopMap:
    """
    Helper function to associate data with the loop class
    """
    def __init__(self, key_func: Callable[[T], Hashable] = id):
        self.key_func = key_func
        self._map = {}

    def __getitem__(self, item: T) -> Loop:
        return self._map[self.key_func(item)]

    def add(self, thing: T) -> None:
        key = self.key_func(thing)
        if key in self._map:
            raise KeyError(f"Key {key} for {repr(thing)} already occupied")
        self._map[key] = Loop(thing)

    def join(self, a: T, b: T) -> None:
        Loop.join(self[a], self[b])

    def groups(self) -> Iterator[Iterator[T]]:
        seen = set()

        def __mark_as_seen(loop: Loop[T]) -> Iterator[T]:
            for i in loop:
                seen.add(self.key_func(i.represents))
                yield i.represents

        for k, v in self._map.items():
            if k in seen:
                continue
            yield __mark_as_seen(v)

