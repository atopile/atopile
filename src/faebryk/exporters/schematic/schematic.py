# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Schematic exporter – generates hierarchical JSON for the Three.js schematic viewer.

Produces **v2 format**: a recursive tree of SchematicSheets, each containing
modules (expandable blocks), components (leaf parts), and scoped nets.

Leverages the pinout exporter's ``_trace_lead_interfaces`` for rich per-pin
bus-type classification and module-interface mapping.

Output: ``layout/<build>.ato_sch``
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver
from faebryk.exporters.pinout.pinout import (
    _assign_sides_from_positions,
    _determine_pin_type,
    _trace_lead_interfaces,
)
from faebryk.exporters.utils import natural_sort_key, strip_root_hex, write_json

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────

_PIN_STUB_LEN = 2.54
_MIN_BODY = 5.08

# Categories that go on the left side of a module block
_LEFT_CATEGORIES = {"power", "ground", "input", "reset", "crystal", "control", "analog"}


# Interface binding tuple used in per-module pin maps:
# (iface_id, signal_suffix, is_line_level)
_PinBinding = tuple[str, str, bool]


@dataclass(frozen=True)
class _ResolvedInterfacePin:
    iface_id: str
    signal_suffix: str
    is_line_level: bool
    category: str
    iface_type: str


def _is_passthrough_binding(binding: _ResolvedInterfacePin) -> bool:
    """GPIO/control interfaces act as pass-through bridges for shared pins."""
    category = binding.category.lower()
    iface_type = binding.iface_type.lower()
    return category == "control" or iface_type in {"gpio", "control"}


# ── Pin classification (reuses pinout exporter primitives) ──────


def _classify_pin(name: str, lead_functions: list[dict]) -> tuple[str, str]:
    """Return (category, preferred_side) for a pin.

    When a pin has both signal and power function traces (e.g., because a
    bridging module like Addressor connects signal lines to power rails),
    we classify based on the pin's display name rather than function types.
    """
    # ── Name-based classification (highest priority) ─────────────
    lower = name.lower()

    # Explicit power/ground pin names
    if lower in ("gnd", "vss", "vee"):
        return ("ground", "left")
    if lower in ("vcc", "vdd", "vin", "vbus", "vbat", "3v3", "5v"):
        return ("power", "left")

    # Explicit protocol pin names
    if re.search(r"reset|rst|nrst|~reset", lower):
        return ("reset", "left")
    if re.search(r"^sc[dl]\d*$|^sd[al]\d*$|^i2c", lower):
        return ("i2c", "right")
    if re.search(r"spi|mosi|miso|sclk|nss", lower):
        return ("spi", "right")
    if re.search(r"uart|^tx\d*$|^rx\d*$", lower):
        return ("uart", "right")

    # ── Function-based classification ─────────────────────────────
    # Only use function types when the name is ambiguous.
    # If a pin has BOTH power and non-power functions, the non-power
    # function takes precedence (the power trace is likely from a
    # bridging module like Addressor).
    if lead_functions:
        non_power_fns = [f for f in lead_functions if f.get("type") != "Power"]
        power_fns = [f for f in lead_functions if f.get("type") == "Power"]

        # Non-power functions → use the protocol type
        for fn in non_power_fns:
            fn_type = fn.get("type", "")
            if fn_type in ("I2C", "SPI", "UART", "I2S", "USB", "JTAG"):
                return (fn_type.lower(), "right")
            if fn_type == "Crystal":
                return ("crystal", "left")
            if fn_type == "Control":
                return ("control", "left")
            if fn_type == "Analog":
                return ("analog", "left")

        # Only power functions (no signal functions) → dedicated power pin
        if power_fns and not non_power_fns:
            pin_type = _determine_pin_type(name, lead_functions)
            if pin_type == "ground":
                return ("ground", "left")
            if pin_type == "power":
                return ("power", "left")

    if lower in ("nc", "n/c"):
        return ("nc", "right")

    return ("signal", "right")


def _net_type(net_name: str) -> str:
    """Classify a net name into power/ground/bus/signal."""
    lower = net_name.lower()
    if any(kw in lower for kw in ["gnd", "vss", "lv"]):
        return "ground"
    if any(kw in lower for kw in ["vcc", "vdd", "3v3", "5v", "power", "vbus", "hv"]):
        return "power"
    if any(
        kw in lower
        for kw in [
            "scl",
            "sda",
            "i2c",
            "spi",
            "mosi",
            "miso",
            "uart",
            "tx",
            "rx",
            "jtag",
            "usb",
        ]
    ):
        return "bus"
    return "signal"


def _extract_designator_prefix(designator: str) -> str:
    return "".join(ch for ch in designator.upper() if ch.isalpha())


def _extract_footprint_hint(component_node: fabll.Node) -> str:
    """Return a best-effort footprint identifier for package inference."""
    fp_trait = component_node.try_get_trait(F.Footprints.has_associated_footprint)
    if fp_trait is None:
        return ""

    try:
        fp = fp_trait.get_footprint()
    except Exception:
        return ""

    if pcb_trait := fp.try_get_trait(
        F.KiCadFootprints.has_associated_kicad_pcb_footprint
    ):
        for getter in (
            pcb_trait.get_kicad_identifier,
            lambda: pcb_trait.get_footprint().name,
            pcb_trait.get_library_name,
        ):
            try:
                value = getter()
                if value:
                    return str(value)
            except Exception:
                continue

    if lib_trait := fp.try_get_trait(
        F.KiCadFootprints.has_associated_kicad_library_footprint
    ):
        for getter in (
            lib_trait.get_kicad_identifier,
            lambda: Path(lib_trait.get_kicad_footprint_file_path()).stem,
            lib_trait.get_library_name,
        ):
            try:
                value = getter()
                if value:
                    return str(value)
            except Exception:
                continue

    return ""


def _normalize_package_code(footprint_hint: str) -> str | None:
    if not footprint_hint:
        return None

    upper = footprint_hint.upper().replace(" ", "")

    for pattern, template in (
        (r"SOD[-_]?([0-9]{3,4})", "SOD-{0}"),
        (r"SOT[-_]?([0-9]{2,4})", "SOT-{0}"),
        (r"DO[-_]?([0-9A-Z]{2,6})", "DO-{0}"),
    ):
        if match := re.search(pattern, upper):
            return template.format(match.group(1))

    if match := re.search(r"\b(SMA|SMB|SMC)\b", upper):
        return match.group(1)

    if match := re.search(
        r"(?<![0-9])(01005|0201|0402|0603|0805|1206|1210|1812|2010|2512)(?![0-9])",
        upper,
    ):
        return match.group(1)

    if "TESTPOINT" in upper:
        if "LOOP" in upper:
            return "TESTPOINT-LOOP"
        if "TH" in upper or "THT" in upper:
            return "TESTPOINT-THT"
        return "TESTPOINT"

    if "USB-C" in upper or "USBC" in upper:
        return "USB-C"

    if match := re.search(r"([12]X[0-9]{1,2})", upper):
        return match.group(1)

    if "HEADER" in upper or "CONNECTOR" in upper or "CONN" in upper:
        return "CONNECTOR"

    return None


def _infer_symbol_family(
    module_type: str | None,
    component_name: str | None,
    designator: str,
    reference: str,
    pin_count: int,
) -> str | None:
    """Infer schematic symbol family from module type/name + reference hints."""
    designator_prefix = _extract_designator_prefix(designator)

    haystack = " ".join(
        part.lower()
        for part in (module_type, component_name, designator_prefix, reference)
        if part
    )

    if "led" in haystack:
        return "led"
    if "testpoint" in haystack or designator_prefix.startswith("TP"):
        return "testpoint"

    connector_keywords = (
        "connector",
        "header",
        "usb",
        "jst",
        "socket",
        "terminal",
        "receptacle",
        "jack",
        "plug",
        "conn",
    )
    if designator_prefix.startswith(("J", "P", "CN", "USB")):
        return "connector"
    if pin_count >= 3 and any(keyword in haystack for keyword in connector_keywords):
        return "connector"

    if (
        "capacitorpolarized" in haystack
        or "capacitor_polarized" in haystack
        or "polarized" in haystack
        or "electrolytic" in haystack
    ):
        return "capacitor_polarized"
    if "capacitor" in haystack or designator_prefix.startswith("C"):
        return "capacitor"
    if "resistor" in haystack or designator_prefix.startswith("R"):
        return "resistor"
    if "inductor" in haystack or designator_prefix.startswith("L"):
        return "inductor"
    if "diode" in haystack or designator_prefix.startswith(("D", "CR", "ZD")):
        return "diode"
    return None


def _infer_symbol_variant(family: str, package_code: str | None) -> str | None:
    if family in {"resistor", "capacitor", "capacitor_polarized", "inductor", "led"}:
        if package_code and re.fullmatch(r"[0-9]{4,5}", package_code):
            return f"chip-{package_code}"
        return "iec"
    if family == "diode":
        if package_code and package_code.startswith(
            ("SOD-", "SOT-", "DO-", "SMA", "SMB", "SMC")
        ):
            return package_code.lower()
        return "iec"
    if family == "connector":
        if package_code and re.fullmatch(r"[12]X[0-9]{1,2}", package_code):
            return f"header-{package_code.lower()}"
        return "generic"
    if family == "testpoint":
        if package_code == "TESTPOINT-LOOP":
            return "loop"
        if package_code == "TESTPOINT-THT":
            return "through_hole"
        return "pad"
    return None


def _infer_polarity(family: str) -> str | None:
    if family in {"diode", "led"}:
        return "anode_cathode"
    if family == "capacitor_polarized":
        return "plus_minus"
    if family in {"connector", "testpoint"}:
        return "pin1"
    return None


def _build_symbol_metadata(
    module_type: str | None,
    component_name: str | None,
    designator: str,
    reference: str,
    pin_count: int,
    footprint_hint: str,
) -> dict[str, str]:
    family = _infer_symbol_family(
        module_type=module_type,
        component_name=component_name,
        designator=designator,
        reference=reference,
        pin_count=pin_count,
    )
    if family is None:
        return {}

    package_code = _normalize_package_code(footprint_hint)
    variant = _infer_symbol_variant(family, package_code)
    polarity = _infer_polarity(family)

    out: dict[str, str] = {"symbolFamily": family}
    if variant:
        out["symbolVariant"] = variant
    if package_code:
        out["packageCode"] = package_code
    if polarity:
        out["polarity"] = polarity
    return out


# ── Body layout ─────────────────────────────────────────────────


