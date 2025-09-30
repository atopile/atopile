# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from pathlib import Path

import pytest

import faebryk.library._F as F  # noqa: F401  # This is required to prevent a circular import
from faebryk.libs.kicad.fileformats import (
    C_kicad_project_file,
    Property,
    kicad,
)
from faebryk.libs.test.fileformats import (
    _FP_DIR,  # noqa: F401
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


def test_parser_netlist():
    netlist = kicad.loads(kicad.netlist.NetlistFile, NETFILE)
    assert [(c.ref, c.value) for c in netlist.netlist.components.comps][:10] == [
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


def test_parser_project():
    pro = C_kicad_project_file.loads(PRJFILE)
    assert pro.pcbnew.last_paths.netlist == "../../faebryk/faebryk.net"


def test_parser_schematics():
    sch = kicad.loads(kicad.schematic.SchematicFile, SCHFILE)
    assert kicad.get(sch.kicad_sch.lib_symbols.symbols, "power:GND").power
    assert not kicad.get(sch.kicad_sch.lib_symbols.symbols, "Device:R").power
    assert (
        Property.get_property(
            kicad.get(
                sch.kicad_sch.lib_symbols.symbols, "Amplifier_Audio:LM4990ITL"
            ).propertys,
            "Datasheet",
        )
        == "http://www.ti.com/lit/ds/symlink/lm4990.pdf"
    )

    # TODO remove
    print(kicad.dumps(sch))


def test_parser_symbols():
    sym = kicad.loads(kicad.symbol.SymbolFile, SYMFILE)
    assert (
        kicad.get(sym.kicad_sym.symbols, "AudioJack-CUI-SJ-3523-SMT").name
        == "AudioJack-CUI-SJ-3523-SMT"
    )


def test_parser_pcb_and_footprints():
    pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE)
    fp = kicad.loads(kicad.footprint.FootprintFile, FPFILE)

    assert [f.name for f in pcb.kicad_pcb.footprints] == [
        "logos:faebryk_logo",
        "lcsc:LED0603-RD-YELLOW",
        "lcsc:R0402",
        "lcsc:BAT-TH_BS-02-A1AJ010",
    ]

    assert not pcb.kicad_pcb.setup.pcbplotparams.usegerberextensions

    padtype = kicad.pcb.E_pad_type
    assert [(p.name, p.type) for p in fp.footprint.pads] == [
        ("", padtype.SMD),
        ("", padtype.SMD),
        ("1", padtype.SMD),
        ("2", padtype.SMD),
    ]

    logo_fp = kicad.get(pcb.kicad_pcb.footprints, "logos:faebryk_logo")
    assert kicad.pcb.E_Attr.EXCLUDE_FROM_BOM in logo_fp.attr


def test_write():
    pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE)

    def _d1(pcb: kicad.pcb.PcbFile):
        return find(
            pcb.kicad_pcb.footprints,
            lambda f: Property.get_property(f.propertys, "Reference") == "D1",
        )

    led_p = Property.get_property_obj(_d1(pcb).propertys, "Value")
    assert led_p.value == "LED"
    led_p.value = "LED2"

    pcb_reload = kicad.loads(kicad.pcb.PcbFile, kicad.dumps(pcb))
    assert Property.get_property_obj(_d1(pcb_reload).propertys, "Value").value == "LED2"


def test_empty_enum_positional():
    pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE)

    def _b1_p1(pcb: kicad.pcb.PcbFile):
        return find(
            find(
                pcb.kicad_pcb.footprints,
                lambda f: Property.get_property(f.propertys, "Reference") == "B1",
            ).pads,
            lambda p: p.name == "1",
        )

    _b1_p1(pcb).drill = kicad.pcb.PadDrill(
        shape=kicad.pcb.E_pad_drill_shape.OVAL,
        size_x=0.5,
        size_y=0.4,
        offset=None,
    )

    def _effects(pcb: kicad.pcb.PcbFile):
        return not_none(
            Property.get_property_obj(
                kicad.get(pcb.kicad_pcb.footprints, "logos:faebryk_logo").propertys,
                "Datasheet",
            ).effects
        )

    _effects(pcb).justify = kicad.pcb.Justify(
        justify1=None, justify2=None, justify3=None
    )
    not_none(_effects(pcb).justify).justify1 = kicad.pcb.E_justify.TOP

    pcb_reload = kicad.loads(kicad.pcb.PcbFile, kicad.dumps(pcb))

    assert not_none(_b1_p1(pcb_reload).drill).shape == kicad.pcb.E_pad_drill_shape.OVAL

    # empty center string ignored
    # Check that justifys were added correctly
    assert not_none(_effects(pcb).justify).justify1 == kicad.pcb.E_justify.TOP


