# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import collections.abc
import hashlib
import importlib.util
import inspect
import itertools
import json
import logging
import os
import select
import shutil
import stat
import subprocess
import sys
import time
import uuid
from abc import abstractmethod
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, fields
from enum import Enum, StrEnum
from functools import wraps
from genericpath import commonprefix
from importlib.metadata import Distribution
from itertools import chain, pairwise
from json import JSONEncoder
from pathlib import Path
from textwrap import indent
from types import ModuleType
from typing import (
    Any,
    Callable,
    Concatenate,
    Container,
    Generator,
    Hashable,
    Iterable,
    Iterator,
    List,
    Optional,
    Protocol,
    Self,
    Sequence,
    SupportsFloat,
    SupportsInt,
    Type,
    TypeGuard,
    cast,
    get_origin,
    get_type_hints,
    overload,
    override,
)

import psutil

logger = logging.getLogger(__name__)


class Serializable(Protocol):
    def serialize(self) -> dict: ...

    @classmethod
    def deserialize(cls, data: dict) -> Self: ...


class SerializableJSONEncoder(JSONEncoder):
    def default(self, o: Serializable | None):
        return None if o is None else o.serialize()


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


def unique[T, U](it: Iterable[T], key: Callable[[T], U]) -> list[T]:
    seen: list[U] = []
    out: list[T] = []
    for i in it:
        v = key(i)
        if v in seen:
            continue
        seen.append(v)
        out.append(i)
    return out


def unique_ref[T](it: Iterable[T]) -> list[T]:
    return unique(it, id)


def duplicates(it, key):
    return {k: v for k, v in groupby(it, key).items() if len(v) > 1}


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


def get_key[T, U](haystack: dict[T, U], needle: U) -> T:
    return find(haystack.items(), lambda x: x[1] == needle)[0]


class KeyErrorNotFound(KeyError): ...


class KeyErrorAmbiguous[T](KeyError):
    def __init__(self, duplicates: list[T], *args: object) -> None:
        super().__init__(*args)
        self.duplicates = duplicates

    def __str__(self):
        return f"KeyErrorAmbiguous: {self.duplicates}"


def find[T](haystack: Iterable[T], needle: Callable[[T], Any] | None = None) -> T:
    if needle is None:
        needle = lambda x: x is not None  # noqa: E731
    results = [x for x in haystack if needle(x)]
    if not results:
        raise KeyErrorNotFound()
    if len(results) != 1:
        raise KeyErrorAmbiguous(results)
    return results[0]


def find_or[T](
    haystack: Iterable[T],
    needle: Callable[[T], bool],
    default: T,
    default_multi: Callable[[list[T]], T] | None = None,
) -> T:
    try:
        return find(haystack, needle)
    except KeyErrorNotFound:
        return default
    except KeyErrorAmbiguous as e:
        if default_multi is not None:
            return default_multi(e.duplicates)
        raise


def groupby[T, U](it: Iterable[T], key: Callable[[T], U]) -> dict[U, list[T]]:
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


class _wrapper[T, P](NotifiesOnPropertyChange):
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

    @abstractmethod
    def extend_list(self, list_name: str, *objs: T) -> None:
        raise NotImplementedError


def Holder[T, P](_type: Type[T], _ptype: Type[P]) -> Type[_wrapper[T, P]]:
    class __wrapper[_T, _P](_wrapper[_T, _P]):
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

            if isinstance(value, dict):
                value = value.values()

            if isinstance(value, Iterable):
                e_objs = nested_enumerate(value)
                objs = [x[1] for x in e_objs]
                assert all(map(lambda x: isinstance(x, self._type), objs))

                self._list += objs
                for i_list, instance in e_objs:
                    i_acc = "".join(f"[{i}]" for i in i_list)
                    self.handle_add(f"{name}{i_acc}", instance)
                return

            raise Exception(
                f"Invalid property added for {name=} {value=} of type {type(value)},"
                + f"expected {_type} or iterable thereof"
            )

        def extend_list(self, list_name: str, *objs: T) -> None:
            if not hasattr(self, list_name):
                setattr(self, list_name, [])
            for obj in objs:
                # emulate property setter
                list_obj = getattr(self, list_name)
                idx = len(list_obj)
                list_obj.append(obj)
                self._list.append(obj)
                self.handle_add(f"{list_name}[{idx}]", obj)

        def get_all(self) -> list[T]:
            # check for illegal list modifications
            for name in sorted(dir(self)):
                value = getattr(self, name)
                if name.startswith("_"):
                    continue
                if callable(value):
                    continue
                if isinstance(value, self._type):
                    continue
                if isinstance(value, dict):
                    value = value.values()
                if isinstance(value, Iterable):
                    assert set(flatten(value, -1)).issubset(set(self._list))
                    continue

            return self._list

        def handle_add(self, name: str, obj: T) -> None: ...

        def get_parent(self) -> P:
            return self._parent

        def repr(self):
            return f"{type(self).__name__}({self._list})"

    return __wrapper[T, P]


def not_none(x):
    assert x is not None
    return x


@overload
def cast_assert[T](t: type[T], obj) -> T: ...


@overload
def cast_assert[T1, T2](t: tuple[type[T1], type[T2]], obj) -> T1 | T2: ...


@overload
def cast_assert[T1, T2, T3](
    t: tuple[type[T1], type[T2], type[T3]], obj
) -> T1 | T2 | T3: ...


@overload
def cast_assert[T1, T2, T3, T4](
    t: tuple[type[T1], type[T2], type[T3], type[T4]], obj
) -> T1 | T2 | T3 | T4: ...


