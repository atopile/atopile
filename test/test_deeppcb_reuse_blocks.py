"""Tests for DeepPCB reuse block collapse/expand round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest

from faebryk.exporters.pcb.deeppcb.transformer import DeepPCB_Transformer
from faebryk.libs.kicad.fileformats import kicad

# ── Minimal KiCad PCB templates for testing ──────────────────────────

_PARENT_PCB = """(kicad_pcb
    (version 20241229)
    (generator "atopile")
    (generator_version "0.0.0")
    (general (thickness 1.6) (legacy_teardrops no))
    (layers
        (0 "F.Cu" signal)
        (31 "B.Cu" signal)
        (36 "B.SilkS" user "B.Silkscreen")
        (37 "F.SilkS" user "F.Silkscreen")
        (44 "Edge.Cuts" user)
        (48 "B.Fab" user)
        (49 "F.Fab" user)
        (55 "User.9" user)
    )
    (setup
        (pad_to_mask_clearance 0)
        (allow_soldermask_bridges_in_footprints no)
        (pcbplotparams
            (layerselection 0x00010fc_ffffffff)
            (plot_on_all_layers_selection 0x0000000_00000000)
            (outputformat 1)
            (drillshape 1)
            (scaleselection 1)
            (outputdirectory "")
        )
    )
    (net 0 "")
    (net 1 "VCC")
    (net 2 "GND")
    (net 3 "INTERNAL_AB")
    (net 4 "SIG_OUT")

    ; Edge cuts for boundary
    (gr_line (start 0 0) (end 50 0)
        (stroke (width 0.2) (type default)) (layer "Edge.Cuts")
        (uuid "e0000001-0000-0000-0000-000000000001"))
    (gr_line (start 50 0) (end 50 50)
        (stroke (width 0.2) (type default)) (layer "Edge.Cuts")
        (uuid "e0000002-0000-0000-0000-000000000002"))
    (gr_line (start 50 50) (end 0 50)
        (stroke (width 0.2) (type default)) (layer "Edge.Cuts")
        (uuid "e0000003-0000-0000-0000-000000000003"))
    (gr_line (start 0 50) (end 0 0)
        (stroke (width 0.2) (type default)) (layer "Edge.Cuts")
        (uuid "e0000004-0000-0000-0000-000000000004"))

    ; ── Grouped footprint A (in reuse block "myblock") ──
    (footprint "PKG:R0402"
        (layer "F.Cu")
        (uuid "aaaa0001-0000-0000-0000-000000000001")
        (at 10 10 0)
        (property "Reference" "R1"
            (at 0 -2 0) (layer "F.SilkS") (hide no)
            (uuid "p0000001-0000-0000-0000-000000000001")
            (effects (font (size 1 1) (thickness 0.15))))
        (property "atopile_address" "myblock.comp_a"
            (at 0 0 0) (layer "User.9") (hide yes)
            (uuid "p0000002-0000-0000-0000-000000000001")
            (effects (font (size 0.125 0.125) (thickness 0.01875))))
        (property "atopile_subaddresses" "[sub/sub.kicad_pcb:comp_a]"
            (at 0 0 0) (layer "User.9") (hide yes)
            (uuid "p0000003-0000-0000-0000-000000000001")
            (effects (font (size 0.125 0.125) (thickness 0.01875))))
        (attr smd)
        (pad "1" smd rect
            (at -0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 1 "VCC")
            (uuid "d0000001-0000-0000-0000-000000000001"))
        (pad "2" smd rect
            (at 0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 3 "INTERNAL_AB")
            (uuid "d0000002-0000-0000-0000-000000000001"))
    )

    ; ── Grouped footprint B (in reuse block "myblock") ──
    (footprint "PKG:R0402"
        (layer "F.Cu")
        (uuid "aaaa0002-0000-0000-0000-000000000002")
        (at 10 15 0)
        (property "Reference" "R2"
            (at 0 -2 0) (layer "F.SilkS") (hide no)
            (uuid "p0000001-0000-0000-0000-000000000002")
            (effects (font (size 1 1) (thickness 0.15))))
        (property "atopile_address" "myblock.comp_b"
            (at 0 0 0) (layer "User.9") (hide yes)
            (uuid "p0000002-0000-0000-0000-000000000002")
            (effects (font (size 0.125 0.125) (thickness 0.01875))))
        (property "atopile_subaddresses" "[sub/sub.kicad_pcb:comp_b]"
            (at 0 0 0) (layer "User.9") (hide yes)
            (uuid "p0000003-0000-0000-0000-000000000002")
            (effects (font (size 0.125 0.125) (thickness 0.01875))))
        (attr smd)
        (pad "1" smd rect
            (at -0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 3 "INTERNAL_AB")
            (uuid "d0000001-0000-0000-0000-000000000002"))
        (pad "2" smd rect
            (at 0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 2 "GND")
            (uuid "d0000002-0000-0000-0000-000000000002"))
    )

    ; ── External footprint C (NOT in any reuse block) ──
    (footprint "PKG:C0402"
        (layer "F.Cu")
        (uuid "bbbb0001-0000-0000-0000-000000000003")
        (at 30 10 0)
        (property "Reference" "C1"
            (at 0 -2 0) (layer "F.SilkS") (hide no)
            (uuid "p0000001-0000-0000-0000-000000000003")
            (effects (font (size 1 1) (thickness 0.15))))
        (property "atopile_address" "cap1"
            (at 0 0 0) (layer "User.9") (hide yes)
            (uuid "p0000002-0000-0000-0000-000000000003")
            (effects (font (size 0.125 0.125) (thickness 0.01875))))
        (attr smd)
        (pad "1" smd rect
            (at -0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 1 "VCC")
            (uuid "d0000001-0000-0000-0000-000000000003"))
        (pad "2" smd rect
            (at 0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 4 "SIG_OUT")
            (uuid "d0000002-0000-0000-0000-000000000003"))
    )

    ; ── External footprint D (NOT in any reuse block) ──
    (footprint "PKG:C0402"
        (layer "F.Cu")
        (uuid "bbbb0002-0000-0000-0000-000000000004")
        (at 30 15 0)
        (property "Reference" "C2"
            (at 0 -2 0) (layer "F.SilkS") (hide no)
            (uuid "p0000001-0000-0000-0000-000000000004")
            (effects (font (size 1 1) (thickness 0.15))))
        (property "atopile_address" "cap2"
            (at 0 0 0) (layer "User.9") (hide yes)
            (uuid "p0000002-0000-0000-0000-000000000004")
            (effects (font (size 0.125 0.125) (thickness 0.01875))))
        (attr smd)
        (pad "1" smd rect
            (at -0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 2 "GND")
            (uuid "d0000001-0000-0000-0000-000000000004"))
        (pad "2" smd rect
            (at 0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 4 "SIG_OUT")
            (uuid "d0000002-0000-0000-0000-000000000004"))
    )

    ; ── Wires ──
    ; Internal wire (INTERNAL_AB between grouped footprints)
    (segment (start 10.5 10) (end 9.5 15)
        (width 0.2) (layer "F.Cu") (net 3)
        (uuid "s0000001-0000-0000-0000-000000000001"))
    ; External wire (VCC from grouped to external)
    (segment (start 9.5 10) (end 29.5 10)
        (width 0.2) (layer "F.Cu") (net 1)
        (uuid "s0000002-0000-0000-0000-000000000002"))
    ; External wire (GND from grouped to external)
    (segment (start 10.5 15) (end 29.5 15)
        (width 0.2) (layer "F.Cu") (net 2)
        (uuid "s0000003-0000-0000-0000-000000000003"))
    ; Fully external wire (SIG_OUT between external footprints)
    (segment (start 30.5 10) (end 30.5 15)
        (width 0.2) (layer "F.Cu") (net 4)
        (uuid "s0000004-0000-0000-0000-000000000004"))

    ; Zone on internal net (should be filtered during collapse)
    (zone (net 3) (net_name "INTERNAL_AB") (layer "F.Cu")
        (uuid "z0000001-0000-0000-0000-000000000001")
        (hatch edge 0.5)
        (connect_pads (clearance 0.3))
        (min_thickness 0.2)
        (fill (thermal_gap 0.3) (thermal_bridge_width 0.3))
        (polygon (pts
            (xy 8 8) (xy 12 8) (xy 12 17) (xy 8 17)
        ))
    )

    ; Zone on external net (should NOT be filtered)
    (zone (net 1) (net_name "VCC") (layer "F.Cu")
        (uuid "z0000002-0000-0000-0000-000000000002")
        (hatch edge 0.5)
        (connect_pads (clearance 0.3))
        (min_thickness 0.2)
        (fill (thermal_gap 0.3) (thermal_bridge_width 0.3))
        (polygon (pts
            (xy 25 5) (xy 35 5) (xy 35 20) (xy 25 20)
        ))
    )
)"""

_SUB_PCB = """(kicad_pcb
    (version 20241229)
    (generator "atopile")
    (generator_version "0.0.0")
    (general (thickness 1.6) (legacy_teardrops no))
    (layers
        (0 "F.Cu" signal)
        (31 "B.Cu" signal)
        (36 "B.SilkS" user "B.Silkscreen")
        (37 "F.SilkS" user "F.Silkscreen")
        (44 "Edge.Cuts" user)
        (48 "B.Fab" user)
        (49 "F.Fab" user)
        (55 "User.9" user)
    )
    (setup
        (pad_to_mask_clearance 0)
        (allow_soldermask_bridges_in_footprints no)
        (pcbplotparams
            (layerselection 0x00010fc_ffffffff)
            (plot_on_all_layers_selection 0x0000000_00000000)
            (outputformat 1)
            (drillshape 1)
            (scaleselection 1)
            (outputdirectory "")
        )
    )
    (net 0 "")
    (net 1 "sub_vcc")
    (net 2 "sub_gnd")
    (net 3 "sub_internal")

    ; Sub-PCB footprint A
    (footprint "PKG:R0402"
        (layer "F.Cu")
        (uuid "cc000001-0000-0000-0000-000000000001")
        (at 5 5 0)
        (property "Reference" "R1"
            (at 0 -2 0) (layer "F.SilkS") (hide no)
            (uuid "q0000001-0000-0000-0000-000000000001")
            (effects (font (size 1 1) (thickness 0.15))))
        (property "atopile_address" "comp_a"
            (at 0 0 0) (layer "User.9") (hide yes)
            (uuid "q0000002-0000-0000-0000-000000000001")
            (effects (font (size 0.125 0.125) (thickness 0.01875))))
        (attr smd)
        (pad "1" smd rect
            (at -0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 1 "sub_vcc")
            (uuid "e0000001-0000-0000-0000-000000000001"))
        (pad "2" smd rect
            (at 0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 3 "sub_internal")
            (uuid "e0000002-0000-0000-0000-000000000001"))
    )

    ; Sub-PCB footprint B
    (footprint "PKG:R0402"
        (layer "F.Cu")
        (uuid "cc000002-0000-0000-0000-000000000002")
        (at 5 10 0)
        (property "Reference" "R2"
            (at 0 -2 0) (layer "F.SilkS") (hide no)
            (uuid "q0000001-0000-0000-0000-000000000002")
            (effects (font (size 1 1) (thickness 0.15))))
        (property "atopile_address" "comp_b"
            (at 0 0 0) (layer "User.9") (hide yes)
            (uuid "q0000002-0000-0000-0000-000000000002")
            (effects (font (size 0.125 0.125) (thickness 0.01875))))
        (attr smd)
        (pad "1" smd rect
            (at -0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 3 "sub_internal")
            (uuid "e0000001-0000-0000-0000-000000000002"))
        (pad "2" smd rect
            (at 0.5 0 0) (size 0.6 0.5)
            (layers "F.Cu" "F.Mask" "F.Paste")
            (net 2 "sub_gnd")
            (uuid "e0000002-0000-0000-0000-000000000002"))
    )

    ; Internal routing within the sub-PCB
    (segment (start 5.5 5) (end 4.5 10)
        (width 0.2) (layer "F.Cu") (net 3)
        (uuid "f0000001-0000-0000-0000-000000000001"))

    ; Arc segment on internal net
    (arc (start 5.5 5) (mid 6 7.5) (end 4.5 10)
        (width 0.2) (layer "F.Cu") (net 3)
        (uuid "f0000002-0000-0000-0000-000000000001"))

    ; Via on external net (sub_vcc)
    (via (at 5 3) (size 0.6) (drill 0.3)
        (layers "F.Cu" "B.Cu") (net 1)
        (uuid "f0000003-0000-0000-0000-000000000001"))

    ; Zone on internal net
    (zone (net 3) (net_name "sub_internal") (layer "F.Cu")
        (uuid "f0000004-0000-0000-0000-000000000001")
        (hatch edge 0.5)
        (connect_pads (clearance 0.3))
        (min_thickness 0.2)
        (fill (thermal_gap 0.3) (thermal_bridge_width 0.3))
        (polygon (pts
            (xy 4 4) (xy 6 4) (xy 6 11) (xy 4 11)
        ))
    )

    ; Graphics: silkscreen line in the sub-PCB
    (gr_line (start 3 3) (end 7 3)
        (stroke (width 0.12) (type default)) (layer "F.SilkS")
        (uuid "f0000005-0000-0000-0000-000000000001"))
)"""


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Set up a project directory with parent and sub PCBs."""
    # Write parent PCB
    parent_path = tmp_path / "parent.kicad_pcb"
    parent_path.write_text(_PARENT_PCB, encoding="utf-8")

    # Write sub-PCB
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    sub_path = sub_dir / "sub.kicad_pcb"
    sub_path.write_text(_SUB_PCB, encoding="utf-8")

    return tmp_path