@pytest.mark.parametrize(
    ("parser", "path"),
    [
        (kicad.pcb.PcbFile, PCBFILE),
        (kicad.footprint.FootprintFile, FPFILE),
        (kicad.netlist.NetlistFile, NETFILE),
        (kicad.project.ProjectFile, PRJFILE),
        (kicad.fp_lib_table.FpLibTableFile, FPLIBFILE),
        (kicad.schematic.SchematicFile, SCHFILE),
        (kicad.symbol.SymbolFile, SYMFILE),
    ],
)
def test_dump_load_equality(parser: type[kicad.types], path: Path):
    loaded = kicad.loads(parser, path)
    dump = kicad.dumps(loaded, Path("/tmp") / path.name if DUMP else None)
    loaded_dump = kicad.loads(parser, dump)
    dump2 = kicad.dumps(
        loaded_dump, Path("/tmp") / (path.name + ".dump") if DUMP else None
    )
    assert dump == dump2


@pytest.mark.parametrize(
    ("parser", "path"),
    [
        (kicad.pcb.PcbFile, PCBFILE),
        (kicad.footprint.FootprintFile, FPFILE),
    ],
)
def test_kicad_equal_format(parser: type[kicad.types], path: Path):
    raw = path.read_text()
    loaded = kicad.loads(parser, raw)
    dump = kicad.dumps(loaded, Path("/tmp") / path.name if DUMP else None)
    assert raw == dump


def test_embedded():
    data = (
        "(kicad_pcb"
        "    (version 20241229)"
        "    (generator test_atopile)"
        "    (generator_version latest)"
        "    (embedded_files"
        "       (file"
        '           (name "TCA9548APWR.kicad_sym")'
        "           (type other)"
        "           (data |KLUv/WCvPs0aACZjbCEA0zzzfQvw6FfUhoV7zwkZml8H6u0W2CGvs/b+/6/+twJfAGYAYAAObZxD"  # noqa: E501
        "               yaFx2w/DxyoZmF75rlPl4JXc3R+RR2/x6w+/Eflm679kfZHc3d3doagRYQy2CwsMOEfkUWWjJV/D"  # noqa: E501
        "               yHXeVT/+ieTuDk3Tcb6j/ozk7g5JrviJWWLZjB9Y7a1IART5IRzfyCEoeyc5ARBv3Q9S22JAgCVb"  # noqa: E501
        "               aUcrAgCC8bI35Z8y1l278TcBTE5KE4TMS1BYJisGdckrQm1SS3wXpRgLz3MIMlpV1uQijza++rJz"  # noqa: E501
        "               NlAzeoxYIRM0ZewPXoo0aVROf84dpZisJxVbJRStpDY9m7KalG9dX5zguu3r6XHGonjDynUWs90i"  # noqa: E501
        "               poYP+l82e6qcssGr+UrWe5wYiB/TJDY9sMmNcv0bv33R6mvnV32grlmyZMmHr5bJDNOV4ZzHJawp"  # noqa: E501
        "               L0u07BM0XZTjIHTQ0QRHB5TTuizDMO7aZqc4UJxXTavzAhy10U7jqGx2GDc3aV2dh1kyszyOgldo"  # noqa: E501
        "               dD50WpecM3L9EgsmqgaRv6XiC5PUKXuCX5S0gLSma5JWfEUH/4bX/mXEGMf3AuKAmKBxvUMkI7MF"  # noqa: E501
        "               RaksB2CGyJAMEXeFAa4pQQal4Eipik5DNTKpzqJJVHjaVCM7tdOvgDbEp1FVmQhT8GkV0AaiqpSJ"  # noqa: E501
        "               qspeugUi1KKiDMoWoUAbBKihUmZKTO6NMkB4mlTLRRWStChGEJwWlTIoSSTk1rcBItOkWi5VFAlJ"  # noqa: E501
        "               ajaCsDSpmEvJEcqZvQFC0qZaNhVv9k9FxgExaaRWuSgWjZGwgLSoNxsRpZxoJV0gxFRBNhQx31IW"  # noqa: E501
        "               pbpcKWa0SlWgCvmoKxYSFqguH8WILFVxVchRz8ctaxVWL4PqD+GpCqgpIxtquPMKVj0ZyagthJfj"  # noqa: E501
        "               r1VYjQw1f+cPGalR10ChTvresEJU9OXLjQLEpx+xCXHglqVAibcltepsEqsSStOjsaOiNvOWHg5G"  # noqa: E501
        "               V6c/0F0aOmouAi+ywtzqa8sQGap9mMJdrKy3SwekXiYUk56peJepoJu+GM0OSHl/ombFd/pwZOOk"  # noqa: E501
        "               Tl3FyynP6mQeT1GLGX9FSA24ETWdXAp/hzgeDkegljsUTt+G2Tyc7Bloulah7IHoXIAwuSQSnXSb"  # noqa: E501
        "               p1lOLwTtiwntzFQB|"
        "           )"
        '           (checksum "93211F8E59511F34A759EE478AABDE93")'
        "       )"
        "    )"
        ")"
    )
    from faebryk.libs.kicad.fileformats import kicad

    pcb = kicad.loads(kicad.pcb.PcbFile, data)

    s_data = not_none(
        kicad.get(
            not_none(pcb.kicad_pcb.embedded_files).files, "TCA9548APWR.kicad_sym"
        ).data
    )
    text = kicad.decompress(s_data).decode("utf-8")

    assert 'symbol "TCA9548APWR"' in text

    encoded = kicad.dumps(pcb)

    sexp2 = kicad.loads(kicad.pcb.PcbFile, encoded)
    assert (
        kicad.decompress(
            not_none(
                kicad.get(
                    not_none(sexp2.kicad_pcb.embedded_files).files,
                    "TCA9548APWR.kicad_sym",
                ).data
            )
        ).decode("utf-8")
        == text
    )