def _get_kicad_positions_by_pin_number(
    component_node: fabll.Node,
) -> dict[str, tuple[float, float]]:
    """Return pin-number keyed KiCad pad positions in footprint-local mm."""
    positions: dict[str, tuple[float, float]] = {}
    try:
        fp_trait = component_node.get_trait(F.Footprints.has_associated_footprint)
        fp = fp_trait.get_footprint()

        for fpad in fp.get_pads():
            pad_number = str(fpad.pad_number)
            if not fpad.has_trait(F.KiCadFootprints.has_associated_kicad_pcb_pad):
                continue

            kicad_trait = fpad.get_trait(F.KiCadFootprints.has_associated_kicad_pcb_pad)
            pcb_fp, pcb_pads = kicad_trait.get_pads()
            if not pcb_pads:
                continue

            pcb_pad = pcb_pads[0]
            positions[pad_number] = (
                round(pcb_pad.at.x - pcb_fp.at.x, 3),
                round(pcb_pad.at.y - pcb_fp.at.y, 3),
            )
    except Exception as e:
        logger.debug("Could not extract KiCad pad positions by pin number: %s", e)
    return positions


def _layout_pins(
    pin_numbers: list[str],
    pin_number_to_display: dict[str, str],
    pin_number_to_functions: dict[str, list[dict]],
    component_node: fabll.Node | None = None,
) -> tuple[list[dict], float, float]:
    """Assign pins to sides using KiCad footprint positions, compute geometry.

    Uses the actual pad XY coordinates from the KiCad footprint to determine
    which side (left/right/top/bottom) each pin belongs to, matching the
    physical package layout.  Falls back to heuristic classification only
    when KiCad pad geometry is unavailable.
    """
    # ── Get real pad positions from KiCad footprint ──────────────
    side_map: dict[str, tuple[str, int]] = {}
    if component_node is not None:
        kicad_positions = _get_kicad_positions_by_pin_number(component_node)
        if kicad_positions:
            side_map = _assign_sides_from_positions(pin_numbers, kicad_positions)

    # ── Bucket pins by side ──────────────────────────────────────
    # side -> [(pin_number, display_name, category, position_index)]
    side_buckets: dict[str, list[tuple[str, str, str, int]]] = {
        "left": [],
        "right": [],
        "top": [],
        "bottom": [],
    }

    for pn in pin_numbers:
        display = pin_number_to_display.get(pn, pn)
        functions = pin_number_to_functions.get(pn, [])
        category, _heuristic_side = _classify_pin(display, functions)

        if pn in side_map:
            side, pos_idx = side_map[pn]
        else:
            side = _heuristic_side
            pos_idx = 0

        side_buckets[side].append((pn, display, category, pos_idx))

    # Sort each side by the position index from _assign_sides_from_positions
    for side in side_buckets:
        side_buckets[side].sort(key=lambda t: t[3])

    # For the schematic view, collapse top/bottom into left/right:
    # top → left (power pins often on top of IC), bottom → right
    left_pins = side_buckets["left"] + side_buckets["top"]
    right_pins = side_buckets["right"] + side_buckets["bottom"]

    # ── Compute body dimensions ──────────────────────────────────
    max_pins = max(len(left_pins), len(right_pins), 1)
    pin_spacing = 2.54
    body_height = max(max_pins * pin_spacing + 2, _MIN_BODY)
    body_width = max(14, _MIN_BODY)

    if len(pin_numbers) <= 2:
        body_width = 5.08
        body_height = 2.04

    half_w = body_width / 2

    pins: list[dict] = []

    def _add_pins(
        side_pins: list[tuple[str, str, str, int]],
        side: str,
    ) -> None:
        count = len(side_pins)
        if count == 0:
            return
        total_span = (count - 1) * pin_spacing
        start_y = total_span / 2

        for idx, (pn, display, cat, _pos) in enumerate(side_pins):
            y = start_y - idx * pin_spacing
            if side == "left":
                px = -(half_w + _PIN_STUB_LEN)
                bx = -half_w
            else:
                px = half_w + _PIN_STUB_LEN
                bx = half_w

            pins.append(
                {
                    "number": pn,
                    "name": display,
                    "side": side,
                    "electricalType": "passive",
                    "category": cat,
                    "x": round(px, 2),
                    "y": round(y, 2),
                    "bodyX": round(bx, 2),
                    "bodyY": round(y, 2),
                }
            )

    _add_pins(left_pins, "left")
    _add_pins(right_pins, "right")

    return pins, body_width, body_height


# ── Internal data structures for hierarchy building ─────────────


@dataclass
class _CompInfo:
    """Collected info for one atomic part."""

    json_id: str
    full_name: str  # Original full name from graph (e.g., "i2c_mux.package")
    json_component: dict
    # Module ancestry: list of (module_full_name, module_json_id) from root
    module_path: list[str]
    # Which "owner module" json_id this component belongs to
    owner_module_id: str | None
    # Per-pin interface mapping:
    # pin_number -> [(iface_name, signal_suffix, iface_type, is_line_level)]
    pin_to_iface: dict[str, list[tuple[str, str, str, bool]]]


@dataclass
class _ModInfo:
    """Discovered module for hierarchy building."""

    node: fabll.Node
    json_id: str
    name: str
    type_name: str
    parent_id: str | None  # json_id of parent module or None for root
    full_name: str  # Graph full name for matching
    atomic_part_count: int  # Recursive count of atomic parts inside
    source_path: str | None = None
    source_component: str | None = None
    direct_component_ids: list[str] = field(default_factory=list)
    child_module_ids: list[str] = field(default_factory=list)
    # Discovered interfaces: iface_name -> {type, signals}
    interfaces: dict[str, dict] = field(default_factory=dict)


def _normalize_component_name(raw: str | None) -> str:
    if not raw:
        return ""
    name = strip_root_hex(raw).strip().rstrip(".:")
    if "::" in name:
        name = name.rsplit("::", 1)[-1].strip()
    return name


def _module_source_from_locator(locator: str) -> tuple[str | None, str | None]:
    if not locator:
        return None, None

    source_path, locator_component = _extract_locator_source_and_component(locator)
    file_path = str(source_path) if source_path else None

    component_name = _normalize_component_name(locator_component)
    if not component_name and "::" in locator:
        component_name = _normalize_component_name(locator.rsplit("::", 1)[-1])

    return file_path, component_name or None


def _strip_internal_path_segments(path: str) -> str:
    if not path:
        return ""
    segments = [
        segment
        for segment in path.split(".")
        if segment and segment.split("[", 1)[0] not in {"package"}
    ]
    return ".".join(segments)


def _make_source_ref(file_path: str, instance_path: str) -> dict[str, str] | None:
    clean_file = file_path.strip()
    clean_instance = instance_path.strip().strip(".")
    if not clean_file or not clean_instance:
        return None
    return {
        "address": f"{clean_file}::{clean_instance}",
        "filePath": clean_file,
        "instancePath": clean_instance,
    }


def _build_instance_source_ref(
    full_name: str,
    module_by_fullname: dict[str, _ModInfo],
) -> dict[str, str] | None:
    candidates = [
        mod
        for mod in module_by_fullname.values()
        if mod.source_path
        and mod.source_component
        and (full_name == mod.full_name or full_name.startswith(mod.full_name + "."))
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda mod: len(mod.full_name), reverse=True)

    for mod in candidates:
        rel = full_name[len(mod.full_name) :]
        if rel.startswith("."):
            rel = rel[1:]
        rel = _strip_internal_path_segments(rel)
        if not rel:
            continue
        return _make_source_ref(
            mod.source_path,
            f"{mod.source_component}.{rel}",
        )

    best = candidates[0]
    return _make_source_ref(best.source_path, best.source_component)


def _append_source_segment(
    source_ref: dict[str, str] | None,
    segment: str,
) -> dict[str, str] | None:
    if not source_ref:
        return None
    file_path = source_ref.get("filePath", "").strip()
    instance_path = source_ref.get("instancePath", "").strip()
    if not file_path or not instance_path:
        return None
    clean_segment = segment.strip().strip(".")
    next_path = f"{instance_path}.{clean_segment}" if clean_segment else instance_path
    return _make_source_ref(file_path, next_path)


# ── Hierarchy discovery ─────────────────────────────────────────


def _discover_modules(app: fabll.Node) -> dict[str, _ModInfo]:
    """
    Walk the graph to find all modules and build a hierarchy tree.

    Returns a dict keyed by module json_id.
    """
    modules: dict[str, _ModInfo] = {}

    # Get all module instances
    try:
        all_module_traits = list(
            fabll.Traits.get_implementors(
                fabll.is_module.bind_typegraph(app.tg),
                g=app.g,
            )
        )
    except Exception:
        logger.debug("Could not get module instances")
        return modules

    # Build raw module info
    module_by_fullname: dict[str, _ModInfo] = {}

    for trait_node in all_module_traits:
        try:
            module_node = fabll.Traits.bind(trait_node).get_obj_raw()
            full_name = strip_root_hex(module_node.get_full_name())

            # Skip root-level hex IDs and the root app itself
            if not full_name or re.match(r"^0x[0-9A-Fa-f]+$", full_name):
                continue

            # Get type name
            type_name = full_name.split(".")[-1] if "." in full_name else full_name
            source_path: str | None = None
            source_component: str | None = None
            try:
                locator = module_node.get_trait(fabll.is_module).get_module_locator()
                source_path, source_component = _module_source_from_locator(locator)
                if source_component:
                    type_name = source_component
                elif "::" in locator:
                    type_name = _normalize_component_name(locator.split("::")[-1])
            except Exception:
                pass
            type_name = strip_root_hex(type_name)
            if not source_component:
                source_component = type_name

            # Instance name (last segment)
            name = full_name.rsplit(".", 1)[-1] if "." in full_name else full_name

            # JSON ID: dots replaced, lowered
            json_id = full_name.replace(".", "_").lower()

            info = _ModInfo(
                node=module_node,
                json_id=json_id,
                name=name,
                type_name=type_name,
                parent_id=None,  # filled in later
                full_name=full_name,
                atomic_part_count=0,
                source_path=source_path,
                source_component=source_component,
            )

            module_by_fullname[full_name] = info
            modules[json_id] = info

        except Exception as e:
            logger.debug("Error discovering module: %s", e)
            continue

    # Resolve parent IDs
    for info in modules.values():
        if "." in info.full_name:
            parent_fn = info.full_name.rsplit(".", 1)[0]
            parent = module_by_fullname.get(parent_fn)
            if parent:
                info.parent_id = parent.json_id

    return modules