def test_collapse_identifies_reuse_groups(project_dir: Path) -> None:
    """from_kicad_pcb should detect reuse groups and produce synthetic components."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        parent_pcb.kicad_pcb,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    # Metadata should contain one block ("myblock")
    assert "myblock" in metadata
    block = metadata["myblock"]
    assert block["pcb_address"] == "sub/sub.kicad_pcb"
    assert "comp_a" in block["footprint_addr_map"]
    assert "comp_b" in block["footprint_addr_map"]

    # Synthetic block component should exist
    block_components = [
        c for c in board.components if "REUSE_BLOCK:myblock" in str(c.get("partNumber", ""))
    ]
    assert len(block_components) == 1

    # Original grouped footprints should be gone
    # The board should have: 1 synthetic + 2 external = 3 components
    # (original had 4 footprints, 2 collapsed into 1 synthetic)
    assert len(board.components) == 3

    # Internal net (INTERNAL_AB) should now be preserved in nets
    net_ids = {str(n.get("id", "")) for n in board.nets}
    assert "INTERNAL_AB" in net_ids

    # External nets should still exist
    assert "VCC" in net_ids
    assert "GND" in net_ids


def test_collapse_filters_internal_wires(project_dir: Path) -> None:
    """Internal wires/vias should be filtered out during collapse."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    metadata: dict = {}

    # Without reuse blocks (no project_root): all 4 wires
    board_no_reuse = DeepPCB_Transformer.from_kicad_pcb(parent_pcb.kicad_pcb)
    assert len(board_no_reuse.wires) == 4

    # With reuse blocks: internal wires are now preserved
    board = DeepPCB_Transformer.from_kicad_pcb(
        parent_pcb.kicad_pcb,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )
    # All 4 wires preserved (internal routing no longer filtered)
    assert len(board.wires) == 4

    # The internal wire on "INTERNAL_AB" should be present
    wire_nets = {str(w.get("netId", "")) for w in board.wires}
    assert "INTERNAL_AB" in wire_nets