def cast_assert(t, obj):
    """
    Assert that obj is an instance of type t and return it with proper type hints.
    t can be either a single type or a tuple of types.
    """
    assert isinstance(obj, t)
    return obj


def times[T](cnt: SupportsInt, lamb: Callable[[], T]) -> list[T]:
    return [lamb() for _ in range(int(cnt))]


@staticmethod
def is_type_pair[T, U](
    param1: Any, param2: Any, type1: type[T], type2: type[U]
) -> Optional[tuple[T, U]]:
    o1 = get_origin(type1) or type1
    o2 = get_origin(type2) or type2
    if isinstance(param1, o1) and isinstance(param2, o2):
        return param1, param2
    if isinstance(param2, o1) and isinstance(param1, o2):
        return param2, param1
    return None


def is_type_set_subclasses(type_subclasses: set[type], types: set[type]) -> bool:
    hits = {t: any(issubclass(s, t) for s in type_subclasses) for t in types}
    return all(hits.values()) and all(
        any(issubclass(s, t) for t in types) for s in type_subclasses
    )


def round_str(value: SupportsFloat, n=8):
    """
    Round a float to n decimals and strip trailing zeros.
    """
    f = round(float(value), n)
    return str(f).rstrip("0").rstrip(".")


def _print_stack(stack) -> Iterable[str]:
    from rich.text import Text

    for frame_info in stack:
        frame = frame_info[0]
        if "venv" in frame_info.filename:
            continue
        if "faebryk" not in frame_info.filename:
            continue
        # if frame_info.function not in ["_connect_across_hierarchies"]:
        #    continue
        yield str(
            Text.assemble(
                (
                    f" Frame in {frame_info.filename} at line {frame_info.lineno}:",
                    "red",
                ),
                (f" {frame_info.function} ", "blue"),
            )
        )

        def pretty_val(value):
            if isinstance(value, dict):
                import pprint

                formatted = pprint.pformat(
                    {pretty_val(k): pretty_val(v) for k, v in value.items()},
                    indent=2,
                    width=120,
                )
                return ("\n" if len(value) > 1 else "") + indent(
                    str(Text(formatted)), " " * 4
                )
            elif isinstance(value, type):
                return f"<class {value.__name__}>"
            return str(value)

        for name, value in frame.f_locals.items():
            yield str(
                Text.assemble(
                    ("  ", ""),
                    (f"{name}", "green"),
                    (" = ", ""),
                    (pretty_val(value), ""),
                )
            )


def print_stack(stack):
    return "\n".join(_print_stack(stack))


# Get deepest values in nested dict:
def flatten_dict(d: dict):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from flatten_dict(v)
        else:
            yield (k, v)


