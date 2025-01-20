# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass
from pathlib import Path

import pytest
from dataclasses_json import CatchAll

import faebryk.library._F as F  # noqa: F401  # This is required to prevent a circular import
from faebryk.libs.kicad.fileformats import (
    C_effects,
    C_footprint,
    C_kicad_footprint_file,
    C_kicad_fp_lib_table_file,
    C_kicad_netlist_file,
    C_kicad_pcb_file,
    C_kicad_project_file,
)
from faebryk.libs.kicad.fileformats_sch import C_kicad_sch_file, C_kicad_sym_file
from faebryk.libs.kicad.fileformats_version import kicad_footprint_file
from faebryk.libs.sexp.dataclass_sexp import (
    JSON_File,
    SEXP_File,
    dataclass_dfs,
    dumps,
    loads,
)
from faebryk.libs.test.fileformats import (
    _FP_DIR,
    _FPLIB_DIR,  # noqa: F401
    _NETLIST_DIR,  # noqa: F401
    _PCB_DIR,  # noqa: F401
    _PRJ_DIR,  # noqa: F401
    _SCH_DIR,  # noqa: F401
    _SYM_DIR,  # noqa: F401
    _VERSION_DIR,  # noqa: F401
    DEFAULT_VERSION,  # noqa: F401
    FPFILE,
    FPLIBFILE,
    NETFILE,
    PCBFILE,
    PRJFILE,
    SCHFILE,
    SYMFILE,
)
from faebryk.libs.util import ConfigFlag, find, not_none

logger = logging.getLogger(__name__)

DUMP = ConfigFlag("DUMP", descr="dump load->save into /tmp")


def test_parser():
    pcb = C_kicad_pcb_file.loads(PCBFILE)
    fp = C_kicad_footprint_file.loads(FPFILE)
    netlist = C_kicad_netlist_file.loads(NETFILE)
    pro = C_kicad_project_file.loads(PRJFILE)
    sch = C_kicad_sch_file.loads(SCHFILE)
    sym = C_kicad_sym_file.loads(SYMFILE)

    assert [f.name for f in pcb.kicad_pcb.footprints] == [
        "logos:faebryk_logo",
        "lcsc:LED0603-RD-YELLOW",
        "lcsc:R0402",
        "lcsc:BAT-TH_BS-02-A1AJ010",
    ]

    assert not pcb.kicad_pcb.setup.pcbplotparams.usegerberextensions

    padtype = pcb.C_kicad_pcb.C_pcb_footprint.C_pad.E_type
    assert [(p.name, p.type) for p in fp.footprint.pads] == [
        ("", padtype.smd),
        ("", padtype.smd),
        ("1", padtype.smd),
        ("2", padtype.smd),
    ]

    assert [(c.ref, c.value) for c in netlist.export.components.comps][:10] == [
        ("C1", "10uF"),
        ("C2", "10uF"),
        ("C3", "10uF"),
        ("C4", "10uF"),
        ("C5", "22uF"),
        ("C6", "100nF"),
        ("C7", "100nF"),
        ("C8", "10uF"),
        ("C9", "100nF"),
        ("C10", "100nF"),
    ]

    # Var args parser
    effects = (
        find(pcb.kicad_pcb.footprints, lambda f: f.name == "logos:faebryk_logo")
        .propertys["Footprint"]
        .effects
    )
    assert effects.justifys[0].justifys == [
        C_effects.C_justify.E_justify.mirror,
        C_effects.C_justify.E_justify.right,
    ]
    assert effects.justifys[1].justifys == [
        C_effects.C_justify.E_justify.bottom,
    ]

    assert effects.get_justifys() == [
        C_effects.C_justify.E_justify.mirror,
        C_effects.C_justify.E_justify.right,
        C_effects.C_justify.E_justify.bottom,
    ]

    assert pro.pcbnew.last_paths.netlist == "../../faebryk/faebryk.net"

    assert (
        sch.kicad_sch.lib_symbols.symbols["Amplifier_Audio:LM4990ITL"]
        .propertys["Datasheet"]
        .value
        == "http://www.ti.com/lit/ds/symlink/lm4990.pdf"
    )

    assert sch.kicad_sch.lib_symbols.symbols["power:GND"].power is not None
    assert sch.kicad_sch.lib_symbols.symbols["Device:R"].power is None

    assert (
        sym.kicad_symbol_lib.symbols["AudioJack-CUI-SJ-3523-SMT"].name
        == "AudioJack-CUI-SJ-3523-SMT"
    )


