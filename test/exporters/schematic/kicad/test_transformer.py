from pathlib import Path

import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.exporters.schematic.kicad.transformer import Transformer
from faebryk.libs.exceptions import FaebrykException
from faebryk.libs.kicad.fileformats_common import C_effects, C_stroke, C_wh, C_xy, C_xyr
from faebryk.libs.kicad.fileformats_sch import (
    C_arc,
    C_circle,
    C_fill,
    C_kicad_sch_file,
    C_lib_symbol,
    C_polyline,
    C_pts,
    C_rect,
)
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
    assert transformer._symbol_files_index is None
    transformer.index_symbol_files(fp_lib_path_path, load_globals=False)
    assert transformer._symbol_files_index is not None
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


def test_get_bbox_arc():
    arc = C_arc(
        # Arcs are made CCW
        start=C_xy(2, 0),
        mid=C_xy(1, 1),
        end=C_xy(0, 0),
        stroke=C_stroke(width=0, type=C_stroke.E_type.default),
        fill=C_fill(type=C_fill.E_type.background),
    )
    bbox = Transformer.get_bbox(arc)
    assert len(bbox) == 2
    # Arc should span from (0,0) to (2,0), going up to (1,1)
    assert bbox[0] == (0, 0)
    assert bbox[1] == (2, 1)


def test_get_bbox_polyline():
    polyline = C_polyline(
        pts=C_pts(xys=[
            C_xy(0, 0),
            C_xy(1, 1),
            C_xy(2, 0),
        ]),
        stroke=C_stroke(width=0, type=C_stroke.E_type.default),
        fill=C_fill(type=C_fill.E_type.background),
    )
    bbox = Transformer.get_bbox(polyline)
    assert len(bbox) == 2
    assert bbox[0] == (0, 0)
    assert bbox[1] == (2, 1)


def test_get_bbox_rect():
    rect = C_rect(
        start=C_xy(1, 1),
        end=C_xy(3, 4),
        stroke=C_stroke(width=0, type=C_stroke.E_type.default),
        fill=C_fill(type=C_fill.E_type.background),
    )
    bbox = Transformer.get_bbox(rect)
    assert len(bbox) == 2
    assert bbox[0] == (1, 1)
    assert bbox[1] == (3, 4)


def test_get_bbox_circle():
    # Test with radius
    circle1 = C_circle(
        center=C_xy(0, 0),
        radius=2.0,
        stroke=C_stroke(width=0, type=C_stroke.E_type.default),
        fill=C_fill(type=C_fill.E_type.background),
    )
    bbox1 = Transformer.get_bbox(circle1)
    assert len(bbox1) == 2
    assert bbox1[0] == (-2, -2)
    assert bbox1[1] == (2, 2)

    # Test with end point
    circle2 = C_circle(
        center=C_xy(0, 0),
        end=C_xy(2, 0),
        stroke=C_stroke(width=0, type=C_stroke.E_type.default),
        fill=C_fill(type=C_fill.E_type.background),
    )
    bbox2 = Transformer.get_bbox(circle2)
    assert len(bbox2) == 2
    assert bbox2[0] == (-2, -2)
    assert bbox2[1] == (2, 2)


def test_get_bbox_pin():
    pin = C_lib_symbol.C_symbol.C_pin(
        at=C_xyr(x=1, y=1, r=0),
        length=2.0,
        type=C_lib_symbol.C_symbol.C_pin.E_type.input,
        style=C_lib_symbol.C_symbol.C_pin.E_style.line,
        name=C_lib_symbol.C_symbol.C_pin.C_name(
            name="",
            effects=C_effects(
                font=C_effects.C_font(size=C_wh(w=1.27, h=1.27), thickness=0.127),
                hide=False
            )
        ),
        number=C_lib_symbol.C_symbol.C_pin.C_number(
            number="",
            effects=C_effects(
                font=C_effects.C_font(size=C_wh(w=1.27, h=1.27), thickness=0.127),
                hide=False
            )
        )
    )
    bbox = Transformer.get_bbox(pin)
    assert len(bbox) == 2
    assert bbox[0] == (1, 1)
    assert bbox[1] == (3, 1)  # Pin extends by length in x direction


def test_get_bbox_symbol():
    symbol = C_lib_symbol.C_symbol(
        name="test_symbol",
        rectangles=[
            C_rect(
                start=C_xy(0, 0),
                end=C_xy(2, 2),
                stroke=C_stroke(width=0, type=C_stroke.E_type.default),
                fill=C_fill(type=C_fill.E_type.background),
            )
        ],
        pins=[
            C_lib_symbol.C_symbol.C_pin(
                at=C_xyr(x=0, y=0, r=0),
                length=1.0,
                type=C_lib_symbol.C_symbol.C_pin.E_type.input,
                style=C_lib_symbol.C_symbol.C_pin.E_style.line,
                name=C_lib_symbol.C_symbol.C_pin.C_name(
                    name="",
                    effects=C_effects(
                        font=C_effects.C_font(size=C_wh(w=1.27, h=1.27), thickness=0.127),
                        hide=False
                    )
                ),
                number=C_lib_symbol.C_symbol.C_pin.C_number(
                    number="",
                    effects=C_effects(
                        font=C_effects.C_font(size=C_wh(w=1.27, h=1.27), thickness=0.127),
                        hide=False
                    )
                )
            )
        ],
        polylines=[],
        circles=[],
        arcs=[]
    )
    bbox = Transformer.get_bbox(symbol)
    assert len(bbox) == 2
    assert bbox[0] == (0, 0)
    assert bbox[1] == (2, 2)


def test_get_bbox_lib_symbol():
    lib_symbol = C_lib_symbol(
        name="test_lib",
        symbols={
            "unit1": C_lib_symbol.C_symbol(
                name="unit1",
                rectangles=[
                    C_rect(
                        start=C_xy(0, 0),
                        end=C_xy(2, 2),
                        stroke=C_stroke(width=0, type=C_stroke.E_type.default),
                        fill=C_fill(type=C_fill.E_type.background),
                    )
                ],
                polylines=[],
                circles=[],
                arcs=[],
                pins=[]
            ),
            "unit2": C_lib_symbol.C_symbol(
                name="unit2",
                rectangles=[
                    C_rect(
                        start=C_xy(1, 1),
                        end=C_xy(3, 3),
                        stroke=C_stroke(width=0, type=C_stroke.E_type.default),
                        fill=C_fill(type=C_fill.E_type.background),
                    )
                ],
                polylines=[],
                circles=[],
                arcs=[],
                pins=[]
            ),
        },
        power=None,
        pin_numbers=None,
        pin_names=None,
        in_bom=None,
        on_board=None,
        convert=None,
        propertys={}
    )
    bbox = Transformer.get_bbox(lib_symbol)
    assert len(bbox) == 2
    assert bbox[0] == (0, 0)
    assert bbox[1] == (3, 3)


def test_get_bbox_empty_polyline():
    polyline = C_polyline(
        pts=C_pts(xys=[]),
        stroke=C_stroke(width=0, type=C_stroke.E_type.default),
        fill=C_fill(type=C_fill.E_type.background),
    )
    bbox = Transformer.get_bbox(polyline)
    assert bbox is None


def test_get_bbox_empty_symbol():
    symbol = C_lib_symbol.C_symbol(
        name="empty_symbol",
        rectangles=[],
        pins=[],
        polylines=[],
        circles=[],
        arcs=[]
    )
    bbox = Transformer.get_bbox(symbol)
    assert bbox is None