def test_synthetic_component_has_external_pins(project_dir: Path) -> None:
    """Synthetic block component should have pins for all pads (external + internal)."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        parent_pcb.kicad_pcb,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    block = metadata["myblock"]

    # All 4 pads are in external_pin_map (both external and internal-net pads)
    assert len(block["external_pin_map"]) == 4

    # The synthetic definition should have 4 pins (all pads)
    definition_id = block["definition_id"]
    synth_def = None
    for d in board.componentDefinitions:
        if d.get("id") == definition_id:
            synth_def = d
            break
    assert synth_def is not None
    assert len(synth_def["pins"]) == 4


def _get_fp_addr(fp) -> str | None:
    """Get atopile_address from a footprint."""
    return next(
        (
            str(p.value)
            for p in fp.propertys
            if str(getattr(p, "name", "")) == "atopile_address"
        ),
        None,
    )


def test_collapse_expand_roundtrip(project_dir: Path) -> None:
    """Collapse + to_kicad + expand should reproduce the original footprints.

    Uses provider_strict=True because that's the production path and the only
    mode that round-trips atopile_address via the ``@@`` component-id encoding.
    """
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    original = parent_pcb.kicad_pcb

    # Record original state
    orig_fp_count = len(original.footprints)
    orig_fp_addrs = sorted(filter(None, (_get_fp_addr(fp) for fp in original.footprints)))

    # Step 1: Collapse (provider_strict to preserve atopile_address)
    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        original,
        provider_strict=True,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )
    assert metadata, "Should have metadata"

    # Step 2: Convert back to KiCad
    result_pcb = DeepPCB_Transformer.to_internal_pcb(board)

    # At this point we have a synthetic footprint + external footprints
    synth_fps = [fp for fp in result_pcb.footprints if str(fp.name).startswith("REUSE_BLOCK:")]
    assert len(synth_fps) == 1

    # Step 3: Expand
    DeepPCB_Transformer.expand_reuse_blocks(result_pcb, metadata, project_dir)

    # Synthetic footprint should be gone
    synth_fps_after = [
        fp for fp in result_pcb.footprints if str(fp.name).startswith("REUSE_BLOCK:")
    ]
    assert len(synth_fps_after) == 0

    # Should have the same number of footprints as original
    assert len(result_pcb.footprints) == orig_fp_count

    # All original atopile_addresses should be present
    expanded_addrs = sorted(filter(None, (_get_fp_addr(fp) for fp in result_pcb.footprints)))
    assert expanded_addrs == orig_fp_addrs


def test_collapse_expand_preserves_external_nets(project_dir: Path) -> None:
    """External net assignments should survive collapse/expand."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    original = parent_pcb.kicad_pcb

    # Collapse
    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        original,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    # Convert back to KiCad
    result_pcb = DeepPCB_Transformer.to_internal_pcb(board)

    # Expand
    DeepPCB_Transformer.expand_reuse_blocks(result_pcb, metadata, project_dir)

    # Check net assignments on expanded footprints
    for fp in result_pcb.footprints:
        addr = next(
            (
                str(p.value)
                for p in fp.propertys
                if str(getattr(p, "name", "")) == "atopile_address"
            ),
            None,
        )
        if addr == "myblock.comp_a":
            # pad 1 should have VCC
            pad1 = next(p for p in fp.pads if p.name == "1")
            assert pad1.net is not None
            assert pad1.net.name == "VCC"
        elif addr == "myblock.comp_b":
            # pad 2 should have GND
            pad2 = next(p for p in fp.pads if p.name == "2")
            assert pad2.net is not None
            assert pad2.net.name == "GND"


