# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import collections.abc
import difflib
import hashlib
import importlib.util
import inspect
import itertools
import json
import logging
import os
import re
import select
import shutil
import stat
import subprocess
import sys
import time
import uuid
from abc import abstractmethod
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum, StrEnum, auto
from functools import wraps
from genericpath import commonprefix
from importlib.metadata import Distribution
from itertools import chain, pairwise
from json import JSONEncoder
from pathlib import Path
from tempfile import NamedTemporaryFile
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


class Advancable(Protocol):
    def set_total(self, total: int | None) -> None: ...

    def advance(self, advance: int = 1) -> None: ...


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


def duplicates[T, U](
    it: Iterable[T], key: Callable[[T], U], by_eq: bool = False
) -> dict[U, list[T]]:
    if by_eq:
        return {
            k: uv
            for k, v in groupby(it, key).items()
            if len(uv := unique(v, key=lambda x: x)) > 1
        }
    else:
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


def groupby[T, U](
    it: Iterable[T], key: Callable[[T], U], only_multi: bool = False
) -> dict[U, list[T]]:
    out = defaultdict(list)
    for i in it:
        out[key(i)].append(i)
    if only_multi:
        return {k: v for k, v in out.items() if len(v) > 1}
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


def not_none[T](x: T | None) -> T:
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
    assert isinstance(obj, t), f"{obj=} is not an instance of {t}"
    return obj


def times[T](cnt: SupportsInt, lamb: Callable[[], T]) -> list[T]:
    return [lamb() for _ in range(int(cnt))]


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


def once[T, **P](
    f: Callable[P, T], _cacheable: Callable[[T], bool] | None = None
) -> Callable[P, T]:
    # TODO add flag for this optimization
    # might not be desirable if different instances with same hash
    # return same values here
    # check if f is a method with only self
    params = inspect.signature(f).parameters
    # optimization: if takes self, cache in instance (saves hash of instance)
    if "self" in params:
        name = f.__name__
        attr_name = f"_{name}_once"
        param_list = list(params)

        # optimization: if takes only self, no need for dict
        if len(param_list) == 1:

            def wrapper_single(self) -> Any:
                if hasattr(self, attr_name):
                    return getattr(self, attr_name)

                result = f(self)
                if _cacheable is None or _cacheable(result):
                    setattr(self, attr_name, result)

                return result

            return wrapper_single

        # optimization: if takes self + args, use self as cache
        def wrapper_self(*args: P.args, **kwargs: P.kwargs) -> Any:
            self = args[0]
            lookup = (args[1:], tuple(kwargs.items()))
            if not hasattr(self, attr_name):
                setattr(self, attr_name, {})

            cache = getattr(self, attr_name)
            if lookup in cache:
                return cache[lookup]

            result = f(*args, **kwargs)
            if _cacheable is None or _cacheable(result):
                cache[lookup] = result
            return result

        return wrapper_self

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        lookup = (args, tuple(kwargs.items()))
        if lookup in wrapper.cache:
            return wrapper.cache[lookup]

        result = f(*args, **kwargs)
        if _cacheable is None or _cacheable(result):
            wrapper.cache[lookup] = result
        return result

    wrapper.cache = {}
    wrapper._is_once_wrapper = True
    return wrapper


def predicated_once[T](
    pred: Callable[[T], bool],
):
    def decorator[F](f: F) -> F:
        return once(f, pred)

    return decorator


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
        self.value = self._get()
        self._has_been_read = False

    @property
    def name(self) -> str:
        return f"FBRK_{self._name}"

    def set(self, value: T, force: bool = False):
        if self._has_been_read and value != self.value and not force:
            raise ValueError(
                f"Can't write flag {self.name}"
                ", has already been read with different value"
            )
        self.value = value

    @property
    def raw_value(self) -> str | None:
        return os.getenv(self.name, None)

    def get(self) -> T:
        self._has_been_read = True
        return self.value

    def _get(self) -> T:
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


class ConfigFlagFloat(_ConfigFlagBase[float]):
    def __init__(self, name: str, default: float = 0.0, descr: str = "") -> None:
        super().__init__(name, default, descr)

    def _convert(self, raw_val: str) -> float:
        return float(raw_val)

    def __float__(self) -> float:
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


