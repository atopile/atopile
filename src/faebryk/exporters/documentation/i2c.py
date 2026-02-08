# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver
from faebryk.exporters.utils import (
    strip_root_hex as _strip_root_hex,
    write_json as _write_json,
)

logger = logging.getLogger(__name__)


def _is_standalone_bus_var(member: F.I2C) -> bool:
    """
    Check if this I2C instance is a standalone bus variable (direct child of
    the app root module), not owned by a real component. These are just
    connection aliases and shouldn't appear as nodes in the tree.

    E.g. `i2c_bus0 = new I2C` at the top level of the app module.
    """
    parent = member.get_parent()
    if not parent:
        return False
    parent_node = parent[0]
    # If the parent has the is_app_root trait, this is a top-level bus variable
    if parent_node.has_trait(F.is_app_root):
        return True
    return False


def _resolve_address(
    member: F.I2C, solver: Solver
) -> tuple[str | None, bool]:
    """
    Try to resolve the I2C address parameter.
    Returns (address_string, is_resolved).
    """
    try:
        addr_param = member.address.get().get_trait(F.Parameters.is_parameter)
        lit = solver.extract_superset(addr_param)
        if lit is None:
            return None, False

        pretty = lit.pretty_str()
        if lit.op_setic_is_singleton():
            cleaned = pretty.strip("{}")
            try:
                val = int(float(cleaned))
                return hex(val), True
            except (ValueError, TypeError):
                return pretty, True

        # Check if it's a meaningful range (not just the full real set)
        if "\u211d" not in pretty and pretty != "?" and pretty:
            return pretty, False

        # Method 2: try direct extraction on the parameter node
        try:
            direct_lit = member.address.get().try_extract_superset()
            if direct_lit is not None:
                direct_pretty = direct_lit.pretty_str()
                if direct_pretty and "\u211d" not in direct_pretty and direct_pretty != "?":
                    if direct_lit.is_singleton():
                        cleaned = direct_pretty.strip("{}")
                        try:
                            val = int(float(cleaned))
                            return hex(val), True
                        except (ValueError, TypeError):
                            return direct_pretty, True
                    return direct_pretty, False
        except Exception:
            pass

        # Method 3: check if the parent module has an Addressor with a resolved
        # address (for devices using pin-configurable addresses like IMUs)
        try:
            parent = member.get_parent()
            if parent:
                parent_node = parent[0]
                for child in parent_node.get_children(
                    direct_only=True,
                    types=fabll.Node,
                    include_root=False,
                ):
                    child_name = child.get_name(accept_no_parent=True) or ""
                    if "addressor" not in child_name.lower():
                        continue
                    # Found an addressor child, try to get its address param
                    for param_child in child.get_children(
                        direct_only=True,
                        types=fabll.Node,
                        required_trait=F.Parameters.is_parameter,
                        include_root=False,
                    ):
                        param_name = param_child.get_name(accept_no_parent=True) or ""
                        if param_name != "address":
                            continue
                        addr_p = param_child.get_trait(F.Parameters.is_parameter)
                        addr_lit = solver.extract_superset(addr_p)
                        if addr_lit is not None and addr_lit.op_setic_is_singleton():
                            addr_pretty = addr_lit.pretty_str().strip("{}")
                            try:
                                val = int(float(addr_pretty))
                                return hex(val), True
                            except (ValueError, TypeError):
                                return addr_lit.pretty_str(), True
        except Exception:
            pass

        return None, False

    except Exception as e:
        logger.debug(f"Could not resolve address for {member.get_full_name()}: {e}")
    return None, False


def _has_addressor(member: F.I2C) -> bool:
    """Check if the parent module of this I2C interface has an Addressor child."""
    try:
        parent = member.get_parent()
        if not parent:
            return False
        parent_node = parent[0]
        for child in parent_node.get_children(
            direct_only=True,
            types=fabll.Node,
            include_root=False,
        ):
            child_name = child.get_name(accept_no_parent=True) or ""
            if "addressor" in child_name.lower():
                return True
    except Exception:
        pass
    return False


