# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from abc import abstractmethod
from collections import defaultdict
from typing import Any, Callable, Generic, Iterable, Iterator, List, Type, TypeVar


class lazy:
    def __init__(self, expr):
        self.expr = expr

    def __str__(self):
        return str(self.expr())

    def __repr__(self):
        return repr(self.expr())


def kw2dict(**kw):
    return dict(kw)


class hashable_dict:
    def __init__(self, obj: dict):
        self.obj = obj

    def __hash__(self):
        return hash(sum(map(hash, self.obj.items())))

    def __repr__(self):
        return "{}({})".format(type(self), repr(self.obj))

    def __eq__(self, other):
        return hash(self) == hash(other)


def unique(it, key):
    seen = []
    out = []
    for i in it:
        v = key(i)
        if v in seen:
            continue
        seen.append(v)
        out.append(i)
    return out


def get_dict(obj, key, default):
    if key not in obj:
        obj[key] = default()

    return obj[key]


def flatten(obj: Iterable, depth=1) -> List:
    if depth == 0:
        return list(obj)
    if not isinstance(obj, Iterable):
        return [obj]
    return [nested for top in obj for nested in flatten(top, depth=depth - 1)]


T = TypeVar("T")
U = TypeVar("U")


def get_key(haystack: dict[T, U], needle: U) -> T:
    return find(haystack.items(), lambda x: x[1] == needle)[0]


def find(haystack: Iterable[T], needle: Callable) -> T:
    results = list(filter(needle, haystack))
    if len(results) != 1:
        raise ValueError
    return results[0]


def groupby(it: Iterable[T], key: Callable[[T], U]) -> dict[U, list[T]]:
    out = defaultdict(list)
    for i in it:
        out[key(i)].append(i)
    return out


def nested_enumerate(it: Iterable) -> list[tuple[list[int], Any]]:
    out: list[tuple[list[int], Any]] = []
    for i, obj in enumerate(it):
        if not isinstance(obj, Iterable):
            out.append(([i], obj))
            continue
        for j, _obj in nested_enumerate(obj):
            out.append(([i] + j, _obj))

    return out


class NotifiesOnPropertyChange(object):
    def __init__(self, callback) -> None:
        self._callback = callback

        # TODO dir -> vars?
        for name in dir(self):
            self._callback(name, getattr(self, name))

    def __setattr__(self, __name, __value) -> None:
        super().__setattr__(__name, __value)

        # before init
        if hasattr(self, "_callback"):
            self._callback(__name, __value)


T = TypeVar("T")
P = TypeVar("P")


class _wrapper(NotifiesOnPropertyChange, Generic[T, P]):
    @abstractmethod
    def __init__(self, parent: P) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> list[T]:
        raise NotImplementedError

    @abstractmethod
    def handle_add(self, name: str, obj: T):
        raise NotImplementedError

    @abstractmethod
    def get_parent(self) -> P:
        raise NotImplementedError


def Holder(_type: Type[T], _ptype: Type[P]) -> Type[_wrapper[T, P]]:
    _T = TypeVar("_T")
    _P = TypeVar("_P")

    class __wrapper(_wrapper[_T, _P]):
        def __init__(self, parent: P) -> None:
            self._list: list[T] = []
            self._type = _type
            self._parent: P = parent

            NotifiesOnPropertyChange.__init__(self, self._callback)

        def _callback(self, name: str, value: Any):
            if name.startswith("_"):
                return

            if callable(value):
                return

            if isinstance(value, self._type):
                self._list.append(value)
                self.handle_add(name, value)
                return

            if isinstance(value, Iterable):
                e_objs = nested_enumerate(value)
                objs = [x[1] for x in e_objs]
                assert all(map(lambda x: isinstance(x, self._type), objs))

                self._list += objs
                for i_list, instance in e_objs:
                    i_acc = "".join(f"[{i}]" for i in i_list)
                    self.handle_add(f"{name}{i_acc}", instance)
                return

            raise Exception("Invalid property added")

        def get_all(self) -> list[T]:
            # check for illegal list modifications
            for name in dir(self):
                value = getattr(self, name)
                if name.startswith("_"):
                    continue
                if callable(value):
                    continue
                if isinstance(value, self._type):
                    continue
                if isinstance(value, Iterable):
                    assert set(flatten(value, -1)).issubset(set(self._list))
                    continue

            return self._list

        def handle_add(self, name: str, obj: T) -> None:
            ...

        def get_parent(self) -> P:
            return self._parent

    return __wrapper[T, P]


def NotNone(x):
    assert x is not None
    return x


def consume_iterator(target, it: Iterator):
    while True:
        try:
            yield target(it)
        except StopIteration:
            return


T = TypeVar("T")


def cast_assert(t: type[T], obj) -> T:
    assert isinstance(obj, t)
    return obj


def times(cnt: int, lamb: Callable[[], T]) -> list[T]:
    return [lamb() for _ in range(cnt)]
