import json
import logging
import time
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path

<<<<<<< HEAD
=======
import pandas as pd
import pint
>>>>>>> origin/main

from atopile import address, errors, instance_methods
from atopile.address import AddrStr
<<<<<<< HEAD
from git import Repo
import warnings

# Filter out specific warnings
warnings.filterwarnings(
    "ignore",
    message="Detected filter using positional arguments. Prefer using the 'filter' keyword argument instead.",
)
=======
from atopile.front_end import Physical
>>>>>>> origin/main

log = logging.getLogger(__name__)

# TODO: currently a hack until we develop the required infrastructure
_generics_to_db_fp_map = {
    "R01005": "01005",
    "R0201": "0201",
    "R0402": "0402",
    "R0603": "0603",
    "R0805": "0805",
    "C01005": "01005",
    "C0201": "0201",
    "C0402": "0402",
    "C0603": "0603",
    "C0805": "0805",
    "C1206": "1206",
}


_GENERIC_RESISTOR = "generic_resistor"
_GENERIC_CAPACITOR = "generic_capacitor"
_GENERIC_MOSFET = "generic_mosfet"
_GENERICS_MPNS = [_GENERIC_RESISTOR, _GENERIC_CAPACITOR, _GENERIC_MOSFET]


_generic_to_type_map = {
    _GENERIC_RESISTOR: "Resistor",
    _GENERIC_CAPACITOR: "Capacitor",
    _GENERIC_MOSFET: "mosfet",
}


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
        log.info("Component data has changed for updating cache")
        return True
    return False


def get_component_from_cache(component_addr, current_data):
    """Retrieve a component from the cache, if available, not stale, and unchanged."""
    cached_entry = component_cache.get(component_addr)
    if cached_entry:
        cached_timestamp = datetime.fromtimestamp(cached_entry["timestamp"])
        if datetime.now() - cached_timestamp < timedelta(
            days=1
        ) and not has_component_changed(cached_entry, current_data):
            return cached_entry["data"]
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


import requests
import logging
from typing import Any, Dict

def _get_generic_from_db(component_addr: str) -> Dict[str, Any]:
    """
    Return the MPN for a component given its address, using an API endpoint.
    """
    name = component_addr.split("::")[1]
    log = logging.getLogger(__name__)
    log.info(f"Fetching component for {name}")

    # First, try to get the component from the cache
    specd_data = instance_methods.get_data_dict(component_addr)
    cached_component = get_component_from_cache(component_addr, specd_data)
    if cached_component:
        log.info(f"Fetching component from cache for {name}")
        return cached_component

    # Prepare the payload for the API request
    specd_mpn = _get_specd_mpn(component_addr)
    specd_type = _generic_to_type_map.get(specd_mpn)

    # Validate and set default values based on component type
    if specd_type in ["Resistor", "Capacitor"]:
        try:
            float_value = units.parse_number(specd_data.get("value", 0))
            tolerance = specd_data.get("tolerance", 0.05)  # Default tolerance 5%
        except units.InvalidPhysicalValue as ex:
            ex.addr = component_addr + ".value"
            raise ex
        payload = {
            "type": specd_type,
            "min_value": float_value * (1 - tolerance),
            "max_value": float_value * (1 + tolerance),
            **specd_data  # Append all other component data
        }
    elif specd_type == "mosfet":
        current_A = specd_data.get("current")
        ds_voltage_V = specd_data.get("drain_source_voltage")
        if current_A is None or ds_voltage_V is None:
            raise ValueError("Required mosfet parameters missing (current, drain_source_voltage)")
        payload = {
            "type": "mosfet",
            "current": current_A,
            "drain_source_voltage": ds_voltage_V,
            **specd_data  # Append all other component data
        }
    else:
        raise ValueError("Invalid component type or missing data")

    # API endpoint URL
    url = "https://get-component-atsuhzfd5a-uc.a.run.app"

    # Make the POST request to the API
    try:
        log.info(payload)
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        best_component = response.json().get('Best Component')

        if not best_component:
            raise NoMatchingComponent("No valid component found", addr=component_addr)

        update_cache(component_addr, best_component, specd_data)
        lcsc = best_component["LCSC Part #"]
        log.info(f"Successfully fetched component {lcsc} for {name}")
        return best_component

    except requests.RequestException as e:
        log.warning(f"API request failed: {e}")
        # raise e  # Or handle it as per your error handling policy
        return  {"LCSC Part #": "Part not found", "value": "N/A", "unit": "N/A"}


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
    specd_mpn = _get_specd_mpn(addr)
    if specd_mpn in _GENERICS_MPNS:
        return _get_generic_from_db(addr)["LCSC Part #"]

    return specd_mpn


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
        description = db_data.get("Description")
        if description:
            return description
        else:
            return "?"

    comp_data = instance_methods.get_data_dict(addr)
    # The default is okay here, because we're only generics
    # must have a value
    return str(comp_data.get("value", ""))

def clone_footprint(addr: AddrStr):
    """
    Take the footprint from the database and make a .kicad_mod file for it
    TODO: clean this mess up
    """
    if not _is_generic(addr):
        return
    db_data = _get_generic_from_db(addr)

    # convert the footprint to a .kicad_mod file
    footprint = db_data.get('footprint_data', {}).get('kicad', 'No KiCad footprint available')

    if not footprint:
        return
    try:
        #Make a new .kicad_mod file and write the footprint to it
        repo = Repo(".", search_parent_directories=True)
        footprints_dir = Path(repo.working_tree_dir) /  "build/footprints/footprints.pretty"
        file_name = db_data.get('footprint').get('kicad')
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
        return db_data.get('footprint', {}).get('kicad', 'No KiCad footprint available')

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
        return db_data.get("Package", "")
    comp_data = instance_methods.get_data_dict(addr)
    try:
        return comp_data["package"]
    except KeyError as ex:
        raise MissingData(
            "$addr has no package", title="No Package", addr=addr
        ) from ex

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