class DAG[T]:
    class Node[T2]:
        def __init__(self, value: T2):
            self.value = value
            self._children = []
            self._parents = []

        @property
        def children(self) -> set[T2]:
            return {child.value for child in self._children}

        @property
        def parents(self) -> set[T2]:
            return {parent.value for parent in self._parents}

    def __init__(self):
        self.nodes: dict[T, DAG[T].Node[T]] = {}

    @property
    def values(self) -> set[T]:
        return set(self.nodes.keys())

    @property
    def roots(self) -> set[T]:
        return {node.value for node in self.nodes.values() if not node.parents}

    @property
    def leaves(self) -> set[T]:
        return {node.value for node in self.nodes.values() if not node.children}

    def get(self, value: T) -> Node[T]:
        return self.add_or_get(value)

    def get_node(self, value: T) -> Node[T] | None:
        return self.nodes.get(value)

    def add_or_get(self, value: T) -> Node[T]:
        node = self.get_node(value)
        if node is not None:
            return node
        node = self.Node(value)
        self.nodes[value] = node
        return node

    def add_edge(self, parent: T, child: T):
        parent_node = self.add_or_get(parent)
        child_node = self.add_or_get(child)
        parent_node._children.append(child_node)
        child_node._parents.append(parent_node)

    def _dfs_cycle_check(
        self, node: Node[T], visiting: set[Node[T]], visited: set[Node[T]]
    ) -> bool:
        """Helper recursive function for cycle detection."""
        visiting.add(node)

        for child in node._children:
            if child in visiting:
                # Cycle detected: trying to visit a node already
                # in the current recursion stack
                return True
            if child not in visited:
                # Recursively check subtree starting from child
                if self._dfs_cycle_check(child, visiting, visited):
                    return True

        # Finished visiting node and all its descendants
        visiting.remove(node)
        visited.add(node)
        return False

    @property
    def contains_cycles(self) -> bool:
        """
        Checks if the graph contains any cycles using Depth First Search.
        """
        visiting = set()  # Nodes currently being visited in the current DFS path
        visited = set()  # Nodes whose subtrees have been fully explored

        # Iterate through all nodes in the graph
        # Necessary for graphs that are not fully connected (forests)
        for node in self.nodes.values():
            if node not in visited:
                if self._dfs_cycle_check(node, visiting, visited):
                    return True  # Cycle found starting from this node

        return False  # No cycles found in any component of the graph

    def to_tree(self, extra_roots: Iterable[T] = tuple()) -> "Tree[T]":
        tree = Tree[T]()

        def node_to_tree(node: DAG[T].Node) -> Tree[T]:
            tree = Tree[T]()
            for child in node._children:
                tree[child.value] = node_to_tree(child)
            return tree

        for root in self.roots | set(extra_roots):
            tree[root] = node_to_tree(self.nodes[root])
        return tree

    def all_parents(self, value: T) -> set[T]:
        node = self.get(value)
        parents = set(node.parents)

        while True:
            new_parents = set()
            for parent in parents:
                new_parents.update(self.get(parent).parents)
            if not new_parents - parents:
                break
            parents.update(new_parents)

        return parents

    @property
    def _in_degrees_by_node(self) -> dict[T, int]:
        return {node.value: len(node._parents) for node in self.nodes.values()}

    def topologically_sorted(self) -> list[T]:
        """
        Performs a topological sort of the DAG.
        Returns a list where each element comes after all its dependencies (parents).
        Raises ValueError if the graph contains cycles.
        """

        if self.contains_cycles:
            raise ValueError("Cannot topologically sort a graph with cycles")

        in_degrees_by_node = self._in_degrees_by_node

        # Start with nodes with no incoming edges
        queue = deque(
            [value for value, degree in in_degrees_by_node.items() if degree == 0]
        )
        out: list[T] = []

        while queue:
            # Remove a node with no incoming edges
            current = queue.popleft()
            out.append(current)

            # Remove edges from current node to its children
            current_node = self.nodes[current]
            for child_node in current_node._children:
                child_value = child_node.value
                in_degrees_by_node[child_value] -= 1

                # If child has no more incoming edges, add to queue
                if in_degrees_by_node[child_value] == 0:
                    queue.append(child_value)

        assert len(out) == len(self.nodes), (
            "Topological sort failed: graph contains cycles"
        )

        return out

    def get_subgraph(self, selector_func: Callable[[T], bool]) -> "DAG[T]":
        """
        Create the smallest subgraph that contains all nodes selected by the selector
        function.

        Args:
            selector_func: A callable that returns True for nodes that must be included

        Returns:
            A new DAG containing the selected nodes and all their dependencies
        """

        subgraph = DAG[T]()

        selected_nodes = {
            node_value for node_value in self.nodes if selector_func(node_value)
        }

        if not selected_nodes:
            return subgraph

        nodes_to_include = selected_nodes.copy()

        for node_value in selected_nodes:
            nodes_to_include |= self.all_parents(node_value)

        for node_value in nodes_to_include:
            subgraph.add_or_get(node_value)

        for node_value in nodes_to_include:
            node = self.nodes[node_value]
            for child_node in node._children:
                if child_node.value in nodes_to_include:
                    subgraph.add_edge(node_value, child_node.value)

        return subgraph


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

    def to_dag(self, dag: DAG[T] | None = None) -> DAG[T]:
        if dag is None:
            dag = DAG()
        for parent, child_tree in self.items():
            child_tree.to_dag(dag)
            for child in child_tree.keys():
                dag.add_edge(parent, child)
        return dag


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
    """
    Unlike dataclasses.asdict because it doesn't convert children dataclasses to dicts.
    This is useful when reconstructing a dataclass from a dict.
    """
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

    def add(self, value: T):
        if value not in self._deref[self._hasher(value)]:
            self._deref[self._hasher(value)].append(value)

    def discard(self, value: T):
        hashed = self._hasher(value)
        if hashed in self._deref and value in self._deref[hashed]:
            self._deref[hashed].remove(value)
            if not self._deref[hashed]:
                del self._deref[hashed]

    def __contains__(self, value: object):
        try:
            # Allow something of broader type than typically allowed
            # but ultimately behave the same
            hash_value = self._hasher(value)  # type: ignore
        except Exception:
            return False
        return value in self._deref[hash_value]

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
                    assert isinstance(result[k], list), (
                        f"Trying to merge list into key '{k}' of type {type(result[k])}"
                    )
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
    cls.__is_abstract__ = cls
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


