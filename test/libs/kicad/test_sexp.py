# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import pytest
from dataclasses_json import CatchAll

import faebryk.library._F as F  # noqa: F401  # This is required to prevent a circular import
from faebryk.libs.kicad.fileformats_latest import C_kicad_pcb_file
from faebryk.libs.sexp.dataclass_sexp import (
    DecodeError,
    SymEnum,
    dumps,
    filter_fields,
    loads,
    sexp_field,
    visit_dataclass,
)
from faebryk.libs.test.fileformats import (
    _FPLIB_DIR,  # noqa: F401
    _NETLIST_DIR,  # noqa: F401
    _PCB_DIR,  # noqa: F401
    _PRJ_DIR,  # noqa: F401
    _SCH_DIR,  # noqa: F401
    _SYM_DIR,  # noqa: F401
    _VERSION_DIR,  # noqa: F401
    DEFAULT_VERSION,  # noqa: F401
    PCBFILE,
)

logger = logging.getLogger(__name__)


def _unformat(s: str) -> str:
    return s.replace("\n", "").replace(" ", "")


@dataclass
class Container:
    @dataclass(kw_only=True)
    class SomeDataclass:
        class E_Numbers(SymEnum):
            ONE = "one"
            TWO = "two"

        a: int = field(**sexp_field(positional=True))
        b: bool = field(**sexp_field(positional=True))
        c: Optional[bool] = field(**sexp_field(positional=True), default=None)
        d: Optional[E_Numbers] = field(**sexp_field(positional=True), default=None)
        f: int
        g: bool
        h: Optional[bool] = None
        i: Optional[E_Numbers] = None

    some_dataclass: SomeDataclass


@pytest.mark.parametrize(
    "container,str_sexp",
    [
        (
            Container(
                some_dataclass=Container.SomeDataclass(
                    a=1, b=True, c=None, d=None, f=2, g=False, h=None, i=None
                )
            ),
            "(some_dataclass 1 yes (f 2) (g no))",
        ),
        (
            Container(
                some_dataclass=Container.SomeDataclass(
                    a=1,
                    b=True,
                    c=False,
                    d=Container.SomeDataclass.E_Numbers.ONE,
                    f=2,
                    g=False,
                    h=True,
                    i=Container.SomeDataclass.E_Numbers.TWO,
                )
            ),
            "(some_dataclass 1 yes no one (f 2) (g no) (h yes) (i two))",
        ),
    ],
)
def test_no_unknowns(container, str_sexp):
    cereal = dumps(container)

    assert _unformat(cereal) == _unformat(str_sexp)

    assert loads(cereal, Container) == container


def test_extra_positional():
    with pytest.raises(DecodeError):
        loads('(some_dataclass 1 yes no "one" gibberish (e 2) (f no))', Container)


def test_empty_unknowns():
    @dataclass
    class Container:
        @dataclass
        class SomeDataclass:
            a: int
            b: str
            unknown: CatchAll = None

        some_dataclass: SomeDataclass

    container = Container(some_dataclass=Container.SomeDataclass(a=1, b="hello"))

    cereal = dumps(container)

    assert _unformat(cereal) == _unformat('(some_dataclass (a 1) (b "hello"))')

    assert loads(cereal, Container) == container


def test_unknowns():
    @dataclass
    class Container:
        @dataclass
        class SomeDataclass:
            a: int
            b: str
            unknown: CatchAll = None

        some_dataclass: SomeDataclass

    cereal = (
        '(some_dataclass gibberish (thingo) (a 1) (b "hello") gibberish (thingo) '
        '(random_key "random_value") (whats_this (who_even_knows True)))'
    )

    container = loads(cereal, Container)

    assert container.some_dataclass.a == 1
    assert container.some_dataclass.b == "hello"
    assert container.some_dataclass.unknown  # there is content

    assert _unformat(dumps(container)) == _unformat(cereal)


def test_print_sexp():
    pcb = C_kicad_pcb_file.loads(PCBFILE)
    dfs = list(visit_dataclass(pcb))
    for it in dfs:
        obj = it.value
        path = it.path
        name_path = it.name_path
        name = "".join(name_path)
        logger.debug(f"{name:70} {[type(p).__name__ for p in path + [obj]]}")

    logger.debug("-" * 80)

    level2 = [p for p in dfs if len(p.path) == 2]
    for it in level2:
        obj = it.value
        path = it.path
        name_path = it.name_path
        name = "".join(name_path)
        logger.debug(f"{name:70}  {[type(p).__name__ for p in path + [obj]]}")