def _find_owner_module(
    comp_full_name: str,
    modules: dict[str, _ModInfo],
    module_by_fullname: dict[str, _ModInfo],
) -> str | None:
    """
    For a component, find the nearest ancestor that is an "interesting" module.

    An interesting module has >= 2 atomic parts (not just a simple wrapper).
    We walk up the name hierarchy looking for the closest interesting ancestor.
    """
    parts = comp_full_name.split(".")
    # Walk from the component's parent upward
    for depth in range(len(parts) - 1, 0, -1):
        candidate = ".".join(parts[:depth])
        mod = module_by_fullname.get(candidate)
        if mod and mod.atomic_part_count >= 2:
            return mod.json_id

    return None


def _filter_lead_functions(functions: list[dict]) -> list[dict]:
    """Filter out reference-network noise from lead function traces.

    ElectricLogic signals have `.reference ~ power` connections that create
    hundreds of spurious Power-type paths through the graph.  This removes:
    - Paths containing ".reference." (e.g. "i2cs[0].scl.reference.vcc")
    - Paths ending with ".reference"
    - Paths containing "_single_electric_reference"
    """
    filtered = []
    for fn in functions:
        path = fn.get("name", "")
        if ".reference." in path or path.endswith(".reference"):
            continue
        if "_single_electric_reference" in path:
            continue
        filtered.append(fn)
    return filtered


def _pin_label_key(label: str) -> str:
    """Normalize pin labels for robust matching across naming styles."""
    cleaned = label.strip().replace("{", "").replace("}", "")
    cleaned = cleaned.replace("~", "N")
    cleaned = re.sub(r"[^A-Za-z0-9]", "", cleaned).upper()

    if cleaned in {"NRESET", "RESETN", "NRST", "RSTN"}:
        return "NRESET"
    if cleaned in {"RESET", "RST"}:
        return "RESET"
    return cleaned


def _infer_function_pin_label(fn: dict) -> str:
    """Infer the concise pin label represented by a traced function path."""
    path = fn.get("name", "")
    lower = path.lower()

    if (
        lower in {"hv", "vcc", "power.hv", "power.vcc"}
        or lower.endswith(".hv")
        or lower.endswith(".vcc")
    ):
        return "VCC"
    if (
        lower in {"lv", "gnd", "power.lv", "power.gnd"}
        or lower.endswith(".lv")
        or lower.endswith(".gnd")
    ):
        return "GND"

    return _shorten_pin_name(path)


def _filter_pin_functions_by_signal_map(
    pin_number_to_functions: dict[str, list[dict]],
    signal_names: dict[str, str],
) -> dict[str, list[dict]]:
    """Keep only function traces consistent with declared per-pin signal names.

    This removes bridged/reference artifacts where a pin picks up unrelated
    line-level paths (e.g. address lines leaking onto VCC/GND pins).
    """
    filtered: dict[str, list[dict]] = {}

    for pin_number, functions in pin_number_to_functions.items():
        target_signal = signal_names.get(pin_number)
        if not target_signal:
            filtered[pin_number] = functions
            continue

        target_key = _pin_label_key(target_signal)
        matches = [
            fn
            for fn in functions
            if _pin_label_key(_infer_function_pin_label(fn)) == target_key
        ]
        if matches:
            filtered[pin_number] = matches
            continue

        # No direct match: drop mismatched line-level continuity traces and keep
        # only non-line-level entries (if any).
        non_line = [fn for fn in functions if not fn.get("is_line_level")]
        filtered[pin_number] = non_line

    return filtered


def _resolve_locator_path(
    candidate: str,
    base_dirs: list[Path] | None = None,
) -> Path | None:
    p = Path(candidate)
    if p.is_file():
        return p.resolve()
    if p.is_absolute():
        return None

    search_dirs: list[Path] = [Path.cwd()]
    if base_dirs:
        search_dirs.extend(base_dirs)

    seen: set[Path] = set()
    for base in search_dirs:
        b = base.resolve()
        if b in seen:
            continue
        seen.add(b)
        rel = (b / p).resolve()
        if rel.is_file():
            return rel
    return None


def _extract_locator_source_and_component(locator: str) -> tuple[Path | None, str]:
    """Extract the most specific ``(source_path, component_name)`` from locator."""
    if not locator:
        return None, ""

    # Locator format can be chained with "|" segments, e.g.
    # root.ato::App.mod|subdir/mod.ato::Wrapper.pkg|parts/foo.ato::PartType.
    # The rightmost leaf is most specific, but its path can be relative to an
    # earlier segment's directory; resolve segments left→right and return the
    # deepest successfully resolved one.
    resolved_segments: list[tuple[Path, str]] = []
    search_bases: list[Path] = []

    for segment in locator.split("|"):
        seg = segment.strip()
        if ".ato" not in seg:
            continue
        if "::" in seg:
            path_text, comp_name = seg.rsplit("::", 1)
        else:
            path_text, comp_name = seg, ""

        source_path = _resolve_locator_path(path_text, base_dirs=search_bases)
        if source_path:
            clean_name = comp_name.strip().rstrip(".:")
            resolved_segments.append((source_path, clean_name))
            search_bases.insert(0, source_path.parent)

    if resolved_segments:
        return resolved_segments[-1]

    # Fallback: use rightmost .ato-like token if present.
    matches = re.findall(r"([^\s|:]+\.ato)", locator)
    for match in reversed(matches):
        source_path = _resolve_locator_path(match, base_dirs=search_bases)
        if source_path:
            return source_path, ""

    return None, ""


def _candidate_component_names(raw_name: str) -> list[str]:
    """Generate likely component declaration names from locator tail text."""
    names: list[str] = []

    def _add(value: str) -> None:
        value = value.strip()
        if "::" in value:
            value = value.rsplit("::", 1)[-1]
        value = value.rstrip(".:")
        if value and value not in names:
            names.append(value)

    _add(raw_name)
    for seg in raw_name.split("|"):
        _add(seg)
        if "::" in seg:
            _add(seg.rsplit("::", 1)[-1])

    snapshot = list(names)
    for name in snapshot:
        if "." in name:
            _add(name.rsplit(".", 1)[-1])

    return names


def _extract_declared_signals_from_source(
    source_path: Path,
    locator_component_name: str,
) -> dict[str, str]:
    """Parse ``[signal] NAME ~ pin N`` lines from a component declaration."""
    try:
        lines = source_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}

    signal_re = re.compile(
        r"^\s*(?:signal\s+)?([A-Za-z_~][A-Za-z0-9_~\[\]\.\-/]*)\s*~\s*pin\s+([A-Za-z0-9_]+)\s*$"
    )

    comp_decl_re = re.compile(
        r"^(?P<indent>\s*)component\s+(?P<name>[A-Za-z_~][A-Za-z0-9_~\[\]\.]*)"
        r"(?:\s*<[^>]*>)?\s*:\s*$"
    )

    def _extract_for_component(candidate_name: str) -> dict[str, str]:
        comp_re = re.compile(
            rf"^(?P<indent>\s*)component\s+{re.escape(candidate_name)}(?:\s*<[^>]*>)?\s*:\s*$"
        )
        start_idx: int | None = None
        base_indent = 0

        for idx, line in enumerate(lines):
            m = comp_re.match(line)
            if m:
                start_idx = idx + 1
                base_indent = len(m.group("indent"))
                break

        if start_idx is None:
            return {}

        pin_to_signal: dict[str, str] = {}
        for line in lines[start_idx:]:
            stripped = line.strip()
            if not stripped:
                continue

            indent = len(line) - len(line.lstrip())
            if indent <= base_indent and not stripped.startswith("#"):
                break

            m = signal_re.match(line)
            if not m:
                continue

            signal_name, pin_number = m.groups()
            if pin_number not in pin_to_signal:
                pin_to_signal[pin_number] = signal_name

        return pin_to_signal

    for candidate_name in _candidate_component_names(locator_component_name):
        pin_to_signal = _extract_for_component(candidate_name)
        if pin_to_signal:
            return pin_to_signal

    # Fallback: when locator component names are unreliable, use the single
    # component declaration in the file (common for generated part files).
    declared_components: list[str] = []
    for line in lines:
        m = comp_decl_re.match(line)
        if not m:
            continue
        name = m.group("name").strip().rstrip(".:")
        if name and name not in declared_components:
            declared_components.append(name)
    if len(declared_components) == 1:
        pin_to_signal = _extract_for_component(declared_components[0])
        if pin_to_signal:
            return pin_to_signal

    return {}


def _derive_display_name(
    pad_name: str, lead_name: str, filtered_functions: list[dict]
) -> str:
    """Derive a meaningful display name from lead functions.

    Triggers when the lead name is uninformative:
    - Just a pad number (e.g. "1", "24")  → IC package pin
    - Generic unnamed lead (e.g. "unnamed[0]") → passive component
    """
    is_numeric = lead_name.isdigit()
    is_unnamed = lead_name.startswith("unnamed")
    if not is_numeric and not is_unnamed:
        return lead_name

    if not filtered_functions:
        return lead_name

    power_fns = [f for f in filtered_functions if f.get("type") == "Power"]
    non_power = [f for f in filtered_functions if f.get("type") != "Power"]

    if is_unnamed:
        # Passive components: strongly prefer Power classification.
        # Non-power functions on passives are usually noise from the
        # reference network (e.g. address lines leaking through).
        if power_fns:
            for fn in power_fns:
                name = fn.get("name", "")
                if name.endswith(".hv") or name.endswith(".vcc"):
                    return "VCC"
                if name.endswith(".lv") or name.endswith(".gnd"):
                    return "GND"
        if non_power:
            best = min(non_power, key=lambda f: len(f.get("name", "")))
            return best.get("name", lead_name)
        return lead_name

    # IC packages (numeric lead names): prefer signal names.
    # If only Power functions exist, it's a dedicated power pin.
    if non_power:
        best = min(non_power, key=lambda f: len(f.get("name", "")))
        name = best.get("name", lead_name)
        if name.endswith(".line"):
            name = name[:-5]
        return _shorten_pin_name(name)

    # Only power functions — dedicated power pin
    if power_fns:
        for fn in power_fns:
            name = fn.get("name", "")
            if name.endswith(".hv") or name.endswith(".vcc"):
                return "VCC"
            if name.endswith(".lv") or name.endswith(".gnd"):
                return "GND"

    return lead_name