def invert_dict[T, U](d: dict[T, U]) -> dict[U, list[T]]:
    return groupby(d.keys(), key=lambda k: d[k])


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

    def get(self, only_multi: bool = False) -> list[set[T]]:
        sets = {id(s): s for s in self.classes.values()}
        if only_multi:
            sets = {k: v for k, v in sets.items() if len(v) > 1}
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
    check: bool = True,
    **kwargs,
) -> tuple[str, str, subprocess.Popen]:
    """Runs a process and logs the output live."""

    # on windows just run the command since select does not work
    if sys.platform == "win32":
        return subprocess.run(*args, **kwargs)

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
    stderr_lines = []
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
            elif stream == process.stderr:
                stderr_lines.append(line)
                if stderr:
                    stderr(line.rstrip())

    # Ensure the process has finished
    process.wait()

    # Get return code and check for errors
    if process.returncode != 0 and check:
        raise subprocess.CalledProcessError(
            process.returncode, args[0], "".join(stdout_lines), "".join(stderr_lines)
        )

    return "\n".join(stdout_lines), "\n".join(stderr_lines), process


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
            pid = int(lock_file_path.read_text(encoding="utf-8"))
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
    lock_file_path.write_text(str(os.getpid()), encoding="utf-8")
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


@overload
def partition_as_list[Y, T](
    pred: Callable[[T], TypeGuard[Y]], iterable: Iterable[T]
) -> tuple[list[T], list[Y]]: ...


@overload
def partition_as_list[T](
    pred: Callable[[T], bool], iterable: Iterable[T]
) -> tuple[list[T], list[T]]: ...


def partition_as_list(pred, iterable):  # type: ignore
    false_list, true_list = partition(pred, iterable)
    return list(false_list), list(true_list)


