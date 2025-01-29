# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import pytest
from dataclasses_json import CatchAll

import faebryk.library._F as F  # noqa: F401  # This is required to prevent a circular import
from faebryk.libs.kicad.fileformats import C_kicad_pcb_file
from faebryk.libs.sexp.dataclass_sexp import dataclass_dfs, dumps, loads
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


def test_no_unknowns():
    @dataclass
    class Container:
        @dataclass
        class SomeDataclass:
            a: int
            b: str

        some_dataclass: SomeDataclass

    container = Container(some_dataclass=Container.SomeDataclass(a=1, b="hello"))
    cereal = dumps(container)

    assert _unformat(cereal) == _unformat('(some_dataclass (a 1) (b "hello"))')

    assert loads(cereal, Container) == container

    bad_cereal = '(some_dataclass gibberish (a 1) (b "hello"))'
    with pytest.raises(ValueError):
        loads(bad_cereal, Container)


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
        '(some_dataclass (a 1) (b "hello") gibberish (thingo) (random_key'
        ' "random_value") (whats_this (who_even_knows True)))'
    )

    container = loads(cereal, Container)

    assert container.some_dataclass.a == 1
    assert container.some_dataclass.b == "hello"
    assert container.some_dataclass.unknown  # there is content

    assert _unformat(dumps(container)) == _unformat(cereal)


def test_print_sexp():
    pcb = C_kicad_pcb_file.loads(PCBFILE)
    dfs = list(dataclass_dfs(pcb))
    for obj, path, name_path in dfs:
        name = "".join(name_path)
        logger.debug(f"{name:70} {[type(p).__name__ for p in path + [obj]]}")

    logger.debug("-" * 80)

    level2 = [p for p in dfs if len(p[1]) == 2]
    for obj, path, name_path in level2:
        name = "".join(name_path)
        logger.debug(f"{name:70}  {[type(p).__name__ for p in path + [obj]]}")