def _extract_signal_names(
    component_node: fabll.Node,
) -> dict[str, str]:
    """Extract pin-number → signal-name mappings from a component definition.

    Preferred path:
    - parse authoritative declarations from source locator text:
      ``signal NAME ~ pin N``.

    Fallback path:
    - infer from strict lead→signal direct-neighbor graph matches:
      signal interface child of the same component with path length == 1.

    Ambiguous fallback matches are ignored rather than guessed.

    Returns: {pin_number: signal_name}
    """
    try:
        if component_node.has_trait(fabll.is_module):
            locator = component_node.get_trait(fabll.is_module).get_module_locator()
            source_path, locator_component = _extract_locator_source_and_component(
                locator
            )
            if source_path:
                declared = _extract_declared_signals_from_source(
                    source_path,
                    locator_component,
                )
                if declared:
                    return declared
    except Exception:
        pass

    pin_to_signal: dict[str, str] = {}
    try:
        # Collect signal children: non-lead, non-private, non-numeric
        # direct interface children of the component
        signal_children: dict[str, fabll.Node] = {}
        children = component_node.get_children(
            direct_only=True,
            types=fabll.Node,
        )
        for child in children:
            child_name = child.get_full_name().rsplit(".", 1)[-1]
            if child_name.startswith("_") or child_name.startswith("pad_"):
                continue
            if child_name.isdigit():
                continue
            if not child.has_trait(fabll.is_interface):
                continue
            signal_children[child_name] = child

        if not signal_children:
            return pin_to_signal

        # Collect leads with associated pads
        lead_nodes = component_node.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.Lead.is_lead,
        )
        leads_with_pads = [
            lead
            for lead in lead_nodes
            if lead.get_trait(F.Lead.is_lead).has_trait(F.Lead.has_associated_pads)
        ]

        # For each lead, find directly-connected same-level signal children.
        for lead_node in leads_with_pads:
            lead_trait = lead_node.get_trait(F.Lead.is_lead)
            if not lead_trait.has_trait(fabll.is_interface):
                continue
            lead_iface = lead_trait.get_trait(fabll.is_interface)
            try:
                connected = lead_iface.get_connected(include_self=False)
            except Exception:
                continue

            matches: set[str] = set()
            for connected_node, path in connected.items():
                # Require a direct connection to avoid traversing bridged nets.
                try:
                    if path.length != 1:
                        continue
                except Exception:
                    continue

                # Connected node must be a direct child of this component.
                try:
                    parent = connected_node.get_parent()
                    if not parent or not parent[0].is_same(component_node):
                        continue
                except Exception:
                    continue

                # Check if this connected node IS one of our signal children.
                for sig_name, sig_node in signal_children.items():
                    try:
                        if connected_node.is_same(sig_node):
                            matches.add(sig_name)
                            break
                    except Exception:
                        continue

            best_signal: str | None = None
            if len(matches) == 1:
                best_signal = next(iter(matches))
            elif matches:
                # Only accept ambiguous sets when one exactly matches the lead
                # instance name; otherwise skip to avoid accidental mislabeling.
                lead_name = lead_trait.get_lead_name()
                if lead_name in matches:
                    best_signal = lead_name

            if not best_signal:
                continue

            assoc_pads = lead_trait.get_trait(F.Lead.has_associated_pads).get_pads()
            for pad in assoc_pads:
                try:
                    pin_number = str(pad.pad_number)
                    if pin_number not in pin_to_signal:
                        pin_to_signal[pin_number] = best_signal
                except Exception:
                    continue

    except Exception:
        pass
    return pin_to_signal