def test_filter_fields():
    from faebryk.libs.sexp.dataclass_sexp import filter_fields

    @dataclass
    class Inner:
        keep_me: str
        remove_me: str
        also_keep: int

    @dataclass
    class Outer:
        name: str
        remove_me: str
        inner: Inner
        inner_list: list[Inner]
        inner_dict: dict[str, Inner]

    # Create test data
    inner1 = Inner(keep_me="hello", remove_me="secret1", also_keep=42)
    inner2 = Inner(keep_me="world", remove_me="secret2", also_keep=99)
    inner3 = Inner(keep_me="test", remove_me="secret3", also_keep=7)

    outer = Outer(
        name="test_outer",
        remove_me="top_secret",
        inner=inner1,
        inner_list=[inner2, inner3],
        inner_dict={"key1": inner1, "key2": inner2},
    )

    # Test filtering single field
    filtered = filter_fields(outer, ["remove_me"])

    # Check that remove_me is set to None in the filtered object
    assert filtered.name == "test_outer"
    assert filtered.remove_me is None

    # Check nested objects
    assert filtered.inner.keep_me == "hello"
    assert filtered.inner.remove_me is None
    assert filtered.inner.also_keep == 42

    # Check list of objects
    assert len(filtered.inner_list) == 2
    for item in filtered.inner_list:
        assert item.keep_me in ["world", "test"]
        assert item.remove_me is None
        assert item.also_keep in [99, 7]

    # Check dict of objects
    assert len(filtered.inner_dict) == 2
    for key, item in filtered.inner_dict.items():
        assert item.keep_me in ["hello", "world"]
        assert item.remove_me is None
        assert item.also_keep in [42, 99]


def test_filter_fields_multiple():
    from faebryk.libs.sexp.dataclass_sexp import filter_fields

    @dataclass
    class TestClass:
        field1: str
        field2: int
        field3: float
        field4: bool
        field5: Optional[str] = None

    obj = TestClass(
        field1="keep", field2=42, field3=3.14, field4=True, field5="optional"
    )

    # Filter multiple fields
    filtered = filter_fields(obj, ["field2", "field4"])

    assert filtered.field1 == "keep"
    assert filtered.field2 is None
    assert filtered.field3 == 3.14
    assert filtered.field4 is None
    assert filtered.field5 == "optional"


def test_filter_fields_edge_cases():
    from faebryk.libs.sexp.dataclass_sexp import filter_fields

    @dataclass
    class SimpleClass:
        value: str

    # Test with empty field list
    obj = SimpleClass(value="test")
    filtered = filter_fields(obj, [])
    assert filtered.value == "test"

    # Test with non-existent field
    filtered = filter_fields(obj, ["non_existent"])
    assert filtered.value == "test"

    # Test with dataclass containing list
    @dataclass
    class ContainerWithList:
        items: list[SimpleClass]

    obj_with_list = ContainerWithList(items=[SimpleClass("a"), SimpleClass("b")])
    filtered_with_list = filter_fields(obj_with_list, ["value"])
    assert len(filtered_with_list.items) == 2
    for item in filtered_with_list.items:
        assert item.value is None

    # Test with dataclass containing tuple
    @dataclass
    class ContainerWithTuple:
        items: tuple[SimpleClass, SimpleClass]

    obj_with_tuple = ContainerWithTuple(items=(SimpleClass("x"), SimpleClass("y")))
    filtered_with_tuple = filter_fields(obj_with_tuple, ["value"])
    assert len(filtered_with_tuple.items) == 2
    assert isinstance(filtered_with_tuple.items, tuple)
    for item in filtered_with_tuple.items:
        assert item.value is None


def test_filter_uuids():
    def filter_uuids(obj: Any) -> Any:
        return filter_fields(obj, ["uuid"])

    @dataclass
    class WithUuid:
        name: str
        uuid: str
        data: int

    obj = WithUuid(name="test", uuid="12345-67890", data=42)
    filtered = filter_uuids(obj)

    assert filtered.name == "test"
    assert filtered.uuid is None
    assert filtered.data == 42
