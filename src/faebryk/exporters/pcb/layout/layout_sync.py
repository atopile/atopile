# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import copy
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from atopile.config import config as gcfg
from faebryk.libs.kicad.fileformats_common import gen_uuid
from faebryk.libs.kicad.fileformats_latest import (
    C_group,
    C_kicad_pcb_file,
)
from faebryk.libs.util import find

logger = logging.getLogger(__name__)

PCB = C_kicad_pcb_file.C_kicad_pcb
type Footprint = PCB.C_pcb_footprint


@dataclass
class LayoutMap:
    """Maps module addresses to their layout information."""

    layout_path: Path
    addr_map: dict[str, str]  # source addr -> target addr
    uuid_to_addr_map: dict[str, str]  # uuid -> addr (legacy support)
    group_components: list[str]
    nested_groups: list[str]


class LayoutSync:
    """Handles layout synchronization between PCB files."""

    def __init__(self, pcb_path: Path):
        self.pcb_path = pcb_path
        self.pcb: PCB | None = None
        self.layout_maps: dict[str, LayoutMap] = {}

        manifest = gcfg.project.paths.manifest
        if not manifest.exists():
            raise FileNotFoundError(f"Manifest file not found: {manifest}")

        logger.info(f"Loading layout maps from {manifest}")
        self._load_layout_maps(manifest)

    def load_pcb(self) -> PCB:
        """Load the PCB file."""
        if self.pcb is None:
            self.pcb = C_kicad_pcb_file.loads(self.pcb_path).kicad_pcb
        return self.pcb

    def _load_layout_maps(self, manifest_path: Path) -> dict[str, LayoutMap]:
        """Load layout maps from the manifest."""
        with manifest_path.open("r") as f:
            manifest = json.load(f)

        # Find the layout map file for this PCB
        layouts = manifest.get("by-layout", {})
        pcb_key = find(
            layouts, lambda key: Path(key).resolve() == self.pcb_path.resolve()
        )

        layout_file = Path(layouts[pcb_key]["layouts"])
        with layout_file.open("r") as f:
            layout_data = json.load(f)

        # Convert to LayoutMap objects
        self.layout_maps = {}
        for group_name, data in layout_data.items():
            self.layout_maps[group_name] = LayoutMap(
                layout_path=Path(data["layout_path"]),
                addr_map=data.get("addr_map", {}),
                uuid_to_addr_map=data.get("uuid_to_addr_map", {}),
                group_components=data.get("group_components", []),
                nested_groups=data.get("nested_groups", []),
            )

        return self.layout_maps

    def get_footprint_addr(self, fp: Footprint) -> str | None:
        """Get the address of a footprint."""
        # First try the property
        out = fp.propertys.get("atopile_address")
        if out:
            return out.value

        # Fallback to UUID mapping (legacy support)
        if hasattr(fp, "uuid") and fp.uuid:
            for layout_map in self.layout_maps.values():
                if fp.uuid in layout_map.uuid_to_addr_map:
                    return layout_map.uuid_to_addr_map[fp.uuid]

        return None

    def get_footprints_by_addr(self) -> dict[str, Footprint]:
        """Get all footprints indexed by their address."""
        pcb = self.load_pcb()
        result = {}
        for fp in pcb.footprints:
            addr = self.get_footprint_addr(fp)
            if addr:
                result[addr] = fp
        return result

    def get_groups_by_name(self) -> dict[str, C_group]:
        """Get all groups indexed by their name."""
        pcb = self.load_pcb()
        return {g.name: g for g in pcb.groups if g.name}

    def sync_groups(self):
        """Synchronize groups based on the layout map."""
        pcb = self.load_pcb()
        groups = self.get_groups_by_name()
        footprints = self.get_footprints_by_addr()

        for group_name, layout_map in self.layout_maps.items():
            logger.debug(f"Updating group {group_name}")

            # Create group if it doesn't exist
            if group_name not in groups:
                group = C_group(
                    name=group_name,
                    uuid=gen_uuid(group_name),
                    members=[],
                )
                pcb.groups.append(group)
                groups[group_name] = group
            else:
                group = groups[group_name]

            # Update group membership
            expected_members = set()
            for fp_addr in layout_map.group_components:
                if fp_addr in footprints:
                    expected_members.add(footprints[fp_addr].uuid)

            # Update members list
            group.members = list(expected_members)

    def generate_net_map(
        self, source_pcb: PCB, target_pcb: PCB, addr_map: dict[str, str]
    ) -> dict[str, str]:
        """Generate mapping from source net names to target net names."""
        net_map: dict[str, str] = {}
        mapping_counts: dict[str, dict[str, int]] = {}

        # Get footprints by address for both boards
        source_fps: dict[str, PCB.C_pcb_footprint] = {}
        for fp in source_pcb.footprints:
            addr = self.get_footprint_addr(fp)
            if addr:
                source_fps[addr] = fp

        target_fps: dict[str, PCB.C_pcb_footprint] = {}
        for fp in target_pcb.footprints:
            addr = self.get_footprint_addr(fp)
            if addr:
                target_fps[addr] = fp

        # Map nets based on pad connections
        for src_addr, tgt_addr in addr_map.items():
            if src_addr not in source_fps or tgt_addr not in target_fps:
                continue

            src_fp = source_fps[src_addr]
            tgt_fp = target_fps[tgt_addr]

            # Match pads by number
            for src_pad in src_fp.pads:
                pad_name = src_pad.name
                tgt_pads = [p for p in tgt_fp.pads if p.name == pad_name]

                if len(tgt_pads) == 1:
                    tgt_pad = tgt_pads[0]
                elif len(tgt_pads) > 1:
                    # Match by size if multiple pads with same number
                    best_match = min(
                        tgt_pads,
                        key=lambda p: abs(p.size.w - src_pad.size.w)
                        + (
                            abs(p.size.h - src_pad.size.h)
                            if p.size.h and src_pad.size.h
                            else 0
                        ),
                    )
                    tgt_pad = best_match
                else:
                    continue

                # Map the nets
                if (
                    src_pad.net
                    and tgt_pad.net
                    and src_pad.net.name
                    and tgt_pad.net.name
                ):
                    src_net = src_pad.net.name
                    tgt_net = tgt_pad.net.name

                    if src_net not in mapping_counts:
                        mapping_counts[src_net] = {}
                    mapping_counts[src_net][tgt_net] = (
                        mapping_counts[src_net].get(tgt_net, 0) + 1
                    )

                    # Use most frequent mapping
                    if src_net not in net_map or mapping_counts[src_net][tgt_net] > max(
                        mapping_counts[src_net].values()
                    ):
                        net_map[src_net] = tgt_net

        return net_map

    def sync_footprints(
        self, source_pcb: PCB, target_pcb: PCB, addr_map: dict[str, str]
    ):
        """Sync footprint positions from source to target."""
        # Get footprints by address
        source_fps: dict[str, PCB.C_pcb_footprint] = {}
        for fp in source_pcb.footprints:
            addr = self.get_footprint_addr(fp)
            if addr:
                source_fps[addr] = fp

        target_fps: dict[str, PCB.C_pcb_footprint] = {}
        for fp in target_pcb.footprints:
            addr = self.get_footprint_addr(fp)
            if addr:
                target_fps[addr] = fp

        # Sync positions
        for src_addr, tgt_addr in addr_map.items():
            if src_addr not in source_fps or tgt_addr not in target_fps:
                continue

            src_fp = source_fps[src_addr]
            tgt_fp = target_fps[tgt_addr]

            # Copy position and orientation
            tgt_fp.at = src_fp.at
            tgt_fp.layer = src_fp.layer

            # Sync reference designator position
            if src_fp.fp_texts and tgt_fp.fp_texts:
                for src_text in src_fp.fp_texts:
                    if src_text.type == "reference":
                        for tgt_text in tgt_fp.fp_texts:
                            if tgt_text.type == "reference":
                                tgt_text.at = src_text.at
                                break
                        break

            # Sync pad positions
            if hasattr(tgt_fp, "pad") and hasattr(src_fp, "pad"):
                for tgt_pad in tgt_fp.pad:  # type: ignore
                    src_pads = [p for p in src_fp.pad if p.number == tgt_pad.number]  # type: ignore
                    if src_pads:
                        src_pad = src_pads[0]
                        tgt_pad.at = src_pad.at

    def calculate_group_offset(
        self, source_pcb: PCB, target_group: C_group
    ) -> tuple[float, float]:
        """Calculate offset to apply when pulling a group layout."""
        # Find anchor footprint (largest by pad count)
        target_pcb = self.load_pcb()
        group_fps = []

        for fp in target_pcb.footprints:
            if fp.uuid in target_group.members:
                group_fps.append(fp)

        if not group_fps:
            return (0.0, 0.0)

        # Find anchor by pad count
        anchor_fp = max(
            group_fps, key=lambda fp: len(fp.pad) if hasattr(fp, "pad") else 0
        )
        target_pos = anchor_fp.at

        # Find corresponding source footprint
        target_addr = self.get_footprint_addr(anchor_fp)
        if not target_addr:
            return (0.0, 0.0)

        # Find in source
        for fp in source_pcb.footprints:
            if self.get_footprint_addr(fp) == target_addr:
                source_pos = fp.at
                return (
                    target_pos.x - source_pos.x,
                    target_pos.y - source_pos.y,
                )

        return (0.0, 0.0)

    def pull_group_layout(self, group_name: str):
        """Pull layout for a specific group from its source file."""
        if group_name not in self.layout_maps:
            logger.warning(f"No layout map found for group {group_name}")
            return

        layout_map = self.layout_maps[group_name]
        if not layout_map.layout_path.exists():
            raise FileNotFoundError(f"Layout file {layout_map.layout_path} not found")

        # Load source and target PCBs
        source_pcb = C_kicad_pcb_file.loads(layout_map.layout_path).kicad_pcb
        target_pcb = self.load_pcb()

        # Get the group
        groups = self.get_groups_by_name()
        if group_name not in groups:
            logger.warning(f"Group {group_name} not found in target PCB")
            return

        group = groups[group_name]

        # Calculate offset
        offset = self.calculate_group_offset(source_pcb, group)

        # Generate net map
        net_map = self.generate_net_map(
            source_pcb, target_pcb, {v: k for k, v in layout_map.addr_map.items()}
        )

        # Sync footprints
        self.sync_footprints(
            source_pcb,
            target_pcb,
            {v: k for k, v in layout_map.addr_map.items()},
        )

        # Sync tracks
        for track in source_pcb.segments:
            # Get source net name
            source_net_name = None
            for net in source_pcb.nets:
                if net.number == track.net:
                    source_net_name = net.name
                    break

            if source_net_name and source_net_name in net_map:
                # Create new track
                new_track = copy.deepcopy(track)
                new_track.net = self._get_net_number(
                    target_pcb, net_map[source_net_name]
                )

                # Apply offset
                new_track.start.x += offset[0]
                new_track.start.y += offset[1]
                new_track.end.x += offset[0]
                new_track.end.y += offset[1]

                target_pcb.segments.append(new_track)
                group.members.append(new_track.uuid)

        # Sync zones
        for zone in source_pcb.zones:
            # Get source net name
            source_net_name = None
            if hasattr(zone, "net") and zone.net:
                for net in source_pcb.nets:
                    if net.number == zone.net:
                        source_net_name = net.name
                        break

            if source_net_name and source_net_name in net_map:
                new_zone = copy.deepcopy(zone)
                new_zone.net = self._get_net_number(
                    target_pcb, net_map[source_net_name]
                )

                # Apply offset to polygon points
                if hasattr(new_zone, "polygon") and new_zone.polygon:
                    polygon = new_zone.polygon
                    if hasattr(polygon, "pts") and hasattr(polygon.pts, "xy"):
                        for pt in polygon.pts.xy:
                            pt.x += offset[0]
                            pt.y += offset[1]

                target_pcb.zones.append(new_zone)
                group.members.append(new_zone.uuid)

        # Sync graphics
        for gr in source_pcb.gr_lines + source_pcb.gr_arcs + source_pcb.gr_rects:
            new_gr = copy.deepcopy(gr)

            # Apply offset based on type
            if hasattr(new_gr, "start"):
                new_gr.start.x += offset[0]
                new_gr.start.y += offset[1]
            if hasattr(new_gr, "end"):
                new_gr.end.x += offset[0]
                new_gr.end.y += offset[1]
            if hasattr(new_gr, "center"):
                new_gr.center.x += offset[0]
                new_gr.center.y += offset[1]

            # Add to appropriate list
            if hasattr(new_gr, "start") and hasattr(new_gr, "end"):
                if hasattr(new_gr, "mid"):
                    target_pcb.gr_arcs.append(new_gr)
                else:
                    target_pcb.gr_lines.append(new_gr)
            elif hasattr(new_gr, "center"):
                target_pcb.gr_rects.append(new_gr)

            group.members.append(new_gr.uuid)

    def _get_net_number(self, pcb: PCB, net_name: str) -> int:
        """Get the net number for a given net name."""
        for net in pcb.nets:
            if net.name == net_name:
                return net.number
        # If net doesn't exist, return 0 (no net)
        return 0

    def save_pcb(self, output_path: Path | None = None):
        """Save the PCB file."""
        if self.pcb is None:
            raise ValueError("No PCB loaded")

        output_path = output_path or self.pcb_path
        C_kicad_pcb_file(kicad_pcb=self.pcb).dumps(output_path)
