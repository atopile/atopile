#%%

import collections.abc
from typing import TypeVar, Optional, Iterator, Callable

T = TypeVar("T")

class Loop(collections.abc.Iterable):  # TODO: is a pure iterable the best thing
    def __init__(
        self,
        represents: T
    ):
        self.represents = represents
        self.prev = None
        self.next = None

    def __next__(self) -> "Loop":
        if self.next is None:
            assert self.prev is None
            raise StopIteration
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
        if self.next is None:
            return f"<Loop {repr(self.represents)} -> {repr(self.represents)}>"
        return f"<Loop {repr(self.prev.represents)} -> {repr(self.represents)} -> {repr(self.next.represents)}>"

    @staticmethod
    def join(a: "Loop", b: "Loop") -> None:
        """TODO:"""
        if 
        a_old_next = a.next
        b_old_prev = b.prev

        if a_old_next is None:
            assert a.prev is None
            a_old_next = b

        if b_old_prev is None:
            assert b.next is None
            b_old_prev = a

        a.next = b
        b.prev = a

        a_old_next.prev = b_old_prev
        b_old_prev.next = a_old_next


# %%

a = Loop(1)
b = Loop(2)
Loop.join(a, b)

print(a)
print(b)
# %%

c = Loop(3)
d = Loop(4)
Loop.join(c, d)

print(c)
print(d)

# %%
Loop.join(c, b)
print(" -> ".join(str(i.represents) for i in  a))
# %%
