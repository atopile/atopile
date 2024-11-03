import logging
from dataclasses import Field, dataclass, fields, is_dataclass
from enum import Enum, IntEnum, StrEnum
from os import PathLike
from pathlib import Path
from types import UnionType
from typing import Any, Callable, Iterator, Union, get_args, get_origin

import sexpdata
from sexpdata import Symbol

from faebryk.libs.sexp.util import prettify_sexp_string
from faebryk.libs.util import cast_assert, duplicates, groupby, zip_non_locked

logger = logging.getLogger(__name__)

# TODO: Should be its own repo

"""
This is a generic sexp-dataclass converter (similar to dataclass_json).
It is used to convert between dataclasses and sexp (s-expressions).
It only supports a specific subset of sexp that is used by KiCAD with following rules:
- Only atom order is important
- Multi-key dict is supported
"""


@dataclass
class sexp_field(dict[str, Any]):
    """
    Metadata for a field to be used in the sexp conversion

    :param bool positional: If True, the fields position will be used instead
    of its name
    :param bool multidict: If True, the field will be converted to a list of
    key-value pairs. Not compatible in combination with positional.
    :param Callable key: Function to extract key from value in multidict
    :param Any assert_value: Assert that the value is equal to this value
    :param int order: Order of the field in the sexp, lower is first,
    can be less than 0. Only used if not positional.
    :param Callable[[Any], Any] | None preprocessor: Run before conversion
    """

    positional: bool = False
    multidict: bool = False
    key: Callable[[Any], Any] | None = None
    assert_value: Any | None = None
    order: int = 0
    preprocessor: Callable[[Any], Any] | None = None

    def __post_init__(self):
        super().__init__({"metadata": {"sexp": self}})

        assert not (self.positional and self.multidict)
        assert (self.key is None) or self.multidict, "Key only supported for multidict"

    @classmethod
    def from_field(cls, f: Field):
        out = f.metadata.get("sexp", cls())
        assert isinstance(out, cls)
        return out


class SymEnum(StrEnum): ...


class DecodeError(Exception):
    """Error during decoding"""


def _prettify_stack(stack: list[tuple[str, type]] | None) -> str:
    if stack is None:
        return "<top-level>"
    return ".".join(s[0] for s in stack)


def _convert(
    val,
    t,
    stack: list[tuple[str, type]] | None = None,
    name: str | None = None,
    sp: sexp_field | None = None,
):
    if name is None:
        name = "<" + t.__name__ + ">"
    if stack is None:
        stack = []
    substack = stack + [(name, t)]

    try:
        # Run preprocessor, if it exists
        if sp and sp.preprocessor:
            val = sp.preprocessor(val)

        # Recurse (GenericAlias e.g list[])
        if (origin := get_origin(t)) is not None:
            args = get_args(t)
            if origin is list:
                return [_convert(_val, args[0], substack) for _val in val]
            if origin is tuple:
                return tuple(
                    _convert(_val, _t, substack) for _val, _t in zip(val, args)
                )
            if (
                origin in (Union, UnionType)
                and len(args) == 2
                and args[1] is type(None)
            ):
                return _convert(val, args[0], substack) if val is not None else None

            raise NotImplementedError(f"{origin} not supported")

        #
        if is_dataclass(t):
            return _decode(val, t, substack)

        # Primitive

        # Unpack list if single atom
        if isinstance(val, list) and len(val) == 1 and not isinstance(val[0], list):
            val = val[0]

        if issubclass(t, bool):
            # See parseMaybeAbsentBool in kicad
            # Default: (hide) hide None
            # True: (hide yes)
            # False: (hide no)

            # hide, None -> automatically filtered

            # (hide yes) (hide no)
            if val in [Symbol("yes"), Symbol("no")]:
                return val == Symbol("yes")

            # (hide)
            if val == []:
                return None

            raise ValueError(f"Invalid value for bool: {val}")

        if isinstance(val, Symbol):
            return t(str(val))

        return t(val)
    except DecodeError:
        raise
    except Exception as e:
        raise DecodeError(
            f"Failed to decode {_prettify_stack(substack)} ({t}) with {val} "
        ) from e


netlist_obj = str | Symbol | int | float | bool | list
netlist_type = list[netlist_obj]


