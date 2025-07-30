# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import copy
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from atopile.config import config as gcfg
from faebryk.exporters.pcb.kicad.transformer import (
    PCB_Transformer,
    get_all_geo_containers,
    get_all_geos,
)
from faebryk.libs.kicad.fileformats_common import C_xy, gen_uuid
from faebryk.libs.kicad.fileformats_latest import (
    C_group,
    C_kicad_pcb_file,
    C_net,
)
from faebryk.libs.util import (
    KeyErrorNotFound,
    find,
    find_or,
    not_none,
    once,
)

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
        self.layout_maps: dict[str, LayoutMap] = {}

        manifest = gcfg.project.paths.manifest
        if not manifest.exists():
            raise FileNotFoundError(f"Manifest file not found: {manifest}")

        logger.info(f"Loading layout maps from {manifest}")
        self._load_layout_maps(manifest)
        self._old_groups: dict[str, C_group] = {}

    @property
    @once
    def pcb(self) -> PCB:
        """Load the PCB file."""
        return C_kicad_pcb_file.loads(self.pcb_path).kicad_pcb

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

    def _get_footprint_addr(self, fp: Footprint) -> str | None:
        """Get the address of a footprint."""
        prop = fp.propertys.get("atopile_address")
        if prop:
            return prop.value
        return None

    def sync_groups(self):
        """Synchronize groups based on the layout map."""
        self._old_groups = {g.name: copy.deepcopy(g) for g in self.pcb.groups if g.name}
        groups = {g.name: g for g in self.pcb.groups if g.name}
        atopile_footprints = {
            addr: fp
            for fp in self.pcb.footprints
            if (addr := self._get_footprint_addr(fp))
        }
        atopile_fps_uuid = {fp.uuid: fp for fp in atopile_footprints.values()}

        for group_name, layout_map in self.layout_maps.items():
            logger.debug(f"Updating group {group_name}")

            # Create group if it doesn't exist
            if group_name not in groups:
                group = C_group(
                    name=group_name,
                    uuid=gen_uuid(group_name),
                    members=[],
                )
                self.pcb.groups.append(group)
                groups[group_name] = group
            else:
                group = groups[group_name]

            # Update group membership
            expected_members = set()
            for fp_addr in layout_map.group_components:
                if fp_addr in atopile_footprints:
                    expected_members.add(atopile_footprints[fp_addr].uuid)

            # add new members
            current_members = set(group.members) | expected_members
            # remove old atopile fps
            current_members -= set(atopile_fps_uuid.keys()).difference(expected_members)

            group.members[:] = list(current_members)

    def _generate_net_map(
        self, source_pcb: PCB, target_pcb: PCB, addr_map: dict[str, str]
    ) -> dict[str, str]:
        """Generate mapping from source net names to target net names."""
        net_map: dict[str, str] = {}
        mapping_counts: dict[str, dict[str, int]] = {}

        # Get footprints by address for both boards
        source_fps: dict[str, PCB.C_pcb_footprint] = {}
        for fp in source_pcb.footprints:
            addr = self._get_footprint_addr(fp)
            if addr:
                source_fps[addr] = fp

        target_fps: dict[str, PCB.C_pcb_footprint] = {}
        for fp in target_pcb.footprints:
            addr = self._get_footprint_addr(fp)
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

    def _sync_footprints(
        self,
        sub_pcb: PCB,
        top_pcb: PCB,
        addr_map: dict[str, str],
        net_map: dict[str, str],
        offset: C_xy,
    ):
        """Sync footprint positions from source to target."""
        # Get footprints by address
        sub_fps: dict[str, PCB.C_pcb_footprint] = {
            addr: fp
            for fp in sub_pcb.footprints
            if (addr := self._get_footprint_addr(fp))
        }

        top_fps: dict[str, PCB.C_pcb_footprint] = {
            addr: fp
            for fp in top_pcb.footprints
            if (addr := self._get_footprint_addr(fp))
        }

        # Sync positions
        for src_addr, tgt_addr in addr_map.items():
            if src_addr not in sub_fps or tgt_addr not in top_fps:
                continue

            sub_fp = sub_fps[src_addr]
            top_fp = top_fps[tgt_addr]

            PCB_Transformer.move_fp(top_fp, sub_fp.at + offset, sub_fp.layer)

        # Non-atopile footprints
        new_objects = []
        manual_fps = [
            fp for fp in sub_pcb.footprints if not self._get_footprint_addr(fp)
        ]
        for sub_fp in manual_fps:
            top_fp = copy.deepcopy(sub_fp)
            top_fp.uuid = gen_uuid()

            for pad in top_fp.pads:
                pad.uuid = gen_uuid()
                if pad.net and pad.net.name in net_map:
                    top_net_name = net_map[pad.net.name]
                    pad.net = C_net(
                        self._get_net_number(top_pcb, top_net_name),
                        name=top_net_name,
                    )
                else:
                    pad.net = None

            new_objects.append(top_fp)

            PCB_Transformer.move_fp(top_fp, sub_fp.at + offset, sub_fp.layer)

        return new_objects

    def _sync_routes(
        self,
        sub_pcb: PCB,
        top_pcb: PCB,
        net_map: dict[str, str],
        offset: C_xy,
    ):
        new_objects = []
        for track in sub_pcb.segments + sub_pcb.arcs + sub_pcb.zones + sub_pcb.vias:
            # Get source net name
            sub_net: C_net | None = find_or(
                sub_pcb.nets,
                lambda n: n.number == track.net,
                None,  # type: ignore
            )

            # Create new track
            new_track: PCB.C_segment | PCB.C_arc_segment | PCB.C_zone | PCB.C_via = (
                copy.deepcopy(track)
            )
            new_track.uuid = gen_uuid()
            if sub_net and sub_net.name in net_map:
                new_track.net = self._get_net_number(top_pcb, net_map[sub_net.name])
                if isinstance(new_track, PCB.C_zone):
                    new_track.net_name = net_map[sub_net.name]
            else:
                new_track.net = 0

            PCB_Transformer.move_object(new_track, offset)
            new_objects.append(new_track)

        return new_objects

    def _sync_other(self, sub_pcb: PCB, top_pcb: PCB, offset: C_xy):
        new_graphics = []
        for gr in (
            get_all_geos(sub_pcb)
            + sub_pcb.gr_text_boxs
            + sub_pcb.gr_texts
            + sub_pcb.images
            # TODO tables are weird about uuids
            # + sub_pcb.tables
        ):
            new_gr = copy.deepcopy(gr)
            new_gr.uuid = gen_uuid()

            PCB_Transformer.move_object(new_gr, offset)
            new_graphics.append(new_gr)

        return new_graphics

    def _calculate_group_offset(self, source_pcb: PCB, target_group: C_group) -> C_xy:
        """Calculate offset to apply when pulling a group layout."""

        ZERO = C_xy(0, 0)
        # Find anchor footprint (largest by pad count)
        group_fps = [
            fp
            for fp in self.pcb.footprints
            if fp.uuid in target_group.members and self._get_footprint_addr(fp)
        ]

        if not group_fps:
            return ZERO

        # Find anchor by pad count
        anchor_fp = max(
            group_fps,
            key=lambda fp: len(fp.pads),
        )
        top_pos = anchor_fp.at

        # Find corresponding source footprint
        target_addr = not_none(self._get_footprint_addr(anchor_fp))
        target_addr = target_addr.split(".", maxsplit=1)[-1]

        # Find in source
        try:
            sub_fp = find(
                source_pcb.footprints,
                lambda fp: self._get_footprint_addr(fp) == target_addr,
            )
        except KeyErrorNotFound:
            logger.warning(f"No source footprint found for '{target_addr}'")
            return ZERO

        sub_pos = sub_fp.at
        # TODO rotation?
        offset = C_xy(
            top_pos.x - sub_pos.x,
            top_pos.y - sub_pos.y,
        )

        return offset

    def pull_group_layout(self, group_name: str):
        """Pull layout for a specific group from its source file."""

        if group_name not in self.layout_maps:
            logger.warning(f"No layout map found for group {group_name}")
            return
        layout_map = self.layout_maps[group_name]
        if not layout_map.layout_path.exists():
            raise FileNotFoundError(f"Layout file {layout_map.layout_path} not found")

        top_pcb = self.pcb
        sub_pcb = C_kicad_pcb_file.loads(layout_map.layout_path).kicad_pcb

        group = find(top_pcb.groups, lambda g: g.name == group_name)
        offset = self._calculate_group_offset(sub_pcb, group)
        inverted_addr_map = {v: k for k, v in layout_map.addr_map.items()}

        net_map = self._generate_net_map(sub_pcb, top_pcb, inverted_addr_map)

        # delete all non-fp elements in group
        to_delete = (
            set(self._old_groups[group_name].members)
            if group_name in self._old_groups
            else set()
        )
        for container in [
            top_pcb.segments,
            top_pcb.arcs,
            top_pcb.vias,
            top_pcb.zones,
            *get_all_geo_containers(top_pcb),
            top_pcb.images,
            top_pcb.gr_texts,
            top_pcb.gr_text_boxs,
            # top_pcb.tables,
        ]:
            container[:] = [x for x in container if x.uuid not in to_delete]
        # delete non-atopile group footprints
        top_pcb.footprints[:] = [
            fp
            for fp in top_pcb.footprints
            if fp.uuid not in to_delete or self._get_footprint_addr(fp)
        ]

        new_fps = self._sync_footprints(
            sub_pcb, top_pcb, inverted_addr_map, net_map, offset
        )
        new_routes = self._sync_routes(sub_pcb, top_pcb, net_map, offset)
        new_other = self._sync_other(sub_pcb, top_pcb, offset)

        new_elements = new_fps + new_routes + new_other
        for new_element in new_elements:
            container = PCB_Transformer.get_pcb_container(new_element, top_pcb)
            container.append(new_element)

        group.members.extend(e.uuid for e in new_elements)

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