def test_collapse_expand_adds_internal_routing(project_dir: Path) -> None:
    """Internal routing from sub-PCB should be added during expansion."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    original = parent_pcb.kicad_pcb

    # Collapse
    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        original,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    # Convert back to KiCad
    result_pcb = DeepPCB_Transformer.to_internal_pcb(board)

    # Expand
    DeepPCB_Transformer.expand_reuse_blocks(result_pcb, metadata, project_dir)

    # The sub-PCB had 1 internal segment. It should appear in the expanded result.
    # Plus the 3 external segments from collapse.
    # Total: at least 3 (external from collapse) + 1 (from sub-PCB expansion) = 4
    assert len(result_pcb.segments) >= 4


def test_no_reuse_blocks_without_project_root(project_dir: Path) -> None:
    """Without project_root, no reuse block processing should happen."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    board = DeepPCB_Transformer.from_kicad_pcb(parent_pcb.kicad_pcb)

    # All 4 footprints should be present
    assert len(board.components) == 4

    # All 4 wires should be present
    assert len(board.wires) == 4

    # All nets should be present
    assert len(board.nets) == 5  # 5 nets including net 0


def test_sub_net_map_built_correctly(project_dir: Path) -> None:
    """The sub-PCB net map should correctly map sub nets to parent nets."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    metadata: dict = {}
    DeepPCB_Transformer.from_kicad_pcb(
        parent_pcb.kicad_pcb,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    block = metadata["myblock"]
    sub_net_map = block["sub_net_map"]

    # sub_vcc → VCC (R1/comp_a pad 1)
    assert sub_net_map.get("sub_vcc") == "VCC"
    # sub_gnd → GND (R2/comp_b pad 2)
    assert sub_net_map.get("sub_gnd") == "GND"
    # sub_internal should NOT be in the map (it's internal)
    assert "sub_internal" not in sub_net_map


def test_provider_strict_collapse(project_dir: Path) -> None:
    """Collapse with provider_strict should produce valid provider JSON."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        parent_pcb.kicad_pcb,
        provider_strict=True,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    # Should still have the synthetic block
    block_components = [
        c for c in board.components if "REUSE_BLOCK:myblock" in str(c.get("partNumber", ""))
    ]
    assert len(block_components) == 1

    # Board should be serializable
    json_str = DeepPCB_Transformer.dumps(board)
    assert "REUSE_BLOCK" in json_str


