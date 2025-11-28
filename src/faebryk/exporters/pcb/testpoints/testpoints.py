# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from collections import defaultdict
from pathlib import Path

import faebryk.library._F as F
from faebryk.core.graph import GraphFunctions
from faebryk.core.module import Module
from faebryk.exporters.pcb.kicad.transformer import (
    PCB_Transformer,
    Point2D,
    abs_pos2d,
)
from faebryk.libs.app.designators import attach_random_designators
from faebryk.libs.kicad.fileformats import kicad
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


def _get_testpoints(app: Module) -> list[F.TestPoint]:
    return [
        testpoint
        for testpoint in app.get_children_modules(
            types=F.TestPoint,
            include_root=True,
        )
        if testpoint.has_trait(F.has_footprint)
        and testpoint.get_trait(F.has_footprint)
        .get_footprint()
        .has_trait(F.has_kicad_footprint)
    ]


def export_testpoints(
    app: Module,
    testpoints_file: Path,
):
    """
    Get all testpoints from the application and export their information to a JSON file
    """
    testpoint_data: dict[str, dict] = {}
    testpoints = _get_testpoints(app)

    for testpoint in testpoints:
        designator = testpoint.get_trait(F.has_designator).get_designator()
        full_name = testpoint.get_full_name()
        fp = testpoint.get_trait(F.has_footprint).get_footprint()
        footprint = PCB_Transformer.get_fp(fp)  # get KiCad footprint
        position = footprint.at
        layer = footprint.layer
        library_name = footprint.name

        # Get single connected net name
        net = F.Net.find_named_net_for_mif(testpoint.contact)
        net_name = net.get_trait(F.has_overriden_name).get_name() if net else "no-net"

        testpoint_data[designator] = {
            "testpoint_name": full_name,
            "net_name": net_name,
            "footprint_name": library_name,
            "position": {"x": position.x, "y": position.y, "rotation": position.r},
            "layer": layer,
        }

    with open(testpoints_file, "w", encoding="utf-8") as f:
        json.dump(obj=testpoint_data, fp=f, indent=4)


class net_has_testpoint(Module.TraitT.decless()):
    def __init__(self, testpoint: F.TestPoint):
        super().__init__()
        self._testpoint = testpoint

    def get_testpoint(self) -> F.TestPoint:
        return self._testpoint


class GENERIC_TESTPOINT(F.TestPoint):
    removed: F.has_part_removed
    # TODO remove?
    attachable: F.can_attach_to_footprint_symmetrically
    is_atomic_part = L.f_field(F.is_atomic_part)(
        manufacturer="Generic",
        partnumber="TESTPOINT",
        footprint="TestPoint_THTPad_D1.0mm_Drill0.5mm.kicad_mod",
        symbol="CC0603KRX7R9BB562.kicad_sym",
        path=Path(__file__).parent / "GENERIC_TESTPOINT",
    )
    hidden_designator: F.has_hidden_designator


def decorate_nets_with_testpoints(app: Module):
    tps = app.get_children(
        direct_only=False,
        types=F.TestPoint,
        include_root=True,
    )
    logger.info(f"Found {len(tps)} pre-existing testpoints")
    for tp in tps:
        net = F.Net.find_named_net_for_mif(tp.contact)
        if net:
            net.add(net_has_testpoint(tp))

    nets = GraphFunctions(app.get_graph()).nodes_of_type(F.Net)
    logger.info(f"Found {len(nets)} nets")
    for net in nets:
        if net.has_trait(net_has_testpoint):
            continue
        netname = net.get_trait(F.has_overriden_name).get_name()
        tp = GENERIC_TESTPOINT()
        # wtf is going in here that i have to do this manually?
        tp.get_trait(F.is_atomic_part).on_obj_set()
        app.add(tp, name=f"TP_{netname}")
        tp.contact.connect(net.part_of)
        logger.info(f"Decorated net {netname} with testpoint {tp.get_full_name()}")
        net.add(net_has_testpoint(tp))

    # TODO remove, have to attach new designators because we just created the testpoints
    attach_random_designators(app.get_graph())