def _decode[T](
    sexp: netlist_type,
    t: type[T],
    stack: list[tuple[str, type]] | None = None,
) -> T:
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"parse into: {t.__name__} {'-'*40}")
        logger.debug(f"sexp: {sexp}")

    # check if t is dataclass type
    if not hasattr(t, "__dataclass_fields__"):
        # is_dataclass(t) trips mypy
        raise TypeError(f"{t} is not a dataclass type")

    value_dict = {}

    # Fields
    fs = fields(t)
    key_fields = {f.name: f for f in fs if not sexp_field.from_field(f).positional}
    positional_fields = {
        i: f for i, f in enumerate(fs) if sexp_field.from_field(f).positional
    }

    # Values
    unprocessed_indices = set()
    ungrouped_key_values = []
    # I'd prefer to do this through a filter/comprehension, but I don't see a good way
    for i, val in enumerate(sexp):
        if isinstance(val, list):
            if len(val):
                if isinstance(key := val[0], Symbol):
                    if str(key) + "s" in key_fields or str(key) in key_fields:
                        ungrouped_key_values.append(val)
                        continue

        unprocessed_indices.add(i)

    key_values = groupby(
        ungrouped_key_values,
        lambda val: (
            str(val[0]) + "s" if str(val[0]) + "s" in key_fields else str(val[0])
        ),
    )
    pos_values = {
        i: val
        for i, val in enumerate(sexp)
        if isinstance(val, (str, int, float, Symbol, bool))
        or (isinstance(val, list) and (not len(val) or not isinstance(val[0], Symbol)))
        # and i in positional_fields
        # and positional_fields[i].name not in value_dict
    }
    unprocessed_indices = unprocessed_indices - set(pos_values.keys())

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"processing: {_prettify_stack(stack)}")
        logger.debug(f"key_fields: {list(key_fields.keys())}")
        logger.debug(
            f"positional_fields: {list(f.name for f in positional_fields.values())}"
        )
        logger.debug(f"key_values: {list(key_values.keys())}")
        logger.debug(f"pos_values: {pos_values}")

    if len(unprocessed_indices):
        unprocessed_values = [sexp[i] for i in unprocessed_indices]
        # This is separate from the above loop to make it easier to debug during dev
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"unprocessed values: {unprocessed_values}")

    # Parse --------------------------------------------------------------

    # Key-Value
    for s_name, f in key_fields.items():
        name = f.name
        sp = sexp_field.from_field(f)
        if s_name not in key_values:
            if sp.multidict and not (f.default_factory or f.default):
                base_type = get_origin(f.type) or f.type
                value_dict[name] = base_type()
            # will be automatically filled by factory
            continue

        values = key_values[s_name]
        if sp.multidict:
            origin = get_origin(f.type)
            args = get_args(f.type)
            if origin is list:
                val_t = args[0]
                value_dict[name] = [
                    _convert(_val[1:], val_t, stack, name, sp) for _val in values
                ]
            elif origin is dict:
                if not sp.key:
                    raise ValueError(f"Key function required for multidict: {f.name}")
                key_t = args[0]
                val_t = args[1]
                converted_values = [
                    _convert(_val[1:], val_t, stack, name, sp) for _val in values
                ]
                values_with_key = [(sp.key(_val), _val) for _val in converted_values]

                if not all(isinstance(k, key_t) for k, _ in values_with_key):
                    raise KeyError(
                        f"Key function returned invalid type in field {f.name}:"
                        f" {key_t=} types={[v[0] for v in values_with_key]}"
                    )
                if d := duplicates(values_with_key, key=lambda v: v[0]):
                    raise ValueError(f"Duplicate keys: {d}")
                value_dict[name] = dict(values_with_key)
            else:
                raise NotImplementedError(
                    f"Multidict not supported for {origin} in field {f}"
                )
        else:
            assert len(values) == 1, f"Duplicate key: {name}"
            out = _convert(values[0][1:], f.type, stack, name, sp)
            # if val is None, use default
            if out is not None:
                value_dict[name] = out

    # Positional
    for f, v in (it := zip_non_locked(positional_fields.values(), pos_values.values())):
        sp = sexp_field.from_field(f)
        # special case for missing positional empty StrEnum fields
        if isinstance(f.type, type) and issubclass(f.type, StrEnum):
            if "" in f.type and not isinstance(v, Symbol):
                value_dict[f.name] = _convert(Symbol(""), f.type, stack, f.name, sp)
                # only advance field iterator
                # if no more positional fields, there shouldn't be any more values
                if it.next(0) is None:
                    raise ValueError(f"Unexpected symbol {v}")
                continue

        # positional list = var args
        origin = get_origin(f.type)
        if origin is list:
            vs = []
            next_val = v
            # consume all values
            while next_val is not None:
                vs.append(next_val)
                next_val = it.next(1, None)
            out = _convert(vs, f.type, stack, f.name, sp)
        else:
            out = _convert(v, f.type, stack, f.name, sp)

        value_dict[f.name] = out

    # Check assertions ----------------------------------------------------
    for f in fs:
        sp = sexp_field.from_field(f)
        if sp.assert_value is not None:
            assert value_dict[f.name] == sp.assert_value, (
                f"Fileformat assertion! {f.name} has to be"
                f" {sp.assert_value} but is {value_dict[f.name]}"
            )

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"value_dict: {value_dict}")

    try:
        out = t(**value_dict)
        # set parent pointers for all dataclasses in the tree
        for k, v in value_dict.items():
            if isinstance(v, list):
                vs = v
            else:
                vs = [v]
            for v_ in vs:
                if is_dataclass(v_):
                    setattr(v_, "_parent", out)
        return out
    except TypeError as e:
        raise TypeError(f"Failed to create {t} with {value_dict}") from e