def test_write():
    pcb = C_kicad_pcb_file.loads(PCBFILE)

    def _d1(pcb: C_kicad_pcb_file):
        return find(
            pcb.kicad_pcb.footprints,
            lambda f: f.propertys["Reference"].value == "D1",
        )

    led_p = _d1(pcb).propertys["Value"]
    assert led_p.value == "LED"
    led_p.value = "LED2"

    pcb_reload = C_kicad_pcb_file.loads(pcb.dumps())
    assert _d1(pcb_reload).propertys["Value"].value == "LED2"


def test_empty_enum_positional():
    pcb = C_kicad_pcb_file.loads(PCBFILE)

    def _b1_p1(pcb: C_kicad_pcb_file):
        return find(
            find(
                pcb.kicad_pcb.footprints,
                lambda f: f.propertys["Reference"].value == "B1",
            ).pads,
            lambda p: p.name == "1",
        )

    _b1_p1(pcb).drill = C_footprint.C_pad.C_drill(
        C_footprint.C_pad.C_drill.E_shape.stadium, 0.5, 0.4
    )

    def _effects(pcb: C_kicad_pcb_file):
        return (
            find(pcb.kicad_pcb.footprints, lambda f: f.name == "logos:faebryk_logo")
            .propertys["Datasheet"]
            .effects
        )

    _effects(pcb).justifys.append(
        C_effects.C_justify([C_effects.C_justify.E_justify.center_horizontal])
    )
    _effects(pcb).justifys.append(
        C_effects.C_justify([C_effects.C_justify.E_justify.top])
    )

    pcb_reload = C_kicad_pcb_file.loads(pcb.dumps())

    assert (
        not_none(_b1_p1(pcb_reload).drill).shape
        == C_footprint.C_pad.C_drill.E_shape.stadium
    )

    # empty center string ignored
    assert _effects(pcb).get_justifys() == [
        C_effects.C_justify.E_justify.center_horizontal,
        C_effects.C_justify.E_justify.top,
    ]


@pytest.mark.parametrize(
    ("parser", "path"),
    [
        (C_kicad_pcb_file, PCBFILE),
        (C_kicad_footprint_file, FPFILE),
        (C_kicad_netlist_file, NETFILE),
        (C_kicad_project_file, PRJFILE),
        (C_kicad_fp_lib_table_file, FPLIBFILE),
        (C_kicad_sch_file, SCHFILE),
        (C_kicad_sym_file, SYMFILE),
    ],
)
def test_dump_load_equality(parser: type[SEXP_File | JSON_File], path: Path):
    loaded = parser.loads(path)
    dump = loaded.dumps(Path("/tmp") / path.name if DUMP else None)
    loaded_dump = parser.loads(dump)
    dump2 = loaded_dump.dumps()
    assert dump == dump2


def test_sexp():
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


@pytest.mark.parametrize(
    "fp_path", _FP_DIR(5).glob("*.kicad_mod"), ids=lambda p: p.stem
)
def test_v5_fp_convert(fp_path: Path):
    fp = kicad_footprint_file(fp_path)
    assert fp.footprint.name.split(":")[-1] == fp_path.stem


@pytest.mark.parametrize(
    "fp_path", _FP_DIR(6).glob("*.kicad_mod"), ids=lambda p: p.stem
)
def test_v6_fp_convert(fp_path: Path):
    fp = kicad_footprint_file(fp_path)
    assert fp.footprint.name.split(":")[-1] == fp_path.stem
