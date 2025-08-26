# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import copy
import logging

from atopile.config import config as gcfg
from atopile.layout import SubAddress
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
    groupby,
    not_none,
    once,
    try_or,
)

logger = logging.getLogger(__name__)

PCB = C_kicad_pcb_file.C_kicad_pcb
type Footprint = PCB.C_pcb_footprint


class LayoutSync:
    """Handles layout synchronization between PCB files."""

    def __init__(self, pcb: PCB):
        self.pcb = pcb

        self._old_groups: dict[str, C_group] = {}

        fps = self.pcb.footprints
        sub_fps = [
            (fp, sub_addr) for fp in fps if (sub_addr := self._get_sub_address(fp))
        ]

        self.groups = groupby(sub_fps, lambda x: self._get_group_name(x[1], x[0]))
        for group_name, fps in self.groups.items():
            pcb_names = {x[1].pcb_address for x in fps}
            assert len(pcb_names) == 1, (
                f"Multiple PCB names found for group {group_name}: {pcb_names}"
            )

    def _get_all_sub_addresses(self, fp: Footprint) -> list[SubAddress]:
        sub_addresses = fp.propertys.get("atopile_subaddresses")
        if not sub_addresses:
            return []
        return [
            SubAddress.deserialize(addr)
            for addr in sub_addresses.value.removeprefix("[")
            .removesuffix("]")
            .split(", ")
        ]

    def _get_sub_address(self, fp: Footprint) -> SubAddress | None:
        return self._choose_sublayout(self._get_all_sub_addresses(fp))

    @once
    def _get_pcb(self, pcb_address: str) -> PCB:
        path = gcfg.project.paths.root / pcb_address
        return C_kicad_pcb_file.loads(path).kicad_pcb

    def _get_group_name(self, sub_addr: SubAddress, fp: Footprint) -> str:
        base_addr = self._get_footprint_addr(fp)
        assert base_addr
        inner = sub_addr.module_address
        return base_addr.removesuffix("." + inner)

    def _choose_sublayout(self, sub_addr: list[SubAddress]) -> SubAddress | None:
        addr_to_pcb = {
            x: pcb
            for x in sub_addr
            if (pcb := try_or(lambda: self._get_pcb(x.pcb_address), None))
        }
        if not addr_to_pcb:
            return None

        # prefer sublayouts with tracks if any exist
        candidates = addr_to_pcb
        if any(pcb.segments for pcb in candidates.values()):
            candidates = {
                sub_addr: pcb for sub_addr, pcb in addr_to_pcb.items() if pcb.segments
            }

        # Heuristic: prefer higher level modules
        candidate = max(
            candidates.items(),
            key=lambda x: len(x[0].module_address.split(".")),
        )
        return candidate[0]

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

        # remove all atopile footprints from groups (later re-added)
        for pcb_group in self.pcb.groups:
            pcb_group.members[:] = [
                uuid for uuid in pcb_group.members if uuid not in atopile_fps_uuid
            ]

        for group_name, fps in self.groups.items():
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
            expected_members = {fp.uuid for fp, _ in fps}

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

    def _calculate_group_offset(
        self,
        source_pcb: PCB,
        target_group: C_group,
    ) -> C_xy:
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
        target_addr = not_none(self._get_sub_address(anchor_fp)).module_address

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

    def _clean_group(self, group_name: str):
        """Delete all non-fp elements in group."""

        if group_name not in self._old_groups:
            return

        pcb = self.pcb

        to_delete = (
            set(self._old_groups[group_name].members)
            if group_name in self._old_groups
            else set()
        )
        for container in [
            pcb.segments,
            pcb.arcs,
            pcb.vias,
            pcb.zones,
            *get_all_geo_containers(pcb),
            pcb.images,
            pcb.gr_texts,
            pcb.gr_text_boxs,
            # top_pcb.tables,
        ]:
            container[:] = [x for x in container if x.uuid not in to_delete]
        # delete non-atopile group footprints
        pcb.footprints[:] = [
            fp
            for fp in pcb.footprints
            if fp.uuid not in to_delete or self._get_footprint_addr(fp)
        ]

    def pull_group_layout(self, group_name: str):
        """Pull layout for a specific group from its source file."""

        if group_name not in self.groups:
            logger.warning(f"No layout map found for group {group_name}")
            return

        fps = self.groups[group_name]
        pcb_address = fps[0][1].pcb_address

        top_pcb = self.pcb
        try:
            sub_pcb = self._get_pcb(pcb_address)
        except Exception as e:
            logger.error(f"Error loading sub pcb {pcb_address}: {e}")
            return

        group = find(top_pcb.groups, lambda g: g.name == group_name)
        offset = self._calculate_group_offset(sub_pcb, group)
        inverted_addr_map = {
            sub_addr.module_address: not_none(self._get_footprint_addr(fp))
            for fp, sub_addr in fps
        }

        net_map = self._generate_net_map(sub_pcb, top_pcb, inverted_addr_map)

        # remove all stuff from involved groups, before re-adding new elements
        involved_groups = {
            self._get_group_name(addr, fp)
            for fp, _ in fps
            for addr in self._get_all_sub_addresses(fp)
        }
        for g_name in involved_groups:
            self._clean_group(g_name)

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