def test_list_single():
    sexp = """
    (footprint "test"
        (version 20241229)
        (generator "pcbnew")
        (generator_version "9.0")
        (layer "F.Cu")
        (tags "LED")
    )
    """
    from faebryk.libs.kicad.fileformats import kicad

    fp = kicad.loads(kicad.footprint.FootprintFile, sexp)
    assert fp.footprint.tags == ["LED"]
    dumped = kicad.dumps(fp)
    assert '(tags "LED")' in dumped


def test_list_multi():
    sexp = """
    (footprint "test"
        (version 20241229)
        (generator "pcbnew")
        (generator_version "9.0")
        (layer "F.Cu")
        (tags "LED" "LED2")
    )
    """
    from faebryk.libs.kicad.fileformats import kicad

    fp = kicad.loads(kicad.footprint.FootprintFile, sexp)
    assert fp.footprint.tags == ["LED", "LED2"]
    dumped = kicad.dumps(fp)
    assert '(tags "LED" "LED2")' in dumped


def test_list_empty():
    sexp = """
    (footprint "test"
        (version 20241229)
        (generator "pcbnew")
        (generator_version "9.0")
        (layer "F.Cu")
        (tags)
    )
    """
    from faebryk.libs.kicad.fileformats import kicad

    fp = kicad.loads(kicad.footprint.FootprintFile, sexp)
    assert fp.footprint.tags == []
    dumped = kicad.dumps(fp)
    assert "tags" not in dumped


def test_list_none():
    sexp = """
    (footprint "test"
        (version 20241229)
        (generator "pcbnew")
        (generator_version "9.0")
        (layer "F.Cu")
    )
    """
    from faebryk.libs.kicad.fileformats import kicad

    fp = kicad.loads(kicad.footprint.FootprintFile, sexp)
    assert fp.footprint.tags == []
    dumped = kicad.dumps(fp)
    assert "tags" not in dumped


def test_list_struct_positional():
    sexp = """
    (kicad_pcb
        (generator "test_atopile")
        (generator_version "latest")
        (layers
            (0 "F.Cu" signal)
            (1 "B.Cu" signal)
        )
    )
    """
    from faebryk.libs.kicad.fileformats import kicad

    pcb = kicad.loads(kicad.pcb.PcbFile, sexp)
    assert len(pcb.kicad_pcb.layers) == 2
    assert pcb.kicad_pcb.layers[0].name == "F.Cu"
    assert pcb.kicad_pcb.layers[1].name == "B.Cu"
    assert pcb.kicad_pcb.layers[0].type == kicad.pcb.E_layer_type.SIGNAL
    assert pcb.kicad_pcb.layers[1].type == kicad.pcb.E_layer_type.SIGNAL

    dumped = kicad.dumps(pcb)
    dumped = re.sub(
        r"\(\s\(",
        "((",
        re.sub(
            r"\)\s\)",
            "))",
            re.sub(r"\s+", " ", dumped.replace("\n", "")),
        ),
    )
    assert '(layers (0 "F.Cu" signal) (1 "B.Cu" signal))' in dumped