def split_recursive_stack(
    stack: Iterable[inspect.FrameInfo],
) -> tuple[list[inspect.FrameInfo], int, list[inspect.FrameInfo]]:
    """
    Handles RecursionError by splitting the stack into three parts:
    - recursion: the repeating part of the stack indicating the recursion.
    - stack_towards_recursion: the part of the stack after the recursion
        has been detected.

    :param stack: The stack obtained from inspect.stack()
    :return: tuple (recursion, recursion_depth, stack_towards_recursion)
    """

    def find_loop_len(sequence):
        for loop_len in range(1, len(sequence) // 2 + 1):
            if len(sequence) % loop_len:
                continue
            is_loop = True
            for i in range(0, len(sequence), loop_len):
                if sequence[i : i + loop_len] != sequence[:loop_len]:
                    is_loop = False
                    break
            if is_loop:
                return loop_len

        return 0

    def find_last_longest_most_frequent_looping_sequence_in_beginning(stack):
        stack = list(stack)

        loops = []

        # iterate over all possible beginnings
        for i in range(len(stack)):
            # iterate over all possible endings
            # try to maximize length of looping sequence
            for j in reversed(range(i + 1, len(stack) + 1)):
                # determine length of loop within this range
                loop_len = find_loop_len(stack[i:j])
                if loop_len:
                    # check if skipped beginning is partial loop
                    if stack[:i] != stack[j - i : j]:
                        continue
                    loops.append((i, j, loop_len))
                    continue

        # print(loops)
        max_loop = max(loops, key=lambda x: (x[1] - x[0], x[1]), default=None)
        return max_loop

    stack = list(stack)

    # Get the full stack representation as a list of strings
    full_stack = [f"{frame.filename}:{frame.positions}" for frame in stack]

    max_loop = find_last_longest_most_frequent_looping_sequence_in_beginning(full_stack)
    assert max_loop
    i, j, depth = max_loop

    return stack[i : i + depth], depth, stack[j:]


CACHED_RECUSION_ERRORS = set()


# TODO: now unused
# Consider splitting into three functions
# - A "lower_recursion_limit" contextmanager, should increase limit from current usage
# - A "better_recursion_error" function, should improve recursion error messaging
# - A separate composable "except" decorator which can be used to more generically
#   return something in case of a function raising an error
def try_avoid_endless_recursion(f: Callable[..., str]):
    import sys

    def _f_no_rec(*args, **kwargs):
        limit = sys.getrecursionlimit()
        target = 100
        sys.setrecursionlimit(target)
        try:
            return f(*args, **kwargs)
        except RecursionError:
            sys.setrecursionlimit(target + 1000)

            rec, depth, non_rec = split_recursive_stack(inspect.stack()[1:])
            recursion_error_str = indent(
                "\n".join(
                    [
                        f"{frame.filename}:{frame.lineno} {frame.code_context}"
                        for frame in rec
                    ]
                    + [f"... repeats {depth} times ..."]
                    + [
                        f"{frame.filename}:{frame.lineno} {frame.code_context}"
                        for frame in non_rec
                    ]
                ),
                "   ",
            )

            if recursion_error_str in CACHED_RECUSION_ERRORS:
                logger.error(
                    f"Recursion error: {f.__name__} {f.__code__.co_filename}:"
                    + f"{f.__code__.co_firstlineno}: DUPLICATE"
                )
            else:
                CACHED_RECUSION_ERRORS.add(recursion_error_str)
                logger.error(
                    f"Recursion error: {f.__name__} {f.__code__.co_filename}:"
                    + f"{f.__code__.co_firstlineno}"
                )
                logger.error(recursion_error_str)

            return "<RECURSION ERROR WHILE CONVERTING TO STR>"
        finally:
            sys.setrecursionlimit(limit)

    return _f_no_rec


def zip_non_locked[T, U](left: Iterable[T], right: Iterable[U]):
    # Theoretically supports any amount of iters,
    #  but for type hinting limit to two for now

    class _Iter[TS, US](Iterator[tuple[TS, US]]):
        class _NONDEFAULT: ...

        def __init__(self, args: list[Iterable]):
            self.iters = [iter(arg) for arg in args]
            self.stopped = False
            self.stepped = False
            self.values = [None for _ in self.iters]

        def next(self, i: int, default: Any = _NONDEFAULT):
            try:
                self.advance(i)
                return self.values[i]
            except StopIteration as e:
                self.stopped = True
                if default is not self._NONDEFAULT:
                    return default
                raise e

        def advance(self, i: int):
            self.values[i] = next(self.iters[i])
            self.stepped = True

        def advance_all(self):
            self.stepped = True
            try:
                self.values = [next(iter) for iter in self.iters]
            except StopIteration:
                self.stopped = True

        def __next__(self):
            if not self.stepped:
                self.advance_all()
            if self.stopped:
                raise StopIteration()
            self.stepped = False

            return tuple(self.values)

    return _Iter[T, U]([left, right])


def try_or[T](
    func: Callable[..., T],
    default: T | None = None,
    default_f: Callable[[Exception], T] | None = None,
    catch: type[Exception] | tuple[type[Exception], ...] = Exception,
) -> T:
    try:
        return func()
    except catch as e:
        if default_f is not None:
            default = default_f(e)
        return default


class SharedReference[T]:
    @dataclass
    class Resolution[U, S]:
        representative: S
        object: U
        old: U

    def __init__(self, object: T):
        self.object: T = object
        self.links: set[Self] = set([self])

    def link(self, other: Self):
        assert type(self) is type(other), f"{type(self)=} {type(other)=}"
        if self == other:
            return

        lhs, rhs = self, other
        old = rhs.object

        r_links = rhs.links
        for rhs_ in r_links:
            rhs_.object = lhs.object
            rhs_.links = lhs.links

        lhs.links.update(r_links)

        return self.Resolution(lhs, lhs.object, old)

    def set(self, obj: T):
        self.object = obj
        for link in self.links:
            link.object = obj

    def __call__(self) -> T:
        return self.object

    def __eq__(self, other: "SharedReference[T]"):
        return self.object is other.object and self.links is other.links

    def __hash__(self) -> int:
        return hash(id(self))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.object})"


def bfs_visit[T](
    neighbours: Callable[[list[T]], list[T]], roots: Iterable[T]
) -> set[T]:
    """
    Generic BFS (not depending on Graph)
    Returns all visited nodes.
    """
    open_path_queue: list[list[T]] = [[root] for root in roots]
    visited: set[T] = set(roots)

    while open_path_queue:
        open_path = open_path_queue.pop(0)

        for neighbour in neighbours(open_path):
            if neighbour not in visited:
                new_path = open_path + [neighbour]
                visited.add(neighbour)
                open_path_queue.append(new_path)

    return visited


class TwistArgs:
    def __init__(self, op: Callable) -> None:
        self.op = op

    def __call__(self, *args, **kwargs):
        return self.op(*reversed(args), **kwargs)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.op})"


class CallOnce[F: Callable]:
    def __init__(self, f: F) -> None:
        self.f = f
        self.called = False

    # TODO types
    def __call__(self, *args, **kwargs) -> Any:
        if self.called:
            return
        self.called = True
        return self.f(*args, **kwargs)


def at_exit(func: Callable, on_exception: bool = True):
    import atexit
    import sys

    f = CallOnce(func)

    atexit.register(f)
    hook = sys.excepthook
    if on_exception:
        sys.excepthook = lambda *args: (f(), hook(*args))

    # get main thread
    import threading

    mainthread = threading.main_thread()

    def wait_main():
        mainthread.join()
        f()

    threading.Thread(target=wait_main).start()

    return f


def lazy_construct(cls):
    """
    Careful: break deepcopy
    """
    old_init = cls.__init__

    def new_init(self, *args, **kwargs):
        self._init = False
        self._old_init = lambda: old_init(self, *args, **kwargs)

    def __getattr__(self, name: str, /):
        assert "_init" in self.__dict__
        if self._init:
            raise AttributeError(name)
        self._old_init()
        self._init = True
        return self.__getattribute__(name)

    cls.__init__ = new_init
    cls.__getattr__ = __getattr__
    return cls


# TODO figure out nicer way (with metaclass or decorator)
class LazyMixin:
    @property
    def is_init(self):
        return self.__dict__.get("_init", False)

    def force_init(self):
        if self.is_init:
            return
        self._old_init()
        self._init = True


class Lazy(LazyMixin):
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        lazy_construct(cls)


