from pathlib import Path

import pytest

from faebryk.exporters.schematic.kicad.transformer import Transformer
from faebryk.libs.kicad import fileformats_sch


@pytest.fixture
def symbol():
    return fileformats_sch.C_kicad_sch_file.C_kicad_sch.C_symbol_instance(
        lib_id="lib:abc",
        at=fileformats_sch.C_xyr(0, 0, 0),
        unit=1,
    )


def test_marking_in_program(symbol):
    old_contents = Transformer._get_hash_contents(symbol)

    assert not Transformer.check_mark(symbol)
    Transformer.mark(symbol)

    new_contents = Transformer._get_hash_contents(symbol)

    assert new_contents == old_contents
    assert Transformer.check_mark(symbol)


def test_marking_in_file(symbol, tmp_path):
    path = Path(tmp_path) / "test.kicad_sch"

    assert not Transformer.check_mark(symbol)

    sch = fileformats_sch.C_kicad_sch_file.skeleton()
    sch.kicad_sch.symbols.append(symbol)
    # prove this mutates the file properly
    Transformer.mark(symbol)
    sch.dumps(path)

    assert Transformer.check_mark(
        fileformats_sch.C_kicad_sch_file.loads(path).kicad_sch.symbols[0]
    )