def times_out(seconds: float):
    # if running in debugger, don't timeout
    if hasattr(sys, "gettrace") and sys.gettrace():
        return lambda func: func

    def decorator[**P, T](func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Check the platform
            if sys.platform == "win32":
                # Windows implementation using concurrent.futures
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(func, *args, **kwargs)
                try:
                    # Wait for the function to complete with the specified timeout
                    result = future.result(timeout=seconds)
                    # Shutdown the executor without waiting for the worker thread to
                    # finish
                    # if the result was obtained successfully.
                    executor.shutdown(wait=False, cancel_futures=False)
                    return result
                except FuturesTimeoutError:
                    # If a timeout occurs, cancel the future (best effort) and shutdown.
                    # Raise the standard TimeoutError for consistency.
                    future.cancel()
                    # Shutdown the executor without waiting for the worker thread,
                    # as it's likely stuck or running long.
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise TimeoutError(
                        f"Function {func.__name__} exceeded time limit of {seconds}s"
                    )
                except Exception as e:
                    # If the function itself raised an exception, ensure cleanup and re
                    # -raise.
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise e
            else:
                # Non-Windows (Unix-like) implementation using signal
                import signal  # Import signal only when needed

                def timeout_handler(signum, frame):
                    raise TimeoutError(
                        f"Function {func.__name__} exceeded time limit of {seconds}s"
                    )

                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.setitimer(signal.ITIMER_REAL, seconds)

                try:
                    return func(*args, **kwargs)
                finally:
                    # Clean up the timer and restore the original signal handler
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
            return sanitized_file_path.samefile(file)
        except Exception:
            return False

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
            raise ImportError(path=str(file_path))

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


# Check if installed as editable
def is_editable_install():
    distro = Distribution.from_name("atopile")

    if dist_info := distro.read_text("direct_url.json"):
        return json.loads(dist_info).get("dir_info", {}).get("editable", False)

    return False


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


def indented_container[T](
    obj: Iterable[T] | dict[T, Any],
    indent_level: int = 1,
    recursive: bool = False,
    use_repr: bool = True,
    mapper: Callable[[T | str | int], T | str | int] = lambda x: x,
    compress_large: int = 100,
) -> str:
    kvs = obj.items() if isinstance(obj, dict) else list(enumerate(obj))
    _indent_prefix = "  "
    _indent = _indent_prefix * indent_level
    ind = "\n" + _indent

    def compress(v: str) -> str:
        if len(v) > compress_large:
            return f"{v[:compress_large]}..."
        return v

    def format_v(v: T) -> str:
        if not use_repr and isinstance(v, str):
            return compress(indent(v, prefix=_indent))
        if not recursive or not isinstance(v, Iterable) or isinstance(v, str):
            return compress(repr(mapper(v)) if use_repr else str(mapper(v)))
        return indented_container(
            v,
            indent_level=indent_level + 1,
            recursive=recursive,
            mapper=mapper,
            compress_large=compress_large,
        )

    inside = ind.join(f"{mapper(k)}: {format_v(v)}" for k, v in kvs)
    if len(kvs):
        inside = f"{ind}{inside}\n"

    return f"{{{inside}{_indent_prefix * (indent_level - 1)}}}"


def md_list[T](
    obj: Iterable[T] | dict[T, Any],
    indent_level: int = 0,
    recursive: bool = False,
    mapper: Callable[[T | str | int], T | str | int] = lambda x: x,
) -> str:
    """
    Convert an iterable or dictionary into a nested markdown list.
    """
    indent = f"{'  ' * indent_level}"

    if isinstance(obj, dict):
        kvs = obj.items()
    elif isinstance(obj, str):
        return f"{indent}- {obj}"
    else:
        try:
            kvs = list(enumerate(obj))
        except TypeError:
            return f"{indent}- {str(mapper(obj))}"

    if not kvs:
        if isinstance(obj, Tree):
            return ""
        return f"{indent}- *(empty)*"

    lines = deque()
    for k, v in kvs:
        k = mapper(k)
        v = mapper(v)
        key_str = ""

        if isinstance(obj, dict):
            sep = ":" if not isinstance(v, Tree) or len(v) else ""
            key_str = f" **{k}{sep}**"

        if recursive and isinstance(v, Iterable) and not isinstance(v, str):
            if isinstance(obj, dict):
                lines.append(f"{indent}-{key_str}")
            nested = md_list(v, indent_level + 1, recursive=recursive, mapper=mapper)
            lines.append(nested)
        else:
            value_str = str(v)
            lines.append(f"{indent}-{key_str} {value_str}")

    return "\n".join(lines)


def md_table(obj: Iterable[Iterable[Any]], headers: Iterable[str]) -> str:
    """Convert an iterable of iterables into a markdown table."""

    headers_list = list(headers)
    rows = list(obj)

    if not headers_list:
        return ""

    # Calculate column widths
    col_widths = [len(str(h)) for h in headers_list]
    for row in rows:
        row_list = list(row)
        for i, cell in enumerate(row_list[: len(col_widths)]):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Build header row
    header_cells = []
    for i, header in enumerate(headers_list):
        header_cells.append(str(header).ljust(col_widths[i]))
    header_row = "| " + " | ".join(header_cells) + " |"

    # Build separator row
    separator_cells = ["-" * width for width in col_widths]
    separator_row = "| " + " | ".join(separator_cells) + " |"

    # Build data rows
    data_rows = []
    for row in rows:
        row_list = list(row)
        cells = []
        for i in range(len(headers_list)):
            if i < len(row_list):
                cells.append(str(row_list[i]).ljust(col_widths[i]))
            else:
                cells.append(" " * col_widths[i])
        data_rows.append("| " + " | ".join(cells) + " |")

    # Combine all parts
    result = []
    result.extend([header_row, separator_row] + data_rows)
    return "\n".join(result)


def robustly_rm_dir(path: os.PathLike) -> None:
    """Remove a directory and all its contents."""

    path = Path(path)

    def remove_readonly(func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(path, onexc=remove_readonly)


def yield_missing(existing: Container, candidates: Iterable | int | None = None):
    match candidates:
        case None:
            counter = itertools.count()
        case int():
            counter = itertools.count(candidates)
        case _:
            counter = candidates

    for c in counter:
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
    except ValueError as e:
        if "is not in the subpath of" in str(e):
            return target
        raise


def repo_root() -> Path:
    return root_by_file(".git")


def in_git_repo(path: Path) -> bool:
    """Check if a path is in a git repository."""
    import git

    try:
        git.Repo(path)
    except git.InvalidGitRepositoryError:
        return False
    return True


def test_for_git_executable() -> bool:
    try:
        import git  # noqa: F401
    except ImportError as e:
        # catch no git executable
        if "executable" not in e.msg:
            raise
        return False
    return True


def root_by_file(pattern: str, start: Path = Path(__file__)) -> Path:
    root = start
    while not (root / pattern).exists():
        if parent := root.parent:
            root = parent
        else:
            raise FileNotFoundError("Could not find root")
    else:
        return root


def is_numeric_str(s: str) -> bool:
    """
    Check if a string is a numeric string.
    """
    return s.replace(".", "").strip().isnumeric()


def remove_venv_from_env(base_env: dict[str, str] | None = None):
    """
    Clean and return environment from venv, so subprocess can launch with system env.
    """

    env = base_env.copy() if base_env is not None else os.environ.copy()

    # Does not work, shell variables (not exported)
    # # Restore original PATH if saved
    # if "_OLD_VIRTUAL_PATH" in env:
    #     env["PATH"] = env.pop("_OLD_VIRTUAL_PATH")

    # # Restore original PYTHONHOME if saved
    # if "_OLD_VIRTUAL_PYTHONHOME" in env:
    #     env["PYTHONHOME"] = env.pop("_OLD_VIRTUAL_PYTHONHOME")

    # # Restore original shell prompt if saved (if applicable)
    # if "_OLD_VIRTUAL_PS1" in env:
    #     env["PS1"] = env.pop("_OLD_VIRTUAL_PS1")

    def _is_venv(_path: str) -> bool:
        path = Path(_path)
        if not path.is_dir():
            return False
        if not any((path / p).exists() for p in ["python", "python.exe"]):
            return False
        if not any((path / p).exists() for p in ["activate", "activate.bat"]):
            return False
        return True

    path = [p for p in env["PATH"].split(":") if not _is_venv(p)]

    path = env["PATH"].split(":")

    # Remove virtual environment specific variables
    venv = env.pop("VIRTUAL_ENV", None)
    if venv is not None:
        # Remove venv from PATH
        path = [p for p in path if not p.startswith(venv)]

    # Remove other venvs e.g uv
    path = [p for p in path if not _is_venv(p)]

    env["PATH"] = ":".join(path)

    venv_prompt = env.pop("VIRTUAL_ENV_PROMPT", None)
    if venv_prompt is not None:
        # Remove venv from prompt
        if prompt := env.get("PS1"):
            prompt = prompt.replace(venv_prompt, "")
            env["PS1"] = prompt

    env.pop("PYTHONHOME", None)

    return env


def pretty_type(t: object | type) -> str:
    try:
        return t.__qualname__
    except Exception:
        return str(t)


class SyncedFlag:
    def __init__(self, value: bool = False):
        self.value = value

    def __bool__(self) -> bool:
        return bool(self.value)

    def set(self, value: bool):
        self.value = value


def re_in(value: str, patterns: Iterable[str]) -> bool:
    return any(re.match(pattern, value) for pattern in patterns)


def clone_repo(
    repo_url: str,
    clone_target: Path,
    depth: int | None = None,
    ref: str | None = None,
) -> Path:
    """Clones a git repository and optionally checks out a specific ref.

    Args:
        repo_url: The URL of the repository to clone.
        clone_target: The directory path where the repository should be cloned.
        depth: If specified, creates a shallow clone with a history truncated
               to the specified number of commits.
        ref: The branch, tag, or commit hash to checkout after cloning.

    Returns:
        The path to the cloned repository (clone_target).

    Raises:
        git.GitCommandError: If any git command fails.
    """
    from git import GitCommandError, Repo

    if depth is not None and ref is not None:
        # GitPython doesn't automatically handle fetching missing refs on checkout
        # during shallow clones like the command-line git might with fetch hints.
        raise NotImplementedError("Cannot specify both depth and ref")

    depth_str = f" with depth {depth or 'full'}" if depth is not None else ""
    logger.debug(f"Cloning {repo_url} into {clone_target}{depth_str}...")
    try:
        repo = Repo.clone_from(repo_url, clone_target, depth=depth)
        logger.debug(f"Successfully cloned {repo_url}")
    except GitCommandError as e:
        logger.error(f"Failed to clone {repo_url}: {e}")
        raise

    if ref:
        logger.debug(f"Checking out ref {ref} in {clone_target}...")
        try:
            repo.git.checkout(ref)
            logger.debug(f"Successfully checked out ref {ref}")
        except GitCommandError as e:
            logger.error(f"Failed to checkout ref {ref}: {e}")
            raise

    return clone_target


def find_file(base_dir: Path, pattern: str):
    """
    equivalent to `find base_dir -type f -name pattern`
    """
    if not base_dir.exists() or not base_dir.is_dir():
        return None
    for file in base_dir.rglob(pattern):
        if file.is_file():
            yield file


def call_with_file_capture[T](func: Callable[[Path], T]) -> tuple[T, bytes]:
    with NamedTemporaryFile("wb", delete=False, delete_on_close=False) as f:
        path = Path(f.name)
    out = func(path), path.read_bytes()
    path.unlink()
    return out


def diff(before: str, after: str) -> str:
    """
    diff two strings
    """
    return "\n".join(difflib.ndiff(before.splitlines(), after.splitlines()))


def compare_dataclasses[T](
    before: T,
    after: T,
    skip_keys: tuple[str, ...] = (),
    require_dataclass_type_match: bool = True,
) -> dict[str, dict[str, Any]]:
    """
    Check two dataclasses for equivalence (with some keys skipped).

    Parameters:
        before: The first dataclass to compare.
        after: The second dataclass to compare.
        skip_keys: A tuple of keys to skip when encountered at any level.
        require_dataclass_type_match: If False, compare dataclasses on fields only.
    """

    def _fmt(b, a):
        return {"before": b, "after": a}

    def _dataclasses_are_comparable(b, a):
        return type(b) is type(a) or (
            not require_dataclass_type_match
            and {field.name for field in fields(b) if field.name not in skip_keys}
            == {field.name for field in fields(a) if field.name not in skip_keys}
        )

    match (before, after):
        case (list(), list()):
            return {
                f"[{i}]{k}": v
                for i, (b, a) in enumerate(zip(before, after))
                for k, v in compare_dataclasses(
                    b,
                    a,
                    skip_keys=skip_keys,
                    require_dataclass_type_match=require_dataclass_type_match,
                ).items()
            }
        case (dict(), dict()):
            return {
                f"[{i!r}]{k}": v
                for i, (b, a) in zip_dicts_by_key(before, after).items()
                for k, v in compare_dataclasses(
                    b,
                    a,
                    skip_keys=skip_keys,
                    require_dataclass_type_match=require_dataclass_type_match,
                ).items()
                if i not in skip_keys
            }
        case before, after if (
            is_dataclass(before)
            and is_dataclass(after)
            and _dataclasses_are_comparable(before, after)
        ):
            return {
                f".{f.name}{k}": v
                for f in fields(before)  # type: ignore
                if f.name not in skip_keys
                for k, v in compare_dataclasses(
                    getattr(before, f.name),
                    getattr(after, f.name),
                    skip_keys=skip_keys,
                    require_dataclass_type_match=require_dataclass_type_match,
                ).items()
            }
        case _:
            return {"": _fmt(before, after)} if before != after else {}


def complete_type_string(value: Any) -> str:
    if isinstance(value, (list, set)):
        inner = unique(
            (complete_type_string(item) for item in value),
            lambda x: x,
        )
        return f"{type(value).__name__}[{' | '.join(inner)}]"
    elif isinstance(value, dict):
        inner_value = unique(
            (complete_type_string(item) for item in value.values()),
            lambda x: x,
        )
        inner_key = unique(
            (complete_type_string(item) for item in value.keys()),
            lambda x: x,
        )
        return (
            f"{type(value).__name__}["
            f"{' | '.join(inner_key)}, "
            f"{' | '.join(inner_value)}]"
        )
    elif isinstance(value, tuple):
        inner = unique(
            (complete_type_string(item) for item in value),
            lambda x: x,
        )
        return f"{type(value).__name__}[{', '.join(inner)}]"
    else:
        return type(value).__name__


def has_uncommitted_changes(files: Iterable[str | Path]) -> bool | None:
    """Check if any of the given files have uncommitted changes."""
    try:
        from git import Repo

        repo = Repo(search_parent_directories=True)
        diff_index = repo.index.diff(None)  # Get uncommitted changes

        # Convert all files to Path objects for consistent comparison
        files = [Path(f).resolve() for f in files]
        repo_root = Path(repo.working_dir)

        # Check if any of the files have changes
        for diff in diff_index:
            touched_file = diff.a_path or diff.b_path
            # m, c or d
            assert touched_file is not None
            touched_path = repo_root / touched_file
            if touched_path in files:
                return True

        return False
    # TODO bad
    except Exception:
        # If we can't check git status (not a git repo, etc), assume we don't
        # have changes
        return None


def least_recently_modified_file(*paths: Path) -> tuple[Path, datetime] | None:
    files = []
    for path in paths:
        if path.is_dir():
            files.extend(path.rglob("**"))
        elif path.is_file():
            files.append(path)
    if not files:
        return None

    files_with_dates = [
        (f, datetime.fromtimestamp(max(f.stat().st_mtime, f.stat().st_ctime)))
        for f in files
    ]
    return max(files_with_dates, key=lambda f: f[1])


class FileChangedWatcher:
    class CheckMethod(Enum):
        FS = auto()
        HASH = auto()

    def __init__(self, path: Path, method: CheckMethod):
        self.path = path
        self.method = method

        match method:
            case FileChangedWatcher.CheckMethod.FS if path.is_file():
                self.before = path.stat().st_mtime
            case FileChangedWatcher.CheckMethod.HASH if path.is_file():
                self.before = hashlib.sha256(
                    path.read_bytes(), usedforsecurity=False
                ).hexdigest()
            case _:
                self.before = None

    def has_changed(self, reset: bool = False) -> bool:
        changed = True
        match self.method:
            case FileChangedWatcher.CheckMethod.FS if self.path.is_file():
                new_val = self.path.stat().st_mtime
                if self.before is not None:
                    assert isinstance(self.before, float)
                    changed = new_val > self.before
            case FileChangedWatcher.CheckMethod.HASH if self.path.is_file():
                new_val = hashlib.sha256(
                    self.path.read_bytes(), usedforsecurity=False
                ).hexdigest()
                if self.before is not None:
                    assert isinstance(self.before, str)
                    changed = new_val != self.before
            case _:
                new_val = None
                changed = self.before is not None

        if reset:
            self.before = new_val

        return changed


def lazy_split[T: str | bytes](string: T, delimiter: T) -> Iterable[T]:
    """
    Split a string into a list of strings, but only split when needed.
    """

    # TODO: type checking goes ham because of bytes

    cur: T = string
    while (i := cur.find(delimiter)) != -1:  # type: ignore
        yield cur[:i]  # type: ignore
        cur = cur[i + len(delimiter) :]  # type: ignore
    yield cur


def starts_or_ends_replace(
    match: str, options: tuple[str, ...], *, prefix: str = "", suffix: str = ""
) -> str:
    for o in options:
        if match.startswith(o):
            return f"{prefix}{match[len(o) :]}{suffix}"
        elif match.endswith(o):
            return f"{prefix}{match[: -len(o)]}{suffix}"
    return match


def sanitize_filepath_part(x: str) -> str:
    """
    Replaces invalid or awkward characters with underscores.
    """
    x = re.sub(r"[^a-zA-Z0-9_]", "_", x)
    x = x.strip("_")
    return x


def get_code_bin_of_terminal() -> str | None:
    if not os.environ.get("TERM_PROGRAM") == "vscode":
        return None

    # Try cursor, fallback to code
    options = ["cursor", "code"]

    for option in options:
        code_bin = shutil.which(option)
        if code_bin:
            return code_bin

    return None


def list_match[T](base: list[T], match: list[T]) -> Generator[int, None, None]:
    for i in range(len(base)):
        if base[i : i + len(match)] == match:
            yield i


def sublist_replace[T](base: list[T], match: list[T], replacement: list[T]) -> list[T]:
    out: list[T] = []
    buffer: list[T] = []

    for i in base:
        buffer.append(i)
        if len(buffer) > len(match):
            out.append(buffer.pop(0))
        if buffer == match:
            out.extend(replacement)
            buffer = []
    out.extend(buffer)
    return out


def path_replace(base: Path, match: Path, replacement: Path) -> Path:
    return Path(
        *sublist_replace(
            list(base.parts),
            list(match.parts),
            list(replacement.parts),
        ),
    )


def sort_dataclass(
    obj: Any, sort_key: Callable[[Any], Any], prefix: str = "", inplace: bool = True
) -> Any:
    if not inplace:
        obj = deepcopy(obj)  # TODO: more efficient copy

    for f in fields(obj):
        val = getattr(obj, f.name)
        if isinstance(val, list):
            s = sorted(val, key=sort_key)
            setattr(obj, f.name, s)
            for v in s:
                if is_dataclass(v):
                    sort_dataclass(v, sort_key, prefix=f"{prefix}.{f.name}")
        elif isinstance(val, dict):
            s = dict(sorted(val.items(), key=lambda x: sort_key(x[1])))
            setattr(obj, f.name, s)
            for v in s.values():
                if is_dataclass(v):
                    sort_dataclass(v, sort_key, prefix=f"{prefix}.{f.name}")
        elif is_dataclass(val):
            sort_dataclass(val, sort_key, prefix=f"{prefix}.{f.name}")
    return obj


def round_dataclass(obj: Any, precision: int = 0) -> Any:
    if isinstance(obj, (float, int)):
        return round(obj, precision)

    if not is_dataclass(obj):
        return obj

    for f in fields(obj):
        val = getattr(obj, f.name)
        if isinstance(val, float):
            setattr(obj, f.name, round(val, precision))
        elif isinstance(val, list):
            val = [round_dataclass(v, precision) for v in val]
        elif isinstance(val, dict):
            val = {k: round_dataclass(v, precision) for k, v in val.items()}
        elif is_dataclass(val):
            round_dataclass(val, precision)
    return obj


def match_iterables[T, U](
    *iterables: Iterable[T], key: Callable[[T], U] = lambda x: x
) -> dict[U, Iterable[T]]:
    multi_dicts = [groupby(iterable, key) for iterable in iterables]
    if not all(len(vs) == 1 for d in multi_dicts for vs in d.values()):
        raise ValueError("All iterables must have unique keys")
    dicts = [{k: vs[0] for k, vs in d.items()} for d in multi_dicts]
    return zip_dicts_by_key(*dicts)  # type: ignore
