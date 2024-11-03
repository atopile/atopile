from pathlib import Path

import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.exporters.schematic.kicad.transformer import Transformer
from faebryk.libs.exceptions import FaebrykException
from faebryk.libs.kicad.fileformats_sch import C_kicad_sch_file
from faebryk.libs.util import find


@pytest.fixture
def test_dir():
    return find(
        Path(__file__).parents,
        lambda p: p.name == "test" and (p / "common/resources").is_dir(),
    )


@pytest.fixture
def fp_lib_path_path(test_dir: Path):
    return test_dir / "common/resources/fp-lib-table"


@pytest.fixture
def sch_file(test_dir: Path):
    return C_kicad_sch_file.loads(test_dir / "common/resources/test.kicad_sch")


@pytest.fixture
def transformer(sch_file: C_kicad_sch_file):
    app = Module()
    return Transformer(sch_file.kicad_sch, app.get_graph(), app)


def test_wire_transformer(transformer: Transformer):
    start_wire_count = len(transformer.sch.wires)

    transformer.insert_wire(
        [
            (0, 0),
            (1, 0),
            (1, 1),
        ]
    )

    # 2 because we have 3 waypoints
    assert len(transformer.sch.wires) == start_wire_count + 2
    assert [(pt.x, pt.y) for pt in transformer.sch.wires[-2].pts.xys] == [
        (0, 0),
        (1, 0),
    ]


def test_index_symbol_files(transformer: Transformer, fp_lib_path_path: Path):
    assert len(transformer._symbol_files_index) == 0
    transformer.index_symbol_files(fp_lib_path_path, load_globals=False)
    assert len(transformer._symbol_files_index) == 1


@pytest.fixture
def full_transformer(transformer: Transformer, fp_lib_path_path: Path):
    transformer.index_symbol_files(fp_lib_path_path, load_globals=False)
    return transformer


def test_get_symbol_file(full_transformer: Transformer):
    with pytest.raises(FaebrykException):
        full_transformer.get_symbol_file("notta-lib")

    sym_flie = full_transformer.get_symbol_file("test")
    assert (
        sym_flie.kicad_symbol_lib.symbols["AudioJack-CUI-SJ-3523-SMT"].name
        == "AudioJack-CUI-SJ-3523-SMT"
    )


def test_insert_symbol(full_transformer: Transformer, sch_file: C_kicad_sch_file):
    start_symbol_count = len(full_transformer.sch.symbols)

    # mimicing typically design/user-space
    audio_jack = full_transformer.app.add(Module())
    pin_s = audio_jack.add(F.Electrical())
    pin_t = audio_jack.add(F.Electrical())
    pin_r = audio_jack.add(F.Electrical())
    audio_jack.add(F.has_overriden_name_defined("U1"))

    # mimicing typically lcsc code
    sym = F.Symbol.with_component(
        audio_jack,
        {
            "S": pin_s,
            "T": pin_t,
            "R": pin_r,
        },
    )
    audio_jack.add(F.Symbol.has_symbol(sym))
    sym.add(F.Symbol.has_kicad_symbol("test:AudioJack-CUI-SJ-3523-SMT"))

    full_transformer.insert_symbol(audio_jack)

    assert len(full_transformer.sch.symbols) == start_symbol_count + 1
    assert full_transformer.sch.symbols[-1].propertys["Reference"].value == "U1"