def once[T, **P](f: Callable[P, T]) -> Callable[P, T]:
    # TODO add flag for this optimization
    # might not be desirable if different instances with same hash
    # return same values here
    # check if f is a method with only self
    if list(inspect.signature(f).parameters) == ["self"]:
        name = f.__name__
        attr_name = f"_{name}_once"

        def wrapper_single(self) -> Any:
            if not hasattr(self, attr_name):
                setattr(self, attr_name, f(self))
            return getattr(self, attr_name)

        return wrapper_single

    # TODO optimization: if takes self + args, use self as cache

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        lookup = (args, tuple(kwargs.items()))
        if lookup in wrapper.cache:
            return wrapper.cache[lookup]

        result = f(*args, **kwargs)
        wrapper.cache[lookup] = result
        return result

    wrapper.cache = {}
    wrapper._is_once_wrapper = True
    return wrapper


def assert_once[T, O, **P](
    f: Callable[Concatenate[O, P], T],
) -> Callable[Concatenate[O, P], T]:
    def wrapper(obj: O, *args: P.args, **kwargs: P.kwargs) -> T:
        if not hasattr(obj, "_assert_once_called"):
            setattr(obj, "_assert_once_called", set())

        wrapper_set = getattr(obj, "_assert_once_called")

        if wrapper not in wrapper_set:
            wrapper_set.add(wrapper)
            return f(obj, *args, **kwargs)
        else:
            raise AssertionError(f"{f.__name__} called on {obj} more than once")

    return wrapper


def assert_once_global[T, **P](f: Callable[P, T]) -> Callable[P, T]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        if not wrapper.called:
            wrapper.called = True
            return f(*args, **kwargs)
        else:
            raise AssertionError("Function called more than once")

    wrapper.called = False
    return wrapper


class _ConfigFlagBase[T]:
    def __init__(self, name: str, default: T, descr: str = ""):
        self._name = name
        self.default = default
        self.descr = descr
        self._type: type[T] = type(default)
        self.get()

    @property
    def name(self) -> str:
        return f"FBRK_{self._name}"

    @property
    def raw_value(self) -> str | None:
        return os.getenv(self.name, None)

    @once
    def get(self) -> T:
        raw_val = self.raw_value

        if raw_val is None:
            res = self.default
        else:
            res = self._convert(raw_val)

        if res != self.default:
            logger.warning(f"Config flag |{self.name}={res}|")

        return res

    def __hash__(self) -> int:
        return hash(self.name)

    @abstractmethod
    def _convert(self, raw_val: str) -> T: ...

    def __eq__(self, other) -> bool:
        # catch cache lookup
        if isinstance(other, _ConfigFlagBase):
            return id(other) == id(self)

        return self.get() == other


class ConfigFlag(_ConfigFlagBase[bool]):
    def __init__(self, name: str, default: bool = False, descr: str = "") -> None:
        super().__init__(name, default, descr)

    def _convert(self, raw_val: str) -> bool:
        matches = [
            (True, ["1", "true", "yes", "y"]),
            (False, ["0", "false", "no", "n"]),
        ]
        val = raw_val.lower()

        return find(matches, lambda x: val in x[1])[0]

    def __bool__(self):
        return self.get()


class ConfigFlagEnum[E: StrEnum](_ConfigFlagBase[E]):
    def __init__(self, enum: type[E], name: str, default: E, descr: str = "") -> None:
        self.enum = enum
        super().__init__(name, default, descr)

    def _convert(self, raw_val: str) -> E:
        return self.enum[raw_val.upper()]


class ConfigFlagString(_ConfigFlagBase[str]):
    def __init__(self, name: str, default: str = "", descr: str = "") -> None:
        super().__init__(name, default, descr)

    def _convert(self, raw_val: str) -> str:
        return raw_val


class ConfigFlagInt(_ConfigFlagBase[int]):
    def __init__(self, name: str, default: int = 0, descr: str = "") -> None:
        super().__init__(name, default, descr)

    def _convert(self, raw_val: str) -> int:
        if raw_val.startswith("0x"):
            return int(raw_val, 16)
        return int(float(raw_val))

    def __int__(self) -> int:
        return self.get()


def zip_dicts_by_key(*dicts):
    keys = {k for d in dicts for k in d}
    return {k: tuple(d.get(k) for d in dicts) for k in keys}


def factory[T, **P](con: Callable[P, T]) -> Callable[P, Callable[[], T]]:
    def _(*args: P.args, **kwargs: P.kwargs) -> Callable[[], T]:
        def __() -> T:
            return con(*args, **kwargs)

        return __

    return _


class PostInitCaller(type):
    def __call__(cls, *args, **kwargs):
        obj = type.__call__(cls, *args, **kwargs)
        obj.__post_init__(*args, **kwargs)
        return obj


def post_init_decorator(cls):
    """
    Class decorator that calls __post_init__ after the last (of derived classes)
    __init__ has been called.
    Attention: Needs to be called on cls in __init_subclass__ of decorated class.
    """
    post_init_base = getattr(cls, "__post_init_decorator", None)
    # already decorated
    if post_init_base is cls:
        return

    original_init = cls.__init__

    # inherited constructor
    if post_init_base and post_init_base.__init__ == cls.__init__:
        original_init = post_init_base.__original_init__

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if hasattr(self, "__post_init__") and type(self) is cls:
            self.__post_init__(*args, **kwargs)

    cls.__init__ = new_init
    cls.__original_init__ = original_init
    cls.__post_init_decorator = cls
    return cls