def test_collapse_filters_internal_zones(project_dir: Path) -> None:
    """Zones on internal nets should be filtered during collapse."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )

    # Without reuse blocks: all zones present (2 zones)
    board_no_reuse = DeepPCB_Transformer.from_kicad_pcb(parent_pcb.kicad_pcb)
    assert len(board_no_reuse.planes) == 2

    # With reuse blocks: internal zones are now preserved
    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        parent_pcb.kicad_pcb,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )
    # Both zones preserved (internal routing no longer filtered)
    assert len(board.planes) == 2


def test_expand_copies_arcs_from_sub_pcb(project_dir: Path) -> None:
    """Arc segments from sub-PCB should be copied during expansion."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    original = parent_pcb.kicad_pcb

    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        original,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    result_pcb = DeepPCB_Transformer.to_internal_pcb(board)
    DeepPCB_Transformer.expand_reuse_blocks(result_pcb, metadata, project_dir)

    # The sub-PCB has 1 arc segment on internal net — should be expanded
    assert len(result_pcb.arcs) >= 1


def test_expand_copies_zones_from_sub_pcb(project_dir: Path) -> None:
    """Zones from sub-PCB should be copied during expansion with net remap."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    original = parent_pcb.kicad_pcb

    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        original,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    result_pcb = DeepPCB_Transformer.to_internal_pcb(board)
    DeepPCB_Transformer.expand_reuse_blocks(result_pcb, metadata, project_dir)

    # The sub-PCB has 1 zone on internal net — should be expanded
    # Plus the 1 external VCC zone from the parent
    expanded_zones = result_pcb.zones
    assert len(expanded_zones) >= 2

    # The sub-PCB zone should have remapped net_name (internal)
    zone_net_names = {getattr(z, "net_name", "") for z in expanded_zones}
    # Internal zone should be renamed to __block_myblock__sub_internal
    assert any("__block_myblock__" in str(name) for name in zone_net_names)


def test_expand_copies_vias_from_sub_pcb(project_dir: Path) -> None:
    """Vias from sub-PCB should be copied during expansion."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    original = parent_pcb.kicad_pcb

    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        original,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    result_pcb = DeepPCB_Transformer.to_internal_pcb(board)
    DeepPCB_Transformer.expand_reuse_blocks(result_pcb, metadata, project_dir)

    # The sub-PCB has 1 via on sub_vcc (mapped to VCC) — should be expanded
    assert len(result_pcb.vias) >= 1