def _convert2(val: Any) -> netlist_obj | None:
    if val is None:
        return None
    if is_dataclass(val):
        return _encode(val)
    if isinstance(val, list):
        return [_convert2(v) for v in val]
    if isinstance(val, tuple):
        return [_convert2(v) for v in val]
    if isinstance(val, dict):
        return [_convert2(v) for v in val.values()]
    if isinstance(val, SymEnum):
        return Symbol(val)
    if isinstance(val, StrEnum):
        return str(val)
    if isinstance(val, IntEnum):
        return int(val)
    if isinstance(val, Enum):
        return Symbol(val)
    if isinstance(val, bool):
        return Symbol("yes" if val else "no")
    if isinstance(val, float):
        if val.is_integer():
            return int(val)
        return val
    if isinstance(val, (str, int)):
        return val

    return str(val)


def _encode(t) -> netlist_type:
    if not is_dataclass(t):
        raise TypeError(f"{t} is not a dataclass type")

    sexp: netlist_type = []

    def _append(_val):
        if val is None:
            return
        sexp.append(_val)

    fs = [(f, sexp_field.from_field(f)) for f in fields(t)]

    for f, sp in sorted(fs, key=lambda x: (not x[1].positional, x[1].order)):
        name = f.name
        val = getattr(t, name)

        if sp.positional:
            if isinstance(val, list):
                for v in val:
                    _append(_convert2(v))
                continue
            _append(_convert2(val))
            continue

        def _append_kv(name, v):
            converted = _convert2(v)
            if converted is None:
                return
            if isinstance(converted, list):
                _append([Symbol(name), *converted])
                return
            _append([Symbol(name), converted])

        if sp.multidict:
            if isinstance(val, list):
                assert get_origin(f.type) is list
                _val = val
            elif isinstance(val, dict):
                assert get_origin(f.type) is dict
                _val = val
                _val = val.values()
            else:
                raise TypeError()
            for v in _val:
                _append_kv(f.name.removesuffix("s"), v)
        else:
            _append_kv(f.name, val)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Dumping {type(t).__name__} {'-'*40}")
        logger.debug(f"Obj: {t}")
        logger.debug(f"Sexp: {sexp}")

    return sexp


def loads[T](s: str | Path | list, t: type[T]) -> T:
    text = s
    sexp = s
    if isinstance(s, Path):
        text = s.read_text()
    if isinstance(text, str):
        sexp = sexpdata.loads(text)

    return _decode([sexp], t)


def dumps(obj, path: PathLike | None = None) -> str:
    path = Path(path) if path else None
    sexp = _encode(obj)[0]
    text = sexpdata.dumps(sexp)
    text = prettify_sexp_string(text)
    if path:
        path.write_text(text)
    return text


def dump_single(obj) -> str:
    @dataclass
    class _(SEXP_File):
        node: type[obj]

    filenode = _(node=obj)

    return filenode.dumps()


class SEXP_File:
    @classmethod
    def loads(cls, path_or_string_or_data: Path | str | list):
        return loads(path_or_string_or_data, cls)

    def dumps(self, path: PathLike | None = None):
        return dumps(self, path)


def get_parent[T](obj, t: type[T]) -> T:
    assert hasattr(obj, "_parent")
    return cast_assert(t, obj._parent)


# TODO move
class JSON_File:
    @classmethod
    def loads[T](cls: type[T], path: Path | str) -> T:
        text = path
        if isinstance(path, Path):
            text = path.read_text()
        return cls.from_json(text)

    def dumps(self, path: PathLike | None = None):
        path = Path(path) if path else None
        text = self.to_json(indent=4)
        if path:
            path.write_text(text)
        return text


def dataclass_dfs(obj) -> Iterator[tuple[Any, list, list[str]]]:
    """
    Iterates over all dataclass fields and their values.

    Yields tuples of:
    - value of the field
    - list of the objects leading to the value
    - list of the names of the fields leading to the value
    """
    return _iterate_tree(obj, [], [])


def _iterate_tree(
    obj, path: list, name_path: list[str]
) -> Iterator[tuple[Any, list, list[str]]]:
    out_path = path + [obj]

    yield obj, path, name_path

    if is_dataclass(obj):
        for f in fields(obj):
            yield from _iterate_tree(
                getattr(obj, f.name), out_path, name_path + [f".{f.name}"]
            )
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _iterate_tree(v, out_path, name_path + [f"[{i}]"])
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iterate_tree(v, out_path, name_path + [f"[{repr(k)}]"])