class Tree[T](dict[T, "Tree[T]"]):
    def iter_by_depth(self) -> Iterable[Sequence[T]]:
        yield list(self.keys())

        for level in zip_exhaust(*[v.iter_by_depth() for v in self.values()]):
            # merge lists of parallel subtrees
            yield [n for subtree in level for n in subtree]

    def pretty(self) -> str:
        # TODO this is def broken for actual trees

        out = ""
        next_levels = [self]
        while next_levels:
            for next_level in next_levels:
                out += " | ".join(f"{p!r}" for p in next_level.keys())
            next_levels = [
                children
                for next_level in next_levels
                for _, children in next_level.items()
            ]
            if any(next_levels):
                out += indent("\n↓\n", " " * 12)

        return out

    def copy(self) -> "Tree[T]":
        return Tree({k: v.copy() for k, v in self.items()})

    def flat(self) -> set[T]:
        return {n for level in self.iter_by_depth() for n in level}

    def leaves(self) -> Generator[T, None, None]:
        for child, child_tree in self.items():
            if not child_tree:
                yield child
            else:
                yield from child_tree.leaves()

    def get_subtree(self, node: T) -> "Tree[T]":
        """
        If not acyclic, will return the highest subtree containing the node.
        """
        trees = [self]
        while trees:
            tree = find_or(
                trees,
                lambda t: node in not_none(t),
                default=None,
                default_multi=lambda x: x[0],
            )
            if tree is not None:
                return tree[node]

            trees = [child for tree in trees for child in tree.values()]

        raise KeyErrorNotFound(f"Node {node} not found in tree")


# zip iterators, but if one iterators stops producing, the rest continue
def zip_exhaust(*args):
    while True:
        out = [next(a, None) for a in args]
        out = [a for a in out if a]
        if not out:
            return

        yield out


def join_if_non_empty(sep: str, *args):
    return sep.join(s for arg in args if (s := str(arg)))


def dataclass_as_kwargs(obj: Any) -> dict[str, Any]:
    return {f.name: getattr(obj, f.name) for f in fields(obj)}


class RecursionGuard:
    def __init__(self, limit: int = 10000):
        self.limit = limit

    # TODO remove this workaround when we have lazy mifs
    def __enter__(self):
        self.recursion_depth = sys.getrecursionlimit()
        sys.setrecursionlimit(self.limit)

    def __exit__(self, exc_type, exc_value, traceback):
        sys.setrecursionlimit(self.recursion_depth)


def in_debug_session() -> bool:
    """
    Check if a debugger is connected.
    """
    # short-cut so we don't end up with a bunch of useless warnings
    # when just checking for debugpy in the import statement
    if "debugpy" not in sys.modules:
        return False

    try:
        import debugpy

        return debugpy.is_client_connected()

    except (ImportError, ModuleNotFoundError):
        pass

    return False


class FuncSet[T, H: Hashable = int](collections.abc.MutableSet[T]):
    """
    A set by pre-processing the objects with the hasher function.
    """

    def __init__(self, data: Iterable[T] = tuple(), hasher: Callable[[T], H] = id):
        self._hasher = hasher
        self._deref: defaultdict[H, list[T]] = defaultdict(list)

        for item in data:
            self._deref[self._hasher(item)].append(item)

    def add(self, item: T):
        if item not in self._deref[self._hasher(item)]:
            self._deref[self._hasher(item)].append(item)

    def discard(self, item: T):
        hashed = self._hasher(item)
        if hashed in self._deref and item in self._deref[hashed]:
            self._deref[hashed].remove(item)
            if not self._deref[hashed]:
                del self._deref[hashed]

    def __contains__(self, item: T):
        return item in self._deref[self._hasher(item)]

    def __iter__(self) -> Iterator[T]:
        yield from chain.from_iterable(self._deref.values())

    def __len__(self) -> int:
        return sum(len(v) for v in self._deref.values())

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"({repr(list(self))}, hasher={repr(self._hasher)})"
        )


class FuncDict[T, U, H: Hashable = int](collections.abc.MutableMapping[T, U]):
    """
    A dict by pre-processing the objects with the hasher function.
    """

    def __init__(
        self,
        data: Iterable[tuple[T, U]] = tuple(),
        hasher: Callable[[T], H] = id,
    ):
        self._hasher = hasher
        self._keys: defaultdict[H, list[T]] = defaultdict(list)
        self._values: defaultdict[H, list[U]] = defaultdict(list)

        for key, value in data:
            hashed_key = self._hasher(key)
            self._keys[hashed_key].append(key)
            self._values[hashed_key].append(value)

    def __contains__(self, item: object):
        try:
            hashed = self._hasher(item)  # type: ignore
        except TypeError:
            return False
        return item in self._keys[hashed]

    def keys(self) -> Iterator[T]:
        yield from chain.from_iterable(self._keys.values())

    def values(self) -> Iterator[U]:
        yield from chain.from_iterable(self._values.values())

    def __iter__(self) -> Iterator[T]:
        yield from self.keys()

    def __len__(self) -> int:
        return sum(len(v) for v in self._values.values())

    def __getitem__(self, key: T) -> U:
        hashed = self._hasher(key)
        for test_key, value in zip(self._keys[hashed], self._values[hashed]):
            if test_key == key:
                return value
        raise KeyError(key)

    def __setitem__(self, key: T, value: U):
        hashed_key = self._hasher(key)
        try:
            idx = self._keys[hashed_key].index(key)
        except ValueError:
            self._keys[hashed_key].append(key)
            self._values[hashed_key].append(value)
        else:
            self._values[hashed_key][idx] = value
            self._keys[hashed_key][idx] = key

    def __delitem__(self, key: T):
        hashed_key = self._hasher(key)
        try:
            idx = self._keys[hashed_key].index(key)
        except ValueError:
            raise KeyError(key)
        else:
            del self._values[hashed_key][idx]
            del self._keys[hashed_key][idx]

    def items(self) -> Iterable[tuple[T, U]]:
        """Iter key-value pairs as items, just like a dict."""
        yield from zip(self.keys(), self.values())

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"({repr(list(self.items()))}, hasher={repr(self._hasher)})"
        )

    def backwards_lookup(self, item: U) -> T:
        """Find the first value that maps to item, and return its key."""
        for key, value in self.items():
            if value == item:
                return key
        raise KeyError(item)

    def setdefault(self, key: T, default: U) -> U:
        """Set default if key is not in the dict, and return the value."""
        try:
            return self[key]
        except KeyError:
            self[key] = default
        return default

    def backwards(self) -> "FuncDict[U, T, H]":
        return FuncDict(((v, k) for k, v in self.items()), hasher=self._hasher)