def position_testpoints(app: Module):
    nets = GraphFunctions(app.get_graph()).nodes_of_type(F.Net)
    for net in nets:
        if not (tp_trait := net.try_get_trait(net_has_testpoint)):
            continue
        tp = tp_trait.get_testpoint()
        if tp.has_trait(F.has_pcb_position) or tp.has_trait(
            PCB_Transformer.has_linked_kicad_footprint
        ):
            continue
        pos = set[Point2D]()
        pads = net.get_connected_pads()
        for pad in pads:
            if not pad.has_trait(PCB_Transformer.has_linked_kicad_pad):
                continue
            kfp, kpads = pad.get_trait(PCB_Transformer.has_linked_kicad_pad).get_pad()  # type: ignore
            for kpad in kpads:
                abs_pad_pos = abs_pos2d(kfp.at, kpad.at)  # type: ignore
                pos.add(abs_pad_pos)

        # TODO try to find cluster instead
        if not pos:
            continue
        tp_pos = next(iter(pos))
        target_pos = (
            tp_pos[0],
            tp_pos[1],
            0,
            F.has_pcb_position.layer_type.BOTTOM_LAYER,
        )
        tp.add(F.has_pcb_position_defined(target_pos))


def make_pogo_board(app: Module, pogo_board_file: Path):
    from atopile.config import BuildTargetPaths
    from faebryk.libs.kicad.fileformats import Property

    tps = app.get_children(
        direct_only=False,
        types=Module,
        include_root=True,
        # TODO
        f_filter=lambda m: type(m).__name__ == "GENERIC_TESTPOINT",
    )

    if not pogo_board_file.exists():
        pcb = BuildTargetPaths._boilerplate_layout()
    else:
        pcb = kicad.loads(kicad.pcb.PcbFile, pogo_board_file)

    # delete all pogos
    kicad.filter(
        pcb.kicad_pcb,
        "footprints",
        pcb.kicad_pcb.footprints,
        lambda fp: Property.try_get_property(fp.propertys, "__atopile_autoplaced__")
        is None,
    )
    if not tps:
        logger.warning("No testpoints found")
        return

    # delete all nets
    kicad.filter(
        pcb.kicad_pcb,
        "nets",
        pcb.kicad_pcb.nets,
        lambda net: True,
    )

    # add new pogos for each testpoint
    # - at same location as testpoint
    #   - on top layer but same x,y
    # - same net name as testpoint
    transformer = PCB_Transformer(
        pcb.kicad_pcb,
        None,
        None,
        noattach=True,
    )
    pogo_fp = Path(__file__).parent / "pogo_fp.kicad_mod"
    assert pogo_fp.exists(), f"Pogo footprint file not found: {pogo_fp}"

    lib_fp = kicad.loads(kicad.footprint.FootprintFile, pogo_fp)
    Property.set_property(
        lib_fp.footprint,
        kicad.pcb.Property(
            name="__atopile_autoplaced__",
            value="true",
            at=kicad.pcb.Xyr(x=0, y=0, r=0),
            layer="B.Cu",
            hide=True,
        ),  # type: ignore
    )

    logger.info("Adding pogos for testpoints")

    nets = defaultdict[kicad.pcb.Net, list[kicad.pcb.Footprint]](list)
    for tp in tps:
        fp = tp.get_trait(F.has_footprint).get_footprint()
        footprint = PCB_Transformer.get_fp(fp)  # get KiCad footprint
        position = footprint.at
        layer = footprint.layer
        if layer != "B.Cu":
            logger.warning(f"Testpoint {tp.get_full_name()} not on bottom layer")
            continue
        net = footprint.pads[0].net
        if not net:
            logger.warning(f"Testpoint {tp.get_full_name()} has no net")
            continue
        if not net.name:
            logger.warning(f"Testpoint {tp.get_full_name()} has no net name")
            continue
        reference_tp = Property.try_get_property(footprint.propertys, "Reference")
        if not reference_tp:
            logger.warning(f"Testpoint {tp.get_full_name()} has no reference")
            continue
        logger.info(f"Adding pogo for {tp.get_full_name()} at {position} layer {layer}")

        fp_out = transformer.insert_footprint(lib_fp.footprint, at=position)
        nets[net].append(fp_out)

        reference = Property.get_property_obj(fp_out.propertys, "Reference")
        reference.value = reference_tp

    for net, fps in nets.items():
        assert net.name
        kicad.insert(pcb.kicad_pcb, "nets", pcb.kicad_pcb.nets, net)
        for fp in fps:
            fp.pads[0].net = net

    kicad.dumps(pcb, pogo_board_file)
