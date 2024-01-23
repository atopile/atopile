import json
import logging
import time
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any, Dict

import attr
import pint
import requests
from git import Repo

from atopile import address, errors, instance_methods
from atopile.address import AddrStr
from atopile.front_end import Physical

log = logging.getLogger(__name__)

_GENERIC_RESISTOR = "generic_resistor"
_GENERIC_CAPACITOR = "generic_capacitor"
_GENERIC_MOSFET = "generic_mosfet"
_GENERICS_MPNS = [_GENERIC_RESISTOR, _GENERIC_CAPACITOR, _GENERIC_MOSFET]

_generic_to_unit_map = {
    _GENERIC_RESISTOR: pint.Unit("ohm"),
    _GENERIC_CAPACITOR: pint.Unit("farad"),
}


def _get_specd_mpn(addr: AddrStr) -> str:
    """
    Return the MPN for a component given its address
    """
    comp_data = instance_methods.get_data_dict(addr)

    try:
        return comp_data["mpn"]
    except KeyError as ex:
        raise MissingData("$addr has no MPN", title="No MPN", addr=addr) from ex


def _is_generic(addr: AddrStr) -> bool:
    """
    Return whether a component is generic
    """
    specd_mpn = _get_specd_mpn(addr)
    return specd_mpn in _GENERICS_MPNS


class NoMatchingComponent(errors.AtoError):
    """
    Raised when there's no component matching the given parameters in jlc_parts.csv
    """

    title = "No component matches parameters"


# Define the cache file path
repo = Repo(".", search_parent_directories=True)
top_level_path = Path(repo.working_tree_dir)
cache_file_path = top_level_path / ".ato/component_cache.json"

# Try to load the cache, if it exists
if cache_file_path.exists():
    with open(cache_file_path, "r") as cache_file:
        component_cache = json.load(cache_file)
else:
    component_cache = {}


def save_cache():
    """Saves the current state of the cache to a file."""
    with open(cache_file_path, "w") as cache_file:
        # Convert the ChainMap to a regular dictionary
        serializable_cache = dict(component_cache)
        json.dump(serializable_cache, cache_file)


def has_component_changed(cached_entry, current_data):
    """Check if the component data has changed based on the address."""
    # Implement logic to compare relevant parts of current_data with cached_entry['address_data']
    # Return True if data has changed, False otherwise
    if current_data != cached_entry["address_data"]:
        log.debug("Component data has changed for updating cache")
        return True
    return False


def get_component_from_cache(component_addr, current_data):
    """Retrieve a component from the cache, if available, not stale, and unchanged."""
    cached_entry = component_cache.get(component_addr)
    if cached_entry:
        log.debug(f"Fetching component from cache for {component_addr}")
        cached_timestamp = datetime.fromtimestamp(cached_entry["timestamp"])
        if datetime.now() - cached_timestamp < timedelta(
            days=1
        ) and not has_component_changed(cached_entry, current_data):
            return cached_entry["data"]
        log.debug("Component data is stale, fetching from database")
    return None


def update_cache(component_addr, component_data, address_data):
    """Update the cache with new component data and save it."""
    component_cache[component_addr] = {
        "data": component_data,
        "timestamp": time.time(),  # Current time as a timestamp
        "address_data": dict(address_data),  # Data used to detect changes
    }
    save_cache()


def clean_cache():
    """Clean out entries older than 1 day."""
    for addr, entry in list(component_cache.items()):
        cached_timestamp = datetime.fromtimestamp(entry["timestamp"])
        if datetime.now() - cached_timestamp >= timedelta(days=1):
            del component_cache[addr]
    save_cache()


def _get_generic_from_db(component_addr: str) -> Dict[str, Any]:
    """
    Return the MPN for a component given its address, using an API endpoint.
    """
    name = component_addr.split("::")[1]
    log = logging.getLogger(__name__)
    log.debug(f"Fetching component for {name}")

    specd_data = instance_methods.get_data_dict(component_addr)

    specd_data_dict = {
        k: v.to_dict() if isinstance(v, Physical) else v for k, v in specd_data.items()
    }

    payload = {
        **specd_data_dict,
    }
    log.debug(payload)

    cached_component = get_component_from_cache(component_addr, specd_data_dict)
    if cached_component:
        log.debug(f"Fetching component from cache for {name}")
        return cached_component

    component = _make_api_request(name, component_addr, payload, log)

    update_cache(component_addr, component, specd_data_dict)

    return component


def _make_api_request(name, component_addr, payload, log):
    url = "https://get-component-atsuhzfd5a-uc.a.run.app"
    try:
        log.debug(payload)
        response = requests.post(url, json=payload)
        response.raise_for_status()
        best_component = response.json().get("bestComponent")

        if not best_component:
            raise NoMatchingComponent("No valid component found", addr=component_addr)

        lcsc = best_component["lcsc_id"]
        log.debug(f"Successfully fetched component {lcsc} for {name}")
        return best_component

    except requests.RequestException as e:
        log.warning(f"API request failed: {e}")
        return Component()

@attr.s(auto_attribs=True)
class Component:
    lcsc_id: str = attr.ib(default="Part not found")
    value: str = attr.ib(default="N/A")
    unit: str = attr.ib(default="N/A")