def dict_map_values(d: dict, function: Callable[[Any], Any]) -> dict:
    """recursively map all values in a dict"""

    result = {}
    for key, value in d.items():
        if isinstance(value, dict):
            result[key] = dict_map_values(value, function)
        elif isinstance(value, list):
            result[key] = [dict_map_values(v, function) for v in value]
        else:
            result[key] = function(value)
    return result


def merge_dicts(*dicts: dict) -> dict:
    """merge a list of dicts into a single dict,
    if same key is present and value is list, lists are merged
    if same key is dict, dicts are merged recursively
    """
    result = {}
    for d in dicts:
        for k, v in d.items():
            if k in result:
                if isinstance(v, list):
                    assert isinstance(
                        result[k], list
                    ), f"Trying to merge list into key '{k}' of type {type(result[k])}"
                    result[k] += v
                elif isinstance(v, dict):
                    assert isinstance(result[k], dict)
                    result[k] = merge_dicts(result[k], v)
                else:
                    result[k] = v
            else:
                result[k] = v
    return result


def abstract[T: type](cls: T) -> T:
    """
    Mark a class as abstract.
    """

    old_new = cls.__new__

    def _new(cls_, *args, **kwargs):
        if cls_ is cls:
            raise TypeError(f"{cls.__name__} is abstract and cannot be instantiated")
        return old_new(cls_, *args, **kwargs)

    cls.__new__ = _new
    return cls


def typename(x: object | type) -> str:
    if not isinstance(x, type):
        x = type(x)
    return x.__name__


def dict_value_visitor(d: dict, visitor: Callable[[Any, Any], Any]):
    for k, v in list(d.items()):
        if isinstance(v, dict):
            dict_value_visitor(v, visitor)
        else:
            d[k] = visitor(k, v)


class DefaultFactoryDict[T, U](dict[T, U]):
    def __init__(self, factory: Callable[[T], U], *args, **kwargs):
        self.factory = factory
        super().__init__(*args, **kwargs)

    def __missing__(self, key: T) -> U:
        res = self.factory(key)
        self[key] = res
        return res


class EquivalenceClasses[T: Hashable]:
    def __init__(self, base: Iterable[T] | None = None):
        self.classes: dict[T, set[T]] = DefaultFactoryDict(lambda k: {k})
        for elem in base or []:
            self.classes[elem]

    def add_eq(self, *values: T):
        if len(values) < 2:
            return
        val1 = values[0]
        for val in values[1:]:
            self.classes[val1].update(self.classes[val])
            for v in self.classes[val]:
                self.classes[v] = self.classes[val1]

    def is_eq(self, a: T, b: T) -> bool:
        return self.classes[a] is self.classes[b]

    def get(self) -> list[set[T]]:
        sets = {id(s): s for s in self.classes.values()}
        return list(sets.values())


def common_prefix_to_tree(iterable: list[str]) -> Iterable[str]:
    """
    Turns:

    <760>|RP2040.adc[0]|ADC.reference|ElectricPower.max_current|Parameter
    <760>|RP2040.adc[0]|ADC.reference|ElectricPower.voltage|Parameter
    <760>|RP2040.adc[1]|ADC.reference|ElectricPower.max_current|Parameter
    <760>|RP2040.adc[1]|ADC.reference|ElectricPower.voltage|Parameter

    Into:

    <760>|RP2040.adc[0]|ADC.reference|ElectricPower.max_current|Parameter
    -----------------------------------------------.voltage|Parameter
    -----------------1]|ADC.reference|ElectricPower.max_current|Parameter
    -----------------------------------------------.voltage|Parameter

    Notes:
        Recommended to sort the iterable first.
    """
    yield iterable[0]

    for s1, s2 in pairwise(iterable):
        prefix = commonprefix([s1, s2])
        prefix_length = len(prefix)
        yield "-" * prefix_length + s2[prefix_length:]


def ind[T: str | list[str]](lines: T) -> T:
    prefix = "    "
    if isinstance(lines, str):
        return indent(lines, prefix=prefix)
    if isinstance(lines, list):
        return [f"{prefix}{line}" for line in lines]  # type: ignore


def run_live(
    *args,
    stdout: Callable[[str], Any] = logger.debug,
    stderr: Callable[[str], Any] = logger.error,
    **kwargs,
) -> tuple[str, subprocess.Popen]:
    """Runs a process and logs the output live."""

    process = subprocess.Popen(
        *args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
        **kwargs,
    )

    # Set up file descriptors to monitor
    reads = [process.stdout, process.stderr]
    stdout_lines = []
    while reads and process.poll() is None:
        # Wait for output on either stream
        readable, _, _ = select.select(reads, [], [])

        for stream in readable:
            line = stream.readline()
            if not line:  # EOF
                reads.remove(stream)
                continue

            if stream == process.stdout:
                stdout_lines.append(line)
                if stdout:
                    stdout(line.rstrip())
            else:
                if stderr:
                    stderr(line.rstrip())

    # Ensure the process has finished
    process.wait()

    # Get return code and check for errors
    if process.returncode != 0:
        raise subprocess.CalledProcessError(
            process.returncode, args[0], "".join(stdout_lines)
        )

    return "\n".join(stdout_lines), process