def _shorten_pin_name(name: str) -> str:
    """Convert a function path to a concise KiCad-style component pin name.

    Examples:
        i2cs[0].scl  → SC0
        i2c.sda      → SDA
        addressor.address_lines[0] → A0
        reset        → ~RESET
    """
    if name in ("VCC", "GND"):
        return name

    # I2C with array index: i2cs[N].scl → SC{N}
    m = re.match(r"\w+\[(\d+)\]\.(scl|sda)$", name)
    if m:
        idx, sig = m.groups()
        return f"{'SC' if sig == 'scl' else 'SD'}{idx}"

    # I2C without index: i2c.scl → SCL
    m = re.match(r"i2c\.(scl|sda)$", name)
    if m:
        return m.group(1).upper()

    # SPI: spi.mosi → MOSI
    m = re.match(r"\w*spi\w*\.(sclk|mosi|miso|cs)$", name, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    # UART: uart.tx → TX
    m = re.match(r"\w*uart\w*\.(tx|rx)$", name, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    # Trailing array index: foo.bar_baz[N] → abbreviate
    m = re.match(r".*?(\w+)\[(\d+)\]$", name)
    if m:
        seg, idx = m.groups()
        if "addr" in seg.lower() or "address" in seg.lower():
            return f"A{idx}"
        abbr = seg[:4].upper() if len(seg) > 4 else seg.upper()
        return f"{abbr}{idx}"

    # Single word
    if "." not in name:
        lower = name.lower()
        if "reset" in lower or "rst" in lower:
            return "~RESET"
        return name

    # Dotted fallback: last segment
    return name.rsplit(".", 1)[-1]


def _extract_pin_interfaces(
    pin_number_to_functions: dict[str, list[dict]],
) -> dict[str, list[tuple[str, str, str, bool]]]:
    """
    From lead_functions, extract which module interfaces each pin connects to.

    Returns:
      {pin_number: [
          (interface_name, signal_suffix, interface_type, is_line_level),
          ...
      ]}

    Expects pre-filtered functions (reference noise already removed).
    """
    result: dict[str, list[tuple[str, str, str, bool]]] = {}

    for pin_number, functions in pin_number_to_functions.items():
        mappings: list[tuple[str, str, str, bool]] = []
        seen: set[tuple[str, str, str, bool]] = set()

        for fn in functions:
            # `name` is display-friendly (often strips trailing `.line`),
            # while `raw_name` preserves full continuity semantics.
            path = fn.get("name", "")
            raw_path = fn.get("raw_name", path)
            fn_type = fn.get("type", "Signal")
            parts = path.split(".")
            is_line_level = bool(fn.get("is_line_level", False)) or any(
                seg == "line" for seg in raw_path.split(".")
            )

            if len(parts) >= 2:
                iface_name = parts[0]
                signal = parts[1]

                # For deeply nested paths like "addressor.address_lines[0].line",
                # the first segment ("addressor") is a parent module, not the
                # interface itself.  Check if a deeper segment has an array
                # index — that segment is the actual interface (e.g.
                # "address_lines[0]").
                if len(parts) >= 3:
                    for seg in parts[1:]:
                        if re.search(r"\[\d+\]", seg):
                            iface_name = seg
                            # Signal is whatever comes after this segment
                            seg_idx = parts.index(seg)
                            remaining = parts[seg_idx + 1 :]
                            signal = ".".join(remaining) if remaining else ""
                            break

                if signal in ("line",):
                    signal = ""
                    is_line_level = True
                key = (iface_name, signal, fn_type, is_line_level)
                if key not in seen:
                    seen.add(key)
                    mappings.append(key)
            elif len(parts) == 1 and path:
                # Single-name interface (e.g. "reset")
                key = (path, "", fn_type, False)
                if key not in seen:
                    seen.add(key)
                    mappings.append(key)

        if mappings:
            result[pin_number] = mappings

    return result


def _mark_passthrough_interfaces(iface_map: dict[str, dict]) -> None:
    """Mark GPIO/control interfaces that bridge shared physical pins."""
    bindings_by_comp_pin: dict[tuple[str, str], list[_ResolvedInterfacePin]] = (
        defaultdict(list)
    )

    for iface_name, iface_data in iface_map.items():
        pin_map = iface_data.get("pin_map", {})
        category = str(iface_data.get("category", "signal"))
        iface_type = str(iface_data.get("type", "Signal"))
        for comp_id, comp_map in pin_map.items():
            for pin_number, binding in comp_map.items():
                iface_id, signal_suffix, is_line_level = binding
                bindings_by_comp_pin[(comp_id, pin_number)].append(
                    _ResolvedInterfacePin(
                        iface_id=iface_id or iface_name,
                        signal_suffix=signal_suffix,
                        is_line_level=is_line_level,
                        category=category,
                        iface_type=iface_type,
                    )
                )

    for bindings in bindings_by_comp_pin.values():
        if len(bindings) < 2:
            continue
        bridge = next((b for b in bindings if _is_passthrough_binding(b)), None)
        if not bridge:
            continue
        iface_data = iface_map.get(bridge.iface_id)
        if iface_data is None:
            continue
        iface_data["pass_through"] = True


# ── Interface pin layout for modules ────────────────────────────


def _build_interface_pins(
    interfaces: dict[str, dict],
    source_ref: dict[str, str] | None = None,
) -> tuple[list[dict], float, float]:
    """
    Build interface-level port dicts for a module and compute body dimensions.

    Each interface becomes a single port on the module block (not expanded
    into individual signals).  For example, an I2C interface shows as one
    ``i2c`` port rather than separate SCL/SDA pins.  Parts (components with
    footprints) still show individual pins via ``_layout_pins``.

    Returns (interface_pins, body_width, body_height).
    """
    left_pins: list[dict] = []
    right_pins: list[dict] = []

    for iface_name, iface_info in sorted(
        interfaces.items(), key=lambda kv: natural_sort_key(kv[0])
    ):
        iface_type = iface_info.get("type", "Signal")
        category = iface_info.get("category", "signal")

        # Determine side: power/ground on left, buses/signals on right
        side = "left" if category in _LEFT_CATEGORIES else "right"

        pin_data = {
            "id": iface_name,
            "name": iface_name,
            "side": side,
            "category": category,
            "interfaceType": iface_type.replace("Power", "ElectricPower"),
        }
        pin_source = _append_source_segment(source_ref, iface_name)
        if pin_source:
            pin_data["source"] = pin_source
        if iface_info.get("pass_through"):
            pin_data["passThrough"] = True

        # Include per-signal breakdown when >=2 real signals exist
        real_signals = sorted(s for s in iface_info.get("signals", set()) if s)
        if len(real_signals) >= 2:
            pin_data["signals"] = real_signals

        if side == "left":
            left_pins.append(pin_data)
        else:
            right_pins.append(pin_data)

    # Compute body dimensions
    pin_spacing = 3.0
    max_side = max(len(left_pins), len(right_pins), 1)
    body_height = max(max_side * pin_spacing + 4, 10)

    # Width based on longest pin name
    max_name_len = max((len(p["name"]) for p in left_pins + right_pins), default=3)
    body_width = max(max_name_len * 1.2 + 8, 18)

    half_w = body_width / 2

    final_pins: list[dict] = []

    def _place(pins: list[dict], side: str) -> None:
        count = len(pins)
        if count == 0:
            return
        total_span = (count - 1) * pin_spacing
        start_y = total_span / 2

        for idx, p in enumerate(pins):
            y = start_y - idx * pin_spacing
            if side == "left":
                px = -(half_w + _PIN_STUB_LEN)
                bx = -half_w
            else:
                px = half_w + _PIN_STUB_LEN
                bx = half_w

            entry = {
                "id": p["id"],
                "name": p["name"],
                "side": side,
                "category": p["category"],
                "interfaceType": p["interfaceType"],
                "x": round(px, 2),
                "y": round(y, 2),
                "bodyX": round(bx, 2),
                "bodyY": round(y, 2),
            }
            if "signals" in p:
                entry["signals"] = p["signals"]
            if p.get("passThrough"):
                entry["passThrough"] = True
            if "source" in p:
                entry["source"] = p["source"]
            final_pins.append(entry)

    _place(left_pins, "left")
    _place(right_pins, "right")

    return final_pins, round(body_width, 2), round(body_height, 2)


# ── Net scoping ─────────────────────────────────────────────────


def _coerce_net_type_for_line_level(net_type: str, is_line_level: bool) -> str:
    """Line-level links represent electrical continuity, not logical signal identity."""
    if not is_line_level:
        return net_type
    if net_type in ("power", "ground"):
        return net_type
    return "electrical"


def _resolve_interface_bindings(
    module_id: str,
    comp_id: str,
    pin_number: str,
    module_interfaces: dict[str, dict[str, dict]],
) -> list[_ResolvedInterfacePin]:
    """Resolve all module interface bindings for a component pin."""
    ifaces = module_interfaces.get(module_id, {})
    if not ifaces:
        return []

    resolved: list[_ResolvedInterfacePin] = []

    for _iface_name, iface_data in ifaces.items():
        pin_map = iface_data.get("pin_map", {})
        comp_map = pin_map.get(comp_id, {})
        binding = comp_map.get(pin_number)
        if not binding:
            continue

        iface_id, signal_suffix, is_line_level = binding
        resolved.append(
            _ResolvedInterfacePin(
                iface_id=iface_id,
                signal_suffix=signal_suffix,
                is_line_level=is_line_level,
                category=str(iface_data.get("category", "signal")),
                iface_type=str(iface_data.get("type", "Signal")),
            )
        )

    return resolved


def _resolve_interface_binding(
    module_id: str,
    comp_id: str,
    pin_number: str,
    module_interfaces: dict[str, dict[str, dict]],
) -> _ResolvedInterfacePin | None:
    """Resolve one interface binding for parent-level pin collapsing."""
    bindings = _resolve_interface_bindings(
        module_id=module_id,
        comp_id=comp_id,
        pin_number=pin_number,
        module_interfaces=module_interfaces,
    )
    if not bindings:
        return None
    return bindings[0]


def _add_port_pins_to_internal_net(
    net: dict,
    module_id: str,
    module_interfaces: dict[str, dict[str, dict]],
) -> tuple[dict, bool]:
    """Add synthetic port pin references to a module-internal net.

    For each component pin in the net that maps to a module interface via
    the pin_map, add a corresponding port pin so the frontend can draw
    wires from the port to the internal component.
    """
    ifaces = module_interfaces.get(module_id, {})
    if not ifaces:
        return net, False

    seen_refs: set[tuple[str, str]] = set()
    has_interface_binding = False
    has_line_level_binding = False
    raw_pin_count = len(net.get("pins", []))

    for pin in net["pins"]:
        comp_id = pin.get("componentId", "")
        pad_name = pin.get("pinNumber", "")
        bindings = _resolve_interface_bindings(
            module_id=module_id,
            comp_id=comp_id,
            pin_number=pad_name,
            module_interfaces=module_interfaces,
        )
        if not bindings:
            continue

        has_interface_binding = True
        has_line_level_binding = has_line_level_binding or any(
            b.is_line_level for b in bindings
        )

        bridge = None
        if len(bindings) >= 2:
            bridge = next((b for b in bindings if _is_passthrough_binding(b)), None)

        if bridge:
            added_non_bridge = False
            for binding in bindings:
                if binding == bridge:
                    continue
                pin_number = binding.signal_suffix if binding.signal_suffix else "1"
                seen_refs.add((binding.iface_id, pin_number))
                added_non_bridge = True

            if added_non_bridge:
                # Front/back pins for pass-through bridges.
                seen_refs.add((bridge.iface_id, "1"))
                seen_refs.add((bridge.iface_id, "2"))
                continue

        for binding in bindings:
            pin_number = binding.signal_suffix if binding.signal_suffix else "1"
            seen_refs.add((binding.iface_id, pin_number))

    if not seen_refs:
        return net, False

    enhanced_pins = list(net["pins"])
    for iface_id, pin_number in seen_refs:
        enhanced_pins.append(
            {
                "componentId": iface_id,
                "pinNumber": pin_number,
            }
        )

    return (
        {
            **net,
            "type": _coerce_net_type_for_line_level(
                net.get("type", "signal"),
                has_line_level_binding or (has_interface_binding and raw_pin_count < 2),
            ),
            "pins": _dedup_pins(enhanced_pins),
        },
        has_interface_binding,
    )


def _scope_nets(
    all_nets: list[dict],
    comp_to_owner: dict[str, str | None],
    module_interfaces: dict[str, dict[str, dict]],
) -> dict[str | None, list[dict]]:
    """
    Assign each net to its appropriate hierarchy level.

    For each net:
    - If all pins are in the same module → internal net at that module's level
    - If pins span multiple modules → net at the parent (root) level,
      with module pins mapped to interface pin IDs

    Returns: {owner_module_id_or_None: [net_dicts]}
    """
    scoped: dict[str | None, list[dict]] = defaultdict(list)

    for net in all_nets:
        pins = net["pins"]
        if len(pins) < 1:
            continue

        # Group pins by their owner module
        pins_by_module: dict[str | None, list[dict]] = defaultdict(list)
        for pin in pins:
            owner = comp_to_owner.get(pin["componentId"])
            pins_by_module[owner].append(pin)

        unique_owners = set(pins_by_module.keys())

        if len(unique_owners) == 1:
            # All pins in the same module (or all at root)
            owner = next(iter(unique_owners))
            if owner is not None:
                # Add synthetic port pins for internal pins that map to
                # module interface pins, so the frontend can draw wires
                # between ports and internal components.
                enhanced, _ = _add_port_pins_to_internal_net(
                    net, owner, module_interfaces
                )
                if len(enhanced["pins"]) >= 2:
                    scoped[owner].append(enhanced)
            else:
                if len(net["pins"]) >= 2:
                    scoped[owner].append(net)
        else:
            # Net crosses module boundaries
            # Create a root-level net with interface pin references
            root_pins: list[dict] = []
            root_has_line_level = False

            for owner, owner_pins in pins_by_module.items():
                if owner is None:
                    # Pins at root level stay as-is
                    root_pins.extend(owner_pins)
                else:
                    # For pins inside a module, map to the module's interface pin
                    # The module ID becomes the componentId, and we need to find
                    # which interface pin this net goes through
                    result = _find_interface_pin_for_net(
                        owner, owner_pins, module_interfaces
                    )
                    if result:
                        iface_id = result.iface_id
                        signal_name = result.signal_suffix
                        root_has_line_level = (
                            root_has_line_level or result.is_line_level
                        )
                        # Parent level — consolidated single pin on module block
                        root_pins.append(
                            {
                                "componentId": owner,
                                "pinNumber": iface_id,
                            }
                        )
                        # Internal level — per-signal pin number
                        # Use signal name so nets route to individual breakout
                        # port dots; fall back to "1" for single-signal interfaces
                        internal_pin_number = signal_name if signal_name else "1"
                    else:
                        iface_id = None
                        internal_pin_number = "1"

                    # Also create an internal net for the module connecting
                    # the port to the internal component pins
                    internal_pins = list(owner_pins)
                    internal_pins.append(
                        {
                            "componentId": iface_id or f"port_{owner}",
                            "pinNumber": internal_pin_number,
                        }
                    )
                    if len(internal_pins) >= 2:
                        internal_net = {
                            "id": f"{net['id']}__{owner}",
                            "name": net["name"],
                            "type": _coerce_net_type_for_line_level(
                                net.get("type", "signal"),
                                result.is_line_level if result else False,
                            ),
                            "pins": internal_pins,
                        }
                        scoped[owner].append(internal_net)

            if len(root_pins) >= 2:
                root_net = {
                    "id": net["id"],
                    "name": net["name"],
                    "type": _coerce_net_type_for_line_level(
                        net.get("type", "signal"), root_has_line_level
                    ),
                    "pins": _dedup_pins(root_pins),
                }
                scoped[None].append(root_net)

    _add_missing_interface_nets(scoped, module_interfaces)

    return dict(scoped)


def _find_interface_pin_for_net(
    module_id: str,
    pins_inside: list[dict],
    module_interfaces: dict[str, dict[str, dict]],
) -> _ResolvedInterfacePin | None:
    """
    For a net that enters a module, find which interface pin it maps to.

    Uses the interface pin map that was built from lead_functions data.
    """
    for pin in pins_inside:
        pin_number = pin.get("pinNumber", "")
        comp_id = pin.get("componentId", "")
        binding = _resolve_interface_binding(
            module_id=module_id,
            comp_id=comp_id,
            pin_number=pin_number,
            module_interfaces=module_interfaces,
        )
        if binding:
            return binding

    return None


def _interface_net_type(iface_data: dict) -> str:
    """Infer net type from interface metadata when no graph net is available."""
    category = str(iface_data.get("category", "signal")).lower()
    iface_type = str(iface_data.get("type", "Signal")).lower()

    if category == "ground":
        return "ground"
    if category == "power" or iface_type in ("power", "electricpower"):
        return "power"
    if category in ("i2c", "spi", "uart") or iface_type in ("i2c", "spi", "uart"):
        return "bus"
    return "signal"


def _net_has_all_refs(net: dict, refs: set[tuple[str, str]]) -> bool:
    net_refs = {(p.get("componentId", ""), p.get("pinNumber", "")) for p in net["pins"]}
    return refs.issubset(net_refs)


def _add_missing_interface_nets(
    scoped: dict[str | None, list[dict]],
    module_interfaces: dict[str, dict[str, dict]],
) -> None:
    """Synthesize internal port↔component nets absent from pad-derived netlist.

    Some `.line` connections do not materialize as `F.Net` pad nets. Recover those
    links from interface pin maps so the viewer can still draw explicit tracks
    between module ports and component pins.
    """
    for module_id, iface_map in module_interfaces.items():
        module_nets = scoped.setdefault(module_id, [])

        for iface_name, iface_data in iface_map.items():
            pin_map = iface_data.get("pin_map", {})
            members_by_pin: dict[str, list[tuple[str, str, bool]]] = defaultdict(list)

            for comp_id, comp_map in pin_map.items():
                for pin_number, binding in comp_map.items():
                    _iface_id, signal_suffix, is_line_level = binding
                    port_pin_number = signal_suffix if signal_suffix else "1"
                    members_by_pin[port_pin_number].append(
                        (comp_id, pin_number, is_line_level)
                    )

            for port_pin_number, members in members_by_pin.items():
                if not members:
                    continue

                # Synthesize only true line-level continuity links.
                line_members = [
                    (comp_id, pin_number)
                    for comp_id, pin_number, is_line_level in members
                    if is_line_level
                ]
                if not line_members:
                    continue

                port_ref = (iface_name, port_pin_number)
                comp_refs = set(line_members)
                expected_refs = set(comp_refs)
                expected_refs.add(port_ref)

                if any(_net_has_all_refs(net, expected_refs) for net in module_nets):
                    continue

                pins = [
                    {"componentId": comp_id, "pinNumber": pin_number}
                    for comp_id, pin_number in sorted(comp_refs)
                ]
                pins.append({"componentId": iface_name, "pinNumber": port_pin_number})
                pins = _dedup_pins(pins)
                if len(pins) < 2:
                    continue

                base_type = _interface_net_type(iface_data)
                net_type = _coerce_net_type_for_line_level(base_type, True)

                suffix = (
                    f".{port_pin_number}"
                    if port_pin_number and port_pin_number != "1"
                    else ""
                )
                net_name = f"{iface_name}{suffix}"
                net_id = re.sub(
                    r"[^a-zA-Z0-9_]",
                    "_",
                    f"__iface__{module_id}__{iface_name}__{port_pin_number}",
                )

                module_nets.append(
                    {
                        "id": net_id,
                        "name": net_name,
                        "type": net_type,
                        "pins": pins,
                    }
                )
                logger.debug(
                    "Synthesized interface net in %s: %s (%s) pins=%s",
                    module_id,
                    net_name,
                    net_type,
                    [f"{p['componentId']}:{p['pinNumber']}" for p in pins],
                )


def _dedup_pins(pins: list[dict]) -> list[dict]:
    """Deduplicate net pins by componentId:pinNumber."""
    seen: set[str] = set()
    result: list[dict] = []
    for p in pins:
        key = f"{p['componentId']}:{p['pinNumber']}"
        if key not in seen:
            seen.add(key)
            result.append(p)
    return result


# ── Sub-PCB schematic position reuse ────────────────────────────


def _remap_position_key(
    key: str,
    src_root_id: str,
    tgt_module_id: str,
    tgt_path_prefix: str,
) -> str | None:
    """Remap a position key from a source .ato_sch to the target hierarchy.

    In the source ``.ato_sch``, positions are keyed as ``path:item_id``:

    - ``__root__:src_root_id`` — the module block on the source root sheet.
      Skipped because the user positions this block themselves in the target.
    - ``src_root_id:src_root_id_comp`` — items on the source module's internal
      sheet.  The item_id has the source module's json_id as prefix.
      Remapped to ``tgt_path_prefix:tgt_module_id_comp``.
    - ``src_root_id/child:child_comp`` — items inside a child sub-sheet.
      Remapped to ``tgt_path_prefix/tgt_module_id_child:tgt_module_id_comp``.

    Returns the remapped key, or ``None`` if the key cannot be mapped.
    """
    if ":" not in key:
        return None

    path_part, item_id = key.split(":", 1)

    # Skip __root__ positions — these are placements of modules on the
    # source's root sheet, not internal layout we want to reuse.
    if path_part == "__root__":
        return None

    # Remap item ID: strip the source module's json_id prefix and replace
    # with the target module's json_id.
    # e.g. "i2c_mux_decoupling_caps_0" → strip "i2c_mux_" → "decoupling_caps_0"
    #      → prepend "my_mux_" → "my_mux_decoupling_caps_0"
    # For interface port IDs (e.g. "power", "i2c") that don't have the
    # source prefix, just prepend the target prefix.
    src_prefix = src_root_id + "_"
    if item_id.startswith(src_prefix):
        item_suffix = item_id[len(src_prefix) :]
        new_item_id = f"{tgt_module_id}_{item_suffix}"
    else:
        # Interface port or item without source prefix — just use as-is
        # (ports like "power", "i2c" don't get module prefixes in json)
        new_item_id = item_id

    # Remap path: the source module's own path becomes the target path prefix,
    # and any child sub-paths get the target module id prepended.
    if path_part == src_root_id:
        # Source module's internal sheet → target module's internal sheet
        new_path = tgt_path_prefix
    else:
        # Nested sub-sheet under the source module.
        # Strip the source root prefix if present, then remap segments.
        if path_part.startswith(src_root_id + "/"):
            child_path = path_part[len(src_root_id) + 1 :]
        else:
            child_path = path_part

        # Remap child path segments similarly: strip source prefix, add target
        src_segments = child_path.split("/")
        tgt_segments = []
        for seg in src_segments:
            if seg.startswith(src_prefix):
                tgt_segments.append(f"{tgt_module_id}_{seg[len(src_prefix) :]}")
            else:
                tgt_segments.append(seg)
        new_path = tgt_path_prefix + "/" + "/".join(tgt_segments)

    return f"{new_path}:{new_item_id}"


def _build_module_path(
    mod_id: str,
    all_modules: dict[str, _ModInfo],
    interesting_module_ids: set[str],
) -> str:
    """Build the pathKey for a module's internal sheet.

    Walks from the module up through *interesting* ancestor modules,
    collecting json_ids.  Only interesting modules (those with their own
    sheets) participate in the navigation path.

    Result: ``grandparent/parent/module`` or just ``module`` for root-level.
    """
    parts: list[str] = []
    current: str | None = mod_id
    while current and current in interesting_module_ids:
        mod = all_modules.get(current)
        if not mod:
            break
        parts.append(mod.json_id)
        current = mod.parent_id
    parts.reverse()
    return "/".join(parts) if parts else mod_id


def _load_subpcb_schematic_positions(
    all_modules: dict[str, _ModInfo],
    interesting_module_ids: set[str],
    existing_positions: dict[str, dict],
) -> dict[str, dict]:
    """Load schematic positions from source .ato_sch files for sub-PCB modules.

    For each interesting module that has a ``has_subpcb`` trait, looks for
    a ``.ato_sch`` file next to the ``.kicad_pcb``, loads its positions,
    remaps the keys to the target hierarchy, and returns the merged dict.

    Existing (user-saved) positions take priority — only missing keys are
    filled from the source.
    """
    import json as _json

    try:
        from atopile.layout import has_subpcb
    except ImportError:
        return {}

    merged: dict[str, dict] = {}

    for mod_id in interesting_module_ids:
        mod = all_modules.get(mod_id)
        if not mod or not mod.node:
            continue

        # Check for has_subpcb trait
        if not mod.node.has_trait(has_subpcb):
            continue

        try:
            subpcbs = mod.node.get_trait(has_subpcb).subpcb
        except Exception:
            continue

        # Try each SubPCB path for a matching .ato_sch
        for subpcb in subpcbs:
            try:
                pcb_path = subpcb.get_path()
                ato_sch_path = pcb_path.with_suffix(".ato_sch")
                if not ato_sch_path.exists():
                    continue

                src_data = _json.loads(ato_sch_path.read_text(encoding="utf-8"))

                # Only process v2 format
                if src_data.get("version") != "2.0":
                    continue

                src_positions = src_data.get("positions", {})
                if not src_positions:
                    continue

                # Find the source root module ID — the first module listed
                # in the source's root sheet (the entry point module)
                src_root = src_data.get("root", {})
                src_root_modules = src_root.get("modules", [])
                if not src_root_modules:
                    continue
                src_root_id = src_root_modules[0].get("id", "")
                if not src_root_id:
                    continue

                # Build the target path prefix for this module
                tgt_path_prefix = _build_module_path(
                    mod_id, all_modules, interesting_module_ids
                )

                # Remap each source position key
                for src_key, pos_data in src_positions.items():
                    new_key = _remap_position_key(
                        src_key, src_root_id, mod.json_id, tgt_path_prefix
                    )
                    if new_key is None:
                        continue
                    # User's existing positions take priority
                    if new_key in existing_positions:
                        continue
                    if new_key not in merged:
                        merged[new_key] = pos_data

                # Found a valid .ato_sch — stop trying other SubPCB paths
                break

            except Exception as e:
                logger.debug(
                    "Could not load sub-PCB schematic from %s: %s",
                    subpcb,
                    e,
                )
                continue

    if merged:
        logger.info(
            "Injected %d schematic positions from sub-PCB packages", len(merged)
        )

    return merged


# ── Main export function ────────────────────────────────────────


def export_schematic_json(
    app: fabll.Node,
    solver: Solver,
    *,
    json_path: Path,
) -> None:
    """
    Export hierarchical schematic data (v2 format).

    Walks the module hierarchy, groups atomic parts into modules,
    identifies module interfaces from lead function tracing,
    and scopes nets to the appropriate hierarchy level.
    """

    # ═══════════════════════════════════════════════════════════════
    # Phase 1: Discover modules
    # ═══════════════════════════════════════════════════════════════

    all_modules = _discover_modules(app)

    logger.info(
        "Discovered %d modules: %s",
        len(all_modules),
        [m.full_name for m in list(all_modules.values())[:15]],
    )
    module_by_fullname = {m.full_name: m for m in all_modules.values()}

    # ═══════════════════════════════════════════════════════════════
    # Phase 2: Collect components (picked/atomic parts with footprints)
    # ═══════════════════════════════════════════════════════════════

    # Collect from both:
    # - picked parts (includes auto-picked parts)
    # - explicit atomic parts
    # and deduplicate by full name.
    trait_nodes = []
    try:
        trait_nodes.extend(
            fabll.Traits.get_implementors(
                F.Pickable.has_part_picked.bind_typegraph(app.tg),
                g=app.g,
            )
        )
    except Exception:
        pass
    try:
        trait_nodes.extend(
            fabll.Traits.get_implementors(
                F.is_atomic_part.bind_typegraph(app.tg),
                g=app.g,
            )
        )
    except Exception:
        pass

    fp_nodes_by_name: dict[str, fabll.Node] = {}
    for trait_node in trait_nodes:
        try:
            component_node = fabll.Traits.bind(trait_node).get_obj_raw()
            if not component_node.has_trait(F.Footprints.has_associated_footprint):
                continue
            comp_full = strip_root_hex(component_node.get_full_name())
            if comp_full not in fp_nodes_by_name:
                fp_nodes_by_name[comp_full] = component_node
        except Exception:
            continue

    # Fallback for unexpected graphs: keep previous broad behavior.
    if not fp_nodes_by_name:
        for node in app.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.Footprints.has_associated_footprint,
        ):
            try:
                comp_full = strip_root_hex(node.get_full_name())
                if comp_full not in fp_nodes_by_name:
                    fp_nodes_by_name[comp_full] = node
            except Exception:
                continue

    fp_nodes = list(fp_nodes_by_name.values())

    logger.info("Found %d components with footprints", len(fp_nodes))

    if not fp_nodes:
        logger.info("No components found, writing empty schematic JSON")
        write_json(
            {
                "version": "2.0",
                "root": {"modules": [], "components": [], "nets": []},
            },
            json_path,
        )
        return

    comp_infos: list[_CompInfo] = []
    # Use pad nodes directly as keys — Node.__hash__ returns a stable graph
    # UUID and Node.__eq__ uses is_same(), so this works across wrapper
    # instances (unlike id() which varies per Python object).
    pad_to_comp: dict[fabll.Node, str] = {}
    pad_to_number: dict[fabll.Node, str] = {}
    comp_fullname_to_id: dict[str, str] = {}

    for component_node in fp_nodes:
        try:
            fp_trait = component_node.get_trait(F.Footprints.has_associated_footprint)
            fp = fp_trait.get_footprint()
            pads = fp.get_pads()
            if not pads:
                continue

            # ── Identity ─────────────────────────────────────
            comp_full = strip_root_hex(component_node.get_full_name())

            # The node with the footprint might be a deeply nested internal node
            # (e.g., "i2c_mux.package" or "i2c_mux.decoupling_caps[0]").
            # Walk up to find the "owning" module for a nice display name,
            # but use the full path for a unique JSON id.
            parent = component_node.get_parent()
            parent_name = None
            if parent:
                pn = strip_root_hex(parent[0].get_full_name())
                if pn and not re.match(r"^0x[0-9A-Fa-f]+$", pn):
                    parent_name = pn

            # Use the parent name as display_name (shorter, nicer)
            display_name = parent_name or comp_full

            # JSON ID must be unique – use the full path
            comp_json_id = comp_full.replace(".", "_").replace(" ", "_").lower()
            # Remove array brackets for cleaner IDs
            comp_json_id = re.sub(r"\[(\d+)\]", r"_\1", comp_json_id)

            logger.info(
                "  Component: full=%s parent=%s id=%s pads=%d",
                comp_full,
                parent_name,
                comp_json_id,
                len(pads),
            )

            # Designator
            designator = comp_json_id.upper()[:4]
            # Check the component itself and its parent for designator
            des_node = component_node
            if not des_node.has_trait(F.has_designator) and parent:
                if parent[0].has_trait(F.has_designator):
                    des_node = parent[0]
            if des_node.has_trait(F.has_designator):
                try:
                    designator = des_node.get_trait(F.has_designator).get_designator()
                except Exception:
                    pass

            reference = designator[0] if designator else "U"

            # Module type – the "kind" of component (e.g., "Capacitor", "Resistor")
            module_type = None
            component_source_file: str | None = None
            component_source_component: str | None = None
            # Try the component node itself first
            for check_node in [component_node] + ([parent[0]] if parent else []):
                try:
                    if check_node.has_trait(fabll.is_module):
                        locator = check_node.get_trait(
                            fabll.is_module
                        ).get_module_locator()
                        src_file, src_component = _module_source_from_locator(locator)
                        if src_file and not component_source_file:
                            component_source_file = src_file
                        if src_component and not component_source_component:
                            component_source_component = src_component

                        resolved_type = src_component
                        if not resolved_type and "::" in locator:
                            resolved_type = _normalize_component_name(
                                locator.split("::")[-1]
                            )
                        if resolved_type and module_type is None:
                            module_type = strip_root_hex(resolved_type)
                except Exception:
                    continue

            # ── Lead → pad mapping + interface tracing ────────
            # The node with the footprint may be different from the node that
            # has meaningful lead names. Walk up the hierarchy to find a node
            # with leads that have associated pads.
            lead_source_node = component_node
            lead_nodes = component_node.get_children(
                direct_only=False,
                types=fabll.Node,
                required_trait=F.Lead.is_lead,
            )

            # Check if leads actually have associated pads
            leads_with_pads = [
                lead
                for lead in lead_nodes
                if lead.get_trait(F.Lead.is_lead).has_trait(F.Lead.has_associated_pads)
            ]

            # If no leads with pads on component, try parent
            if not leads_with_pads and parent:
                parent_leads = parent[0].get_children(
                    direct_only=False,
                    types=fabll.Node,
                    required_trait=F.Lead.is_lead,
                )
                parent_leads_with_pads = [
                    lead
                    for lead in parent_leads
                    if lead.get_trait(F.Lead.is_lead).has_trait(
                        F.Lead.has_associated_pads
                    )
                ]
                if parent_leads_with_pads:
                    lead_source_node = parent[0]
                    lead_nodes = parent_leads
                    leads_with_pads = parent_leads_with_pads

            # Canonical pin identity in schematic export is pad_number.
            # This avoids collisions when multiple pads share a pad_name.
            pin_number_to_display: dict[str, str] = {}
            pin_number_to_functions: dict[str, list[dict]] = {}

            # Context node for interface tracing: the highest ato module ancestor
            trace_context = lead_source_node

            for lead_node in leads_with_pads:
                lead_trait = lead_node.get_trait(F.Lead.is_lead)
                lead_name = lead_trait.get_lead_name()
                functions = _trace_lead_interfaces(lead_node, trace_context)

                assoc_pads = lead_trait.get_trait(F.Lead.has_associated_pads).get_pads()
                for pad in assoc_pads:
                    try:
                        pin_number = str(pad.pad_number)
                        pin_number_to_display[pin_number] = lead_name
                        pin_number_to_functions[pin_number] = functions
                    except Exception:
                        continue

            # Filter out reference-network noise from functions
            for pin_number in pin_number_to_functions:
                pin_number_to_functions[pin_number] = _filter_lead_functions(
                    pin_number_to_functions[pin_number]
                )
            # Preserve the post-noise-filter trace set for module-interface
            # extraction; signal-name remapping below is intentionally stricter
            # and can hide bus/interface paths that should still surface as
            # module ports (SPI/I2C/UART/etc.).
            pin_number_to_functions_for_interfaces = {
                pin_number: list(functions)
                for pin_number, functions in pin_number_to_functions.items()
            }

            # ── Use .ato signal names when available ──────────────
            # The component's .ato definition has authoritative signal names
            # (e.g., "signal A0 ~ pin 1", "signal GND ~ pin 12") that are
            # unaffected by bridged-net function traces.
            signal_names = _extract_signal_names(component_node)
            if not signal_names and not component_node.is_same(lead_source_node):
                signal_names = _extract_signal_names(lead_source_node)
            if signal_names:
                pin_number_to_functions = _filter_pin_functions_by_signal_map(
                    pin_number_to_functions,
                    signal_names,
                )
                for pin_number, sig_name in signal_names.items():
                    pin_number_to_display[pin_number] = sig_name

            # Build the physical pin-number list from all available sources:
            # footprint pads, lead mappings, and .ato signal mappings.
            # This keeps pin identity stable even when one source is incomplete.
            pad_number_fallbacks: dict[str, str] = {}
            for pad in sorted(pads, key=lambda p: natural_sort_key(p.pad_number)):
                pin_number = str(pad.pad_number)
                if pin_number not in pad_number_fallbacks:
                    fallback = str(pad.pad_name) if str(pad.pad_name) else pin_number
                    pad_number_fallbacks[pin_number] = fallback

            pin_number_set = (
                set(pad_number_fallbacks.keys())
                | set(pin_number_to_display.keys())
                | set(pin_number_to_functions.keys())
                | set(signal_names.keys())
            )
            pin_numbers = sorted(pin_number_set, key=natural_sort_key)

            for pin_number in pin_numbers:
                if pin_number not in pin_number_to_display:
                    pin_number_to_display[pin_number] = pad_number_fallbacks.get(
                        pin_number, pin_number
                    )
                if pin_number not in pin_number_to_functions:
                    pin_number_to_functions[pin_number] = []

            # Derive better display names when lead names are generic numbers.
            for pin_number in pin_numbers:
                pin_number_to_display[pin_number] = _derive_display_name(
                    pin_number,
                    pin_number_to_display[pin_number],
                    pin_number_to_functions.get(pin_number, []),
                )

            logger.info(
                "    Leads: %d with pads (from %s), display_map=%s",
                len(leads_with_pads),
                strip_root_hex(lead_source_node.get_full_name()),
                dict(list(pin_number_to_display.items())[:8]),
            )

            # Layout pins using real KiCad footprint pad positions
            pins_data, body_w, body_h = _layout_pins(
                pin_numbers,
                pin_number_to_display,
                pin_number_to_functions,
                component_node=component_node,
            )

            component_name = module_type or display_name.rsplit(".", 1)[-1]
            footprint_hint = _extract_footprint_hint(component_node)
            symbol_metadata = _build_symbol_metadata(
                module_type=module_type,
                component_name=component_name,
                designator=designator,
                reference=reference,
                pin_count=len(pin_numbers),
                footprint_hint=footprint_hint,
            )

            # Store pad mapping (use pad node directly — stable hash/eq)
            for pad in pads:
                try:
                    pad_to_comp[pad] = comp_json_id
                    pad_to_number[pad] = pad.pad_number
                except Exception:
                    continue

            json_component = {
                "kind": "component",
                "id": comp_json_id,
                "name": component_name,
                "designator": designator,
                "reference": reference,
                "bodyWidth": round(body_w, 2),
                "bodyHeight": round(body_h, 2),
                "pins": pins_data,
            }
            if symbol_metadata:
                json_component.update(symbol_metadata)
            component_source = _build_instance_source_ref(
                comp_full,
                module_by_fullname,
            )
            if (
                component_source is None
                and component_source_file
                and component_source_component
            ):
                component_source = _make_source_ref(
                    component_source_file,
                    component_source_component,
                )
            if component_source:
                json_component["source"] = component_source

            # Extract interface mapping for this component's pins
            pin_to_iface = _extract_pin_interfaces(
                pin_number_to_functions_for_interfaces
            )

            comp_infos.append(
                _CompInfo(
                    json_id=comp_json_id,
                    full_name=comp_full,
                    json_component=json_component,
                    module_path=[],
                    owner_module_id=None,
                    pin_to_iface=pin_to_iface,
                )
            )

            comp_fullname_to_id[comp_full] = comp_json_id

        except Exception as e:
            logger.debug(
                "Error processing component for schematic: %s", e, exc_info=True
            )
            continue

    logger.info(
        "Processed %d components: %s",
        len(comp_infos),
        [c.json_id for c in comp_infos[:10]],
    )

    # ═══════════════════════════════════════════════════════════════
    # Phase 3: Count atomic parts per module and determine hierarchy
    # ═══════════════════════════════════════════════════════════════

    # Count atomic parts inside each module using original graph full_name
    for comp in comp_infos:
        for mod in all_modules.values():
            # Check if component's full_name starts with the module's full_name
            if comp.full_name.startswith(mod.full_name + "."):
                mod.atomic_part_count += 1

    logger.info(
        "Module part counts: %s",
        {m.full_name: m.atomic_part_count for m in all_modules.values()},
    )

    # Determine "interesting" modules (>= 2 atomic parts)
    interesting_module_ids = {
        mid for mid, m in all_modules.items() if m.atomic_part_count >= 2
    }

    logger.info(
        "Interesting modules (>=2 parts): %s",
        [all_modules[mid].full_name for mid in interesting_module_ids],
    )

    # Assign components to their owner module
    comp_to_owner: dict[str, str | None] = {}

    for comp in comp_infos:
        owner = None

        # Find the deepest interesting module that contains this component
        best_match_len = 0
        for mid in interesting_module_ids:
            mod = all_modules[mid]
            if comp.full_name.startswith(mod.full_name + "."):
                if len(mod.full_name) > best_match_len:
                    best_match_len = len(mod.full_name)
                    owner = mid

        comp.owner_module_id = owner
        comp_to_owner[comp.json_id] = owner

        logger.info(
            "  Component %s (full=%s) -> owner=%s",
            comp.json_id,
            comp.full_name,
            all_modules[owner].full_name if owner else "ROOT",
        )

        # Register component with its owner module
        if owner and owner in all_modules:
            all_modules[owner].direct_component_ids.append(comp.json_id)

    # Build child module relationships (only interesting modules)
    for mid, mod in all_modules.items():
        if mid not in interesting_module_ids:
            continue
        if mod.parent_id and mod.parent_id in interesting_module_ids:
            all_modules[mod.parent_id].child_module_ids.append(mid)

    # ═══════════════════════════════════════════════════════════════
    # Phase 4: Discover interfaces from lead_functions data
    # ═══════════════════════════════════════════════════════════════

    # For each interesting module, collect interfaces from its components' pins
    module_interfaces: dict[str, dict[str, dict]] = {}

    for mid in interesting_module_ids:
        mod = all_modules[mid]
        iface_map: dict[str, dict] = {}
        pin_map: dict[str, dict[str, dict[str, _PinBinding]]] = defaultdict(
            lambda: defaultdict(dict)
        )

        # Build a set of internal entity names (relative to module).
        # Interface names matching these are internal wiring, not public ports.
        # Includes both internal components and child sub-modules.
        _internal_names: set[str] = set()
        for comp in comp_infos:
            if comp.owner_module_id != mid:
                continue
            # Relative name: strip the module prefix
            if comp.full_name.startswith(mod.full_name + "."):
                rel = comp.full_name[len(mod.full_name) + 1 :]
                # The immediate child name (before any further dots)
                child = rel.split(".")[0]
                _internal_names.add(child)
                # Also add the bare name without array indices
                bare = re.sub(r"\[\d+\]", "", child)
                if bare != child:
                    _internal_names.add(bare)
        # Also include child sub-module instance names
        for child_mid in mod.child_module_ids:
            child_mod = all_modules.get(child_mid)
            if child_mod:
                _internal_names.add(child_mod.name)

        for comp in comp_infos:
            if comp.owner_module_id != mid:
                continue
            for pad_name, iface_list in comp.pin_to_iface.items():
                for iface_name, signal_suffix, iface_type, is_line_level in iface_list:
                    # Skip private interfaces (atopile convention: _ prefix)
                    if iface_name.startswith("_"):
                        continue
                    # Skip interfaces that reference internal entities
                    # (e.g., "core_power_decoupling_capacitor[0]" is wiring,
                    #  not a module port)
                    bare_name = re.sub(r"\[\d+\]$", "", iface_name)
                    if bare_name in _internal_names or iface_name in _internal_names:
                        continue
                    if iface_name not in iface_map:
                        category = "signal"
                        if iface_type in ("Power", "ElectricPower"):
                            category = "power"
                        elif iface_type == "I2C":
                            category = "i2c"
                        elif iface_type == "SPI":
                            category = "spi"
                        elif iface_type == "UART":
                            category = "uart"
                        elif iface_type in ("GPIO", "Control"):
                            category = "control"
                        elif iface_type == "Crystal":
                            category = "crystal"

                        iface_map[iface_name] = {
                            "type": iface_type,
                            "category": category,
                            "signals": set(),
                            "pin_map": pin_map[iface_name],
                        }

                    iface_map[iface_name]["signals"].add(signal_suffix)

                    # Build pin_map:
                    # comp_id -> {pad -> (iface_id, signal_suffix, is_line_level)}
                    # Tracks signal and connection mode each pad maps to.
                    pin_map[iface_name][comp.json_id][pad_name] = (
                        iface_name,
                        signal_suffix,
                        is_line_level,
                    )

        _mark_passthrough_interfaces(iface_map)
        mod.interfaces = iface_map
        module_interfaces[mid] = iface_map
        logger.debug(
            "Module %s interface map sizes: %s",
            mod.json_id,
            {
                iface_name: sum(
                    len(comp_map) for comp_map in iface_data.get("pin_map", {}).values()
                )
                for iface_name, iface_data in iface_map.items()
            },
        )

    # ═══════════════════════════════════════════════════════════════
    # Phase 5: Collect all nets
    # ═══════════════════════════════════════════════════════════════

    raw_nets: list[dict] = []

    try:
        all_fbrk_nets = list(F.Net.bind_typegraph(app.tg).get_instances(app.g))
    except Exception:
        all_fbrk_nets = []

    for fbrk_net in all_fbrk_nets:
        try:
            # Net names are assigned by the build pipeline (attach_net_names)
            # via the has_net_name trait — use get_name(), not get_net_name()
            net_name = None
            if fbrk_net.has_trait(F.has_net_name):
                try:
                    net_name = fbrk_net.get_trait(F.has_net_name).get_name()
                except Exception:
                    pass

            if not net_name:
                net_name = strip_root_hex(fbrk_net.get_full_name())

            net_pins: list[dict] = []
            try:
                connected_pads = fbrk_net.get_connected_pads()
                for pad in connected_pads:
                    if pad in pad_to_comp:
                        net_pins.append(
                            {
                                "componentId": pad_to_comp[pad],
                                "pinNumber": pad_to_number.get(pad, "?"),
                            }
                        )
            except Exception:
                continue

            if len(net_pins) < 1:
                continue

            unique_pins = _dedup_pins(net_pins)
            if len(unique_pins) < 1:
                continue
            net_id = re.sub(r"[^a-zA-Z0-9_]", "_", net_name)

            raw_nets.append(
                {
                    "id": net_id,
                    "name": net_name,
                    "type": _net_type(net_name),
                    "pins": unique_pins,
                }
            )

        except Exception as e:
            logger.debug("Error processing net: %s", e, exc_info=True)
            continue

    # ═══════════════════════════════════════════════════════════════
    # Phase 6: Scope nets to hierarchy levels
    # ═══════════════════════════════════════════════════════════════

    scoped_nets = _scope_nets(raw_nets, comp_to_owner, module_interfaces)

    # ═══════════════════════════════════════════════════════════════
    # Phase 7: Build hierarchical output
    # ═══════════════════════════════════════════════════════════════

    comp_by_id = {c.json_id: c for c in comp_infos}

    def _build_module(mod_id: str) -> dict | None:
        """Recursively build a SchematicModule dict."""
        mod = all_modules.get(mod_id)
        if not mod:
            return None

        module_source = _build_instance_source_ref(
            mod.full_name,
            module_by_fullname,
        )

        # Build interface pins
        interface_pins, body_w, body_h = _build_interface_pins(
            mod.interfaces,
            module_source,
        )

        # Build child modules
        child_modules = []
        for child_id in mod.child_module_ids:
            child = _build_module(child_id)
            if child:
                child_modules.append(child)

        # Build components (only those directly owned by this module)
        components = []
        for comp_id in mod.direct_component_ids:
            ci = comp_by_id.get(comp_id)
            if ci:
                components.append(ci.json_component)

        # Get nets for this module's sheet
        nets = scoped_nets.get(mod_id, [])

        module_json = {
            "kind": "module",
            "id": mod.json_id,
            "name": mod.name,
            "typeName": mod.type_name,
            "componentCount": mod.atomic_part_count,
            "interfacePins": interface_pins,
            "bodyWidth": body_w,
            "bodyHeight": body_h,
            "sheet": {
                "modules": child_modules,
                "components": components,
                "nets": nets,
            },
        }
        if module_source:
            module_json["source"] = module_source
        return module_json

    # Root-level modules (interesting modules with no interesting parent)
    root_modules = []
    for mid in interesting_module_ids:
        mod = all_modules[mid]
        if mod.parent_id not in interesting_module_ids:
            module_json = _build_module(mid)
            if module_json:
                root_modules.append(module_json)

    # Root-level components (not owned by any interesting module)
    root_components = [
        ci.json_component for ci in comp_infos if ci.owner_module_id is None
    ]

    # Root-level nets
    root_nets = scoped_nets.get(None, [])

    root_sheet = {
        "modules": root_modules,
        "components": root_components,
        "nets": root_nets,
    }

    # ═══════════════════════════════════════════════════════════════
    # Phase 8: Write output
    # ═══════════════════════════════════════════════════════════════

    # Preserve existing positions from the output file (if any)
    existing_positions: dict = {}
    if json_path.exists():
        try:
            import json as _json

            existing_data = _json.loads(json_path.read_text(encoding="utf-8"))
            existing_positions = existing_data.get("positions", {})
        except Exception:
            pass  # file corrupt or not JSON — start fresh

    # Inject schematic positions from sub-PCB packages
    try:
        subpcb_positions = _load_subpcb_schematic_positions(
            all_modules,
            interesting_module_ids,
            existing_positions,
        )
        existing_positions.update(subpcb_positions)
    except Exception as e:
        logger.debug("Could not load sub-PCB schematic positions: %s", e)

    result: dict = {
        "version": "2.0",
        "root": root_sheet,
        "positions": existing_positions,
    }

    write_json(result, json_path)
    logger.info(
        "Wrote v2 schematic to %s (%d root modules, %d root components, "
        "%d root nets, %d saved positions)",
        json_path,
        len(root_modules),
        len(root_components),
        len(root_nets),
        len(existing_positions),
    )