class MissingData(errors.AtoError):
    """
    Raised when a component is missing data in the Basic_Parts.csv file.
    """


# We cache the MPNs to ensure we select the same component if it's hit multiple times
# in a build
@cache
def get_mpn(addr: AddrStr) -> str:
    """
    Return the MPN for a component
    """
    log.debug(f"Getting MPN for {addr}")
    if _is_generic(addr):
        db_data = _get_generic_from_db(addr)
        return db_data.get("lcsc_id", "")
    else:
        return _get_specd_mpn(addr)


def get_specd_value(addr: AddrStr) -> str:
    """
    Return the MPN for a component given its address
    """
    comp_data = instance_methods.get_data_dict(addr)
    if not _is_generic(addr):
        # it's cool if there's no value for non-generics
        return str(comp_data.get("value", ""))

    try:
        return str(comp_data["value"])
    except KeyError as ex:
        raise MissingData(
            "$addr has no value spec'd", title="No value", addr=addr
        ) from ex


# Values come from the finally selected
# component, so we need to arbitrate via that data
@cache
def get_user_facing_value(addr: AddrStr) -> str:
    """
    Return a "value" of a component we can slap in things like
    the BoM and netlist. Doesn't need to be perfect, just
    something to look at.
    """
    if _is_generic(addr):
        db_data = _get_generic_from_db(addr)
        if db_data:
            # return db_data.get("type", "")
            return db_data.get("description", "")
        else:
            return "?"

    comp_data = instance_methods.get_data_dict(addr)
    # The default is okay here, because we're only generics
    # must have a value
    return str(comp_data.get("value", ""))

#FIXME: this might create a circular dependency
def clone_footprint(addr: AddrStr):
    """
    Take the footprint from the database and make a .kicad_mod file for it
    TODO: clean this mess up
    """
    if not _is_generic(addr):
        return
    db_data = _get_generic_from_db(addr)


    # convert the footprint to a .kicad_mod file
    try:
        footprint = db_data.get("footprint_data", {}).get(
            "kicad", "No KiCad footprint available"
        )
    except KeyError:
        footprint = None

    if not footprint:
        return
    if footprint == "standard_library":
        log.debug("Footprint is standard library, skipping")
        return
    try:
        # Make a new .kicad_mod file and write the footprint to it
        repo = Repo(".", search_parent_directories=True)
        footprints_dir = (
            Path(repo.working_tree_dir) / "build/footprints/footprints.pretty"
        )
        file_name = db_data.get("footprint").get("kicad")
        file_path = footprints_dir / f"{file_name}"
        footprint_file = open(f"{file_path}.kicad_mod", "w")
        footprint_file.write(footprint)
    except Exception as e:
        log.warning(f"Failed to write footprint file: {e}")

# Footprints come from the users' code, so we reference that directly
@cache
def get_footprint(addr: AddrStr) -> str:
    """
    Return the footprint for a component
    """
    if _is_generic(addr):
        db_data = _get_generic_from_db(addr)
        clone_footprint(addr)

        try:
            footprint = db_data.get("footprint", {}).get(
                "kicad", "No KiCad footprint available"
            )
        except KeyError:
            footprint = None
        return footprint

    comp_data = instance_methods.get_data_dict(addr)
    try:
        return comp_data["footprint"]
    except KeyError as ex:
        raise MissingData(
            "$addr has no footprint", title="No Footprint", addr=addr
        ) from ex


@cache
def get_package(addr: AddrStr) -> str:
    """
    Return the package for a component
    """
    if _is_generic(addr):
        db_data = _get_generic_from_db(addr)
        return db_data.get("package", "")
    comp_data = instance_methods.get_data_dict(addr)
    try:
        return comp_data["package"]
    except KeyError as ex:
        raise MissingData("$addr has no package", title="No Package", addr=addr) from ex


class DesignatorManager:
    """TODO:"""

    def __init__(self) -> None:
        self._designators: dict[AddrStr, str] = {}

    def _make_designators(self, root: str) -> dict[str, str]:
        designators: dict[str, str] = {}
        unnamed_components = []
        used_designators = set()

        # first pass: grab all the designators from the lock data
        for component in filter(
            instance_methods.match_components, instance_methods.all_descendants(root)
        ):
            designator = instance_methods.get_lock_data_dict(component).get(
                "designator"
            )
            if designator:
                used_designators.add(designator)
                designators[component] = designator
            else:
                unnamed_components.append(component)

        # second pass: assign designators to the unnamed components
        for component in unnamed_components:
            prefix = instance_methods.get_data_dict(component).get(
                "designator_prefix", "U"
            )

            i = 1
            while f"{prefix}{i}" in used_designators:
                i += 1

            designators[component] = f"{prefix}{i}"
            used_designators.add(designators[component])
            instance_methods.get_lock_data_dict(component)["designator"] = designators[
                component
            ]

        return designators

    def get_designator(self, addr: str) -> str:
        """Return a mapping of instance address to designator."""
        if addr not in self._designators:
            self._designators = self._make_designators(address.get_entry(addr))
        return self._designators[addr]


designator_manager = DesignatorManager()


def get_designator(addr: str) -> str:
    """
    Return the designator for a component
    """
    return designator_manager.get_designator(addr)