@contextmanager
def global_lock(lock_file_path: Path, timeout_s: float | None = None):
    # TODO consider using filelock instead

    lock_file_path.parent.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    while try_or(
        lambda: bool(lock_file_path.touch(exist_ok=False)),
        default=True,
        catch=FileExistsError,
    ):
        # check if pid still alive
        try:
            pid = int(lock_file_path.read_text())
        except ValueError:
            lock_file_path.unlink(missing_ok=True)
            continue
        assert pid != os.getpid()
        if not psutil.pid_exists(pid):
            lock_file_path.unlink(missing_ok=True)
            continue
        if timeout_s and time.time() - start_time > timeout_s:
            raise TimeoutError()
        time.sleep(0.1)

    # write our pid to the lock file
    lock_file_path.write_text(str(os.getpid()))
    try:
        yield
    finally:
        lock_file_path.unlink(missing_ok=True)


def consume(iter: Iterable, n: int) -> list:
    assert n >= 0
    out = list(itertools.islice(iter, n))
    return out if len(out) == n else []


def closest_base_class(cls: type, base_classes: list[type]) -> type:
    """
    Find the most specific (closest) base class from a list of potential base classes.

    Args:
        cls: The class to find the closest base class for
        base_classes: List of potential base classes to check

    Returns:
        The most specific base class from the list that cls inherits from

    Raises:
        ValueError: If cls doesn't inherit from any of the base classes
    """
    # Get all base classes in method resolution order (most specific first)
    mro = cls.__mro__

    # Find the first (most specific) base class that appears in the provided list
    sort = sorted(base_classes, key=lambda x: mro.index(x))
    return sort[0]


def operator_type_check[**P, T](method: Callable[P, T]) -> Callable[P, T]:
    @wraps(method)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        hints = get_type_hints(
            method, include_extras=True
        )  # This resolves string annotations
        sig = inspect.signature(method)
        param_hints = {name: hint for name, hint in hints.items() if name != "return"}

        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        for name, value in bound_args.arguments.items():
            if name not in param_hints:
                continue
            expected_type = param_hints[name]
            # Handle Union, Optional, etc.
            if hasattr(expected_type, "__origin__"):
                expected_type = expected_type.__origin__
            if not isinstance(value, expected_type):
                return NotImplemented

        return method(*args, **kwargs)

    return wrapper


@overload
def partition[Y, T](
    pred: Callable[[T], TypeGuard[Y]], iterable: Iterable[T]
) -> tuple[Iterable[T], Iterable[Y]]: ...


@overload
def partition[T](
    pred: Callable[[T], bool], iterable: Iterable[T]
) -> tuple[Iterable[T], Iterable[T]]: ...


def partition(pred, iterable):  # type: ignore
    from more_itertools import partition as p

    return p(pred, iterable)


def times_out(seconds: float):
    # if running in debugger, don't timeout
    if hasattr(sys, "gettrace") and sys.gettrace():
        return lambda func: func

    def decorator[**P, T](func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(
                    f"Function {func.__name__} exceeded time limit of {seconds}s"
                )

            # Set up the signal handler
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            # Set alarm to trigger after specified seconds
            signal.setitimer(signal.ITIMER_REAL, seconds)

            try:
                return func(*args, **kwargs)
            finally:
                # Cancel the alarm and restore the old signal handler
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old_handler)

        return wrapper

    return decorator


def hash_string(string: str) -> str:
    """Spits out a uuid in hex from a string"""
    return str(
        uuid.UUID(
            bytes=hashlib.blake2b(string.encode("utf-8"), digest_size=16).digest()
        )
    )


def get_module_from_path(
    file_path: os.PathLike, attr: str | None = None, allow_ambiguous: bool = False
) -> ModuleType | None:
    """
    Return a module based on a file path if already imported, or return None.

    If allow_ambiguous is True, and there are multiple modules with the same file path,
    return the first one.
    """
    sanitized_file_path = Path(file_path).expanduser().resolve().absolute()

    def _needle(m: ModuleType) -> bool:
        try:
            file = Path(getattr(m, "__file__"))
        except Exception:
            return False
        return sanitized_file_path.samefile(file)

    try:
        module = find(sys.modules.values(), _needle)
    except KeyErrorNotFound:
        return None
    except KeyErrorAmbiguous as e:
        if allow_ambiguous:
            module = e.duplicates[0]
        else:
            raise

    if attr is None:
        return module

    return getattr(module, attr, None)


def import_from_path(
    file_path: os.PathLike, attr: str | None = None
) -> ModuleType | Type:
    """
    Import a module from a file path.

    If the module is already imported, return the existing module.
    Otherwise, import the module and return the new module.

    Raises FileNotFoundError if the file does not exist.
    Raises AttributeError if the attr is not found in the module.
    """
    # custom unique name to avoid collisions
    # we use this hasher to generate something terse and unique
    module_name = hash_string(str(Path(file_path).expanduser().resolve().absolute()))

    if module_name in sys.modules:
        module = sys.modules[module_name]
    else:
        # setting to a sequence (and not None) indicates that the module is a package,
        # which lets us use relative imports for submodules
        submodule_search_locations = []

        spec = importlib.util.spec_from_file_location(
            module_name,
            file_path,
            submodule_search_locations=submodule_search_locations,
        )
        if spec is None:
            raise ImportError(path=file_path)

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        assert spec.loader is not None

        spec.loader.exec_module(module)

    if attr is None:
        return module
    else:
        return getattr(module, attr)