def _determine_role(
    member: F.I2C,
    address_str: str | None,
    address_resolved: bool,
) -> str:
    """
    Determine if an I2C interface is a controller or target.

    Priority:
    1. Explicit is_i2c_controller / is_i2c_target traits
    2. Has a resolved non-zero address -> target
    3. Has any address constraint at all -> target
    4. Parent module has an Addressor -> target (address via pin config)
    5. No address info -> controller (MCU-like)
    """
    if member.has_trait(F.is_i2c_controller):
        return "controller"
    if member.has_trait(F.is_i2c_target):
        return "target"

    if address_str is not None:
        if address_resolved:
            try:
                if int(address_str, 16) == 0:
                    return "controller"
            except (ValueError, TypeError):
                pass
            return "target"
        else:
            return "target"

    # Check if parent has an Addressor (pin-configurable address device)
    if _has_addressor(member):
        return "target"

    return "controller"


def export_i2c_tree_json(
    app: fabll.Node,
    solver: Solver,
    *,
    json_path: Path,
) -> None:
    """
    Export the I2C bus tree as a JSON file for the tree visualizer.
    """
    i2c_instances = list(
        F.I2C.bind_typegraph(tg=app.tg).get_instances()
    )

    if not i2c_instances:
        logger.info("No I2C interfaces found, skipping I2C tree export")
        _write_json({"version": "1.0", "buses": []}, json_path)
        return

    # Group into buses by connectivity
    buses = fabll.is_interface.group_into_buses(i2c_instances)
    buses = {
        root: members
        for root, members in buses.items()
        if len(members) > 1
    }

    json_buses = []
    bus_counter = 0

    for bus_root, bus_members in buses.items():
        bus_id = f"bus_{bus_counter}"
        bus_counter += 1

        controllers = []
        targets = []
        ctrl_counter = 0
        tgt_counter = 0

        # Resolve bus frequency
        frequency_str = None

        for raw_member in bus_members:
            # CRITICAL: bus members are raw Nodes -- cast back to F.I2C
            member = F.I2C.bind_instance(raw_member.instance)

            parent = member.get_parent()

            # Skip standalone bus variables: I2C instances whose name doesn't
            # contain a dot (they're direct children of the app, not nested
            # inside a component module)
            member_name_raw = member.get_full_name()
            clean_name = _strip_root_hex(member_name_raw)
            if "." not in clean_name:
                # This is a top-level bus variable like i2c_bus0, skip it
                continue
            parent_module_raw = parent[0].get_full_name() if parent else None

            member_name = clean_name
            parent_module = _strip_root_hex(parent_module_raw) if parent_module_raw else None
            # If parent module is still a bare hex ID (top-level app), use None
            if parent_module and re.match(r"^0x[0-9A-Fa-f]+$", parent_module):
                parent_module = None

            # Resolve frequency from first member that has it
            if frequency_str is None:
                try:
                    freq_param = member.frequency.get().get_trait(
                        F.Parameters.is_parameter
                    )
                    freq_lit = solver.extract_superset(freq_param)
                    if freq_lit is not None:
                        freq_str = freq_lit.pretty_str()
                        if freq_str and freq_str != "?" and "\u211d" not in freq_str:
                            frequency_str = freq_str
                except Exception:
                    pass

            # Resolve address
            address_str, address_resolved = _resolve_address(member, solver)

            # If address not resolved but has addressor, note it
            if address_str is None and _has_addressor(member):
                address_str = "via addressor"
                address_resolved = False

            # Determine role
            role = _determine_role(member, address_str, address_resolved)

            if role == "controller":
                controllers.append({
                    "id": f"{bus_id}_ctrl_{ctrl_counter}",
                    "name": member_name,
                    "parent_module": parent_module,
                })
                ctrl_counter += 1
            else:
                targets.append({
                    "id": f"{bus_id}_tgt_{tgt_counter}",
                    "name": member_name,
                    "parent_module": parent_module,
                    "address": address_str,
                    "address_resolved": address_resolved,
                })
                tgt_counter += 1

        json_buses.append({
            "id": bus_id,
            "controllers": controllers,
            "targets": targets,
            "frequency": frequency_str,
        })

    _write_json({"version": "1.0", "buses": json_buses}, json_path)
    logger.info("Wrote I2C tree JSON to %s", json_path)



# _write_json is imported from faebryk.exporters.utils