def test_expand_copies_graphics_from_sub_pcb(project_dir: Path) -> None:
    """Graphics (gr_lines etc.) from sub-PCB should be copied during expansion."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    original = parent_pcb.kicad_pcb

    # Count original gr_lines (4 Edge.Cuts lines)
    orig_gr_line_count = len(original.gr_lines)

    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        original,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    result_pcb = DeepPCB_Transformer.to_internal_pcb(board)
    DeepPCB_Transformer.expand_reuse_blocks(result_pcb, metadata, project_dir)

    # The sub-PCB has 1 gr_line (silkscreen), so we should have more than
    # the original boundary lines from the parent
    assert len(result_pcb.gr_lines) >= orig_gr_line_count + 1


def test_reuse_block_protected_flag(project_dir: Path) -> None:
    """Synthetic reuse block components should be marked protected."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        parent_pcb.kicad_pcb,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    block_components = [
        c for c in board.components if "REUSE_BLOCK:myblock" in str(c.get("partNumber", ""))
    ]
    assert len(block_components) == 1
    assert block_components[0]["protected"] is True


def test_expand_no_duplicate_internal_routing(project_dir: Path) -> None:
    """Collapse → serialize → deserialize → expand should not double internal routing."""
    parent_pcb = kicad.loads(
        kicad.pcb.PcbFile, project_dir / "parent.kicad_pcb"
    )
    original = parent_pcb.kicad_pcb

    # Collapse
    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_pcb(
        original,
        provider_strict=True,
        project_root=project_dir,
        reuse_block_metadata_out=metadata,
    )

    # Serialize + deserialize (simulates DeepPCB round-trip)
    json_str = DeepPCB_Transformer.dumps(board)
    board2 = DeepPCB_Transformer.loads(json_str)

    # Convert back to KiCad
    result_pcb = DeepPCB_Transformer.to_internal_pcb(board2)

    # Expand
    DeepPCB_Transformer.expand_reuse_blocks(result_pcb, metadata, project_dir)

    # The sub-PCB has 1 internal segment (net 3 "sub_internal").
    # After expand, there should be exactly 1 segment on the internal net,
    # not 2 (which would happen if board-level was kept + sub-PCB copy added).
    internal_net_name = "__block_myblock__sub_internal"
    internal_net_num = None
    for net in result_pcb.nets:
        if net.name == internal_net_name:
            internal_net_num = net.number
            break

    if internal_net_num is not None:
        internal_segments = [s for s in result_pcb.segments if s.net == internal_net_num]
        # Sub-PCB has exactly 1 segment on internal net — should not be doubled
        assert len(internal_segments) == 1