def test_multidict_single():
    sexp = """
    (export (version "E")
        (libparts
            (libpart (lib "Connector") (part "TestPoint")
                (pins
                    (pin (num "1") (name "1") (type "passive"))
                )
            )
        )
    )
    """
    from faebryk.libs.kicad.fileformats import kicad

    netlist = kicad.loads(kicad.netlist.NetlistFile, sexp)
    assert not_none(netlist.netlist.libparts.libparts[0].pins).pin[0].num == "1"


def test_multidict_multi():
    sexp = """
    (export (version "E")
        (libparts
            (libpart (lib "Connector") (part "TestPoint")
                (pins
                    (pin (num "1") (name "1") (type "passive"))
                    (pin (num "2") (name "2") (type "passive"))
                )
            )
        )
    )
    """
    from faebryk.libs.kicad.fileformats import kicad

    netlist = kicad.loads(kicad.netlist.NetlistFile, sexp)
    assert not_none(netlist.netlist.libparts.libparts[0].pins).pin[0].num == "1"
    assert not_none(netlist.netlist.libparts.libparts[0].pins).pin[1].num == "2"


# def test_multidict_empty():
#    sexp = """
#    (export (version "E")
#        (libparts
#            (libpart (lib "Connector") (part "TestPoint")
#                (pins
#                )
#            )
#        )
#    )
#    """
#    from faebryk.libs.kicad.fileformats import kicad
#
#    netlist = kicad.loads(kicad.netlist.NetlistFile, sexp)
#    assert len(not_none(netlist.netlist.libparts.libparts[0].pins).pin) == 0


def test_multidict_none():
    sexp = """
   (export (version "E")
       (libparts
           (libpart (lib "Connector") (part "TestPoint")
           )
       )
   )
   """
    from faebryk.libs.kicad.fileformats import kicad

    netlist = kicad.loads(kicad.netlist.NetlistFile, sexp)
    assert netlist.netlist.libparts.libparts[0].pins is None


def test_string_escape():
    test_string = 'foo"bar'

    pcb = kicad.pcb.PcbFile(
        kicad_pcb=kicad.pcb.KicadPcb(
            version=0,
            generator="faebryk",
            generator_version=test_string,
        )  # type: ignore
    )

    sexp = kicad.dumps(pcb)
    pcb_load = kicad.loads(kicad.pcb.PcbFile, sexp)

    assert pcb_load.kicad_pcb.generator_version == test_string


def test_mutable_list():
    sexp = """
    (fp_lib_table
        (version 7)
        (lib (name "test0") (type "KiCad") (uri "test") (options "") (descr "test0"))
        (lib (name "test1") (type "KiCad") (uri "test") (options "") (descr "test1"))
    )
    """
    from faebryk.libs.kicad.fileformats import kicad

    def _ids(fp_lib_table: kicad.fp_lib_table.FpLibTableFile):
        return [lib.__zig_address__() for lib in fp_lib_table.fp_lib_table.libs]

    fp_lib_table = kicad.loads(kicad.fp_lib_table.FpLibTableFile, sexp)
    # len
    assert len(fp_lib_table.fp_lib_table.libs) == 2

    # index
    assert fp_lib_table.fp_lib_table.libs[0].name == "test0"
    assert fp_lib_table.fp_lib_table.libs[1].name == "test1"

    # for later
    ids = _ids(fp_lib_table)

    # iter
    for i, lib in enumerate(fp_lib_table.fp_lib_table.libs):
        assert lib.name == f"test{i}"

    # append
    fp_lib_table.fp_lib_table.libs.append(
        kicad.fp_lib_table.FpLibEntry(
            name="test2",
            type="KiCad",
            uri="test",
            options="",
            descr="test2",
        )
    )
    assert len(fp_lib_table.fp_lib_table.libs) == 3
    assert fp_lib_table.fp_lib_table.libs[2].name == "test2"

    new_ids = _ids(fp_lib_table)
    assert new_ids[:2] == ids, f"references have gone bad {new_ids} != {ids}"

    # remove
    fp_lib_table.fp_lib_table.libs.remove(fp_lib_table.fp_lib_table.libs[0])
    assert len(fp_lib_table.fp_lib_table.libs) == 2
    assert fp_lib_table.fp_lib_table.libs[0].name == "test1"
    assert fp_lib_table.fp_lib_table.libs[1].name == "test2"

    # check that original refs are still valid
    assert _ids(fp_lib_table)[0] == ids[1]

    # clear
    fp_lib_table.fp_lib_table.libs.clear()
    assert len(fp_lib_table.fp_lib_table.libs) == 0