def has_attr_or_property(obj: object, attr: str) -> bool:
    """Check if an object has an attribute or property by the name `attr`."""
    return hasattr(obj, attr) or (
        hasattr(type(obj), attr) and isinstance(getattr(type(obj), attr), property)
    )


def write_only_property(func: Callable):
    def raise_write_only(*args, **kwargs):
        raise AttributeError(f"{func.__name__} is write-only")

    return property(
        fget=raise_write_only,
        fset=func,
    )


def has_instance_settable_attr(obj: object, attr: str) -> bool:
    """
    Check if an object has an instance attribute that is settable.
    """
    # If we have a property, it's going to tell us all we need to know
    if hasattr(type(obj), attr) and isinstance(getattr(type(obj), attr), property):
        # If the property is settable, use it to set the value
        if getattr(type(obj), attr).fset is not None:
            return True
        # If not, it's not settable, end here
        return False

    # If there's an instance only attribute, we can set it
    if hasattr(obj, attr) and not hasattr(type(obj), attr):
        return True

    # If there's an instance attribute, that's unique compared to the class
    # attribute, we can set it. We don't need to check for a property here
    # because we already checked for that above.
    if (
        hasattr(obj, attr)
        and hasattr(type(obj), attr)
        and getattr(obj, attr) is not getattr(type(obj), attr)
    ):
        return True

    return False


AUTO_RECOMPILE = ConfigFlag(
    "AUTO_RECOMPILE",
    default=False,
    descr="Automatically recompile source files if they have changed",
)


# Check if installed as editable
def is_editable_install():
    distro = Distribution.from_name("atopile")
    return (
        json.loads(distro.read_text("direct_url.json") or "")
        .get("dir_info", {})
        .get("editable", False)
    )


class SerializableEnum[E: Enum](Serializable):
    class Value[E_: Enum](Serializable):
        def __init__(self, enum: "SerializableEnum", value: E_):
            self._value = value
            self._enum = enum

        @property
        def name(self) -> str:
            return self._value.name

        @property
        def value(self) -> E:
            return self._value.value

        @override
        def serialize(self) -> dict:
            return {"name": self._value.name}

        def __eq__(self, other: "SerializableEnum.Value[E]") -> bool:
            if not other._enum == self._enum:
                return False
            return (
                other._value.name == self._value.name
                and other._value.value == self._value.value
            )

        def __hash__(self) -> int:
            return hash(self._value)

        def __repr__(self) -> str:
            return f"{self._enum.enum.__name__}.{self._value.name}"

    def __init__(self, enum: type[Enum]):
        self.enum = enum

        class _Value(SerializableEnum.Value[E]):
            @override
            @staticmethod
            def deserialize(data: dict) -> "_Value":
                return _Value(self, self.enum[data["name"]])

        self.value_cls = _Value

    def serialize(self) -> dict:
        enum = self.enum
        # check enum values to all be ints or str
        if not all(isinstance(e.value, (int, str, float)) for e in enum):
            raise ValueError(f"Can't serialize {enum}: has non-primitive values")

        enum_cls_serialized = {
            "name": enum.__name__,
            "values": {e.name: e.value for e in enum},
        }

        return enum_cls_serialized

    @staticmethod
    def deserialize(data: dict) -> "SerializableEnum":
        enum_cls = Enum(data["name"], data["values"])
        return SerializableEnum(cast(type[Enum], enum_cls))

    def make_value(
        self, value: "E | SerializableEnum.Value[E]"
    ) -> "SerializableEnum.Value[E]":
        if isinstance(value, SerializableEnum.Value):
            return value
        return self.value_cls(self, value)

    def deserialize_value(self, data: dict) -> "SerializableEnum.Value[E]":
        return self.value_cls.deserialize(data)

    def __eq__(self, other: "SerializableEnum") -> bool:
        return self.enum.__name__ == other.enum.__name__ and {
            e.name: e.value for e in self.enum
        } == {e.name: e.value for e in other.enum}


def indented_container(
    obj: Iterable | dict,
    indent_level: int = 1,
    recursive: bool = False,
    use_repr: bool = True,
) -> str:
    kvs = obj.items() if isinstance(obj, dict) else enumerate(obj)

    def format_v(v: Any) -> str:
        if not recursive or not isinstance(v, Iterable) or isinstance(v, str):
            return repr(v) if use_repr else str(v)
        return indented_container(v, indent_level=indent_level + 1, recursive=recursive)

    ind = "\n" + "  " * indent_level
    inside = ind.join(f"{k}: {format_v(v)}" for k, v in kvs)
    if kvs:
        inside = f"{ind}{inside}\n"

    return f"{{{inside}}}"


def robustly_rm_dir(path: os.PathLike) -> None:
    """Remove a directory and all its contents."""

    path = Path(path)

    def remove_readonly(func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(path, onexc=remove_readonly)


def yield_missing(existing: Container, candidates: Iterable | None = None):
    if candidates is None:
        candidates = range(10000)  # Prevent counting to infinity by default
    for c in candidates:
        if c not in existing:
            yield c


def try_relative_to(
    target: os.PathLike, root: os.PathLike | None = None, walk_up: bool = False
) -> Path:
    target = Path(target)
    root = Path(root) if root is not None else Path.cwd()
    try:
        return target.relative_to(root, walk_up=walk_up)
    except FileNotFoundError:
        return target


def repo_root() -> Path:
    repo_root = Path(__file__)
    while not (repo_root / ".git").exists():
        if parent := repo_root.parent:
            repo_root = parent
        else:
            raise FileNotFoundError("Could not find repo root")
    else:
        return repo_root
