import json
import logging
import time
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any, Optional

import requests

from atopile import address, errors, instance_methods, config

from atopile.address import AddrStr
from atopile.front_end import RangedValue

log = logging.getLogger(__name__)


def _get_specd_mpn(addr: AddrStr) -> str:
    """
    Return the MPN for a component given its address
    """
    try:
        return instance_methods.get_data(addr, "mpn")
    except KeyError as ex:
        raise MissingData("$addr has no MPN", title="No MPN", addr=addr) from ex


def _get_specd_type(addr: AddrStr) -> str:
    """
    Return the type for a component given its address
    """
    try:
        mpn = _get_specd_mpn(addr)
        # split off "generic_" from the mpn
        return mpn.split("_", 1)[1]
    except KeyError as ex:
        raise MissingData("$addr has no type", title="No Type", addr=addr) from ex


def _is_generic(addr: AddrStr) -> bool:
    """
    Return whether a component is generic
    """
    # check if "generic_" is in the mpn
    try:
        return _get_specd_mpn(addr).startswith("generic_")
    except MissingData:
        return False


class NoMatchingComponent(errors.AtoError):
    """
    Raised when there's no component matching the given parameters in jlc_parts.csv
    """

    title = "No component matches parameters"


component_cache: dict[str, Any]
cache_file_path: Path

def configure_cache(top_level_path: Path):
    """Configure the cache to be used by the component module."""
    global component_cache
    global cache_file_path
    cache_file_path = top_level_path / ".ato/component_cache.json"
    if cache_file_path.exists():
        with open(cache_file_path, "r") as cache_file:
                component_cache = json.load(cache_file)
        # Clean out stale entries
        clean_cache()
    else:
        component_cache = {}

def save_cache():
    """Saves the current state of the cache to a file."""
    cache_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file_path, "w") as cache_file:
        # Convert the ChainMap to a regular dictionary
        serializable_cache = dict(component_cache)
        json.dump(serializable_cache, cache_file)


def get_component_from_cache(component_addr: AddrStr, current_data: dict) -> Optional[dict]:
    """Retrieve a component from the cache, if available, not stale, and unchanged."""
    if component_addr not in component_cache:
        return None

    # Check the cache age
    cached_entry = component_cache[component_addr]
    cached_timestamp = datetime.fromtimestamp(cached_entry["timestamp"])
    cache_age = datetime.now() - cached_timestamp
    if cache_age > timedelta(days=14):
        return None

    # Check the component attrs
    if current_data != cached_entry["address_data"]:
        return None

    log.debug("Using cached component for %s", component_addr)
    return cached_entry["data"]


def update_cache(component_addr, component_data, address_data):
    """Update the cache with new component data and save it."""
    component_cache[component_addr] = {
        "data": component_data,
        "timestamp": time.time(),  # Current time as a timestamp
        "address_data": dict(address_data),  # Source attributes used to detect changes
    }
    save_cache()


def clean_cache():
    """Clean out entries older than 1 day."""
    addrs_to_delete = set()
    for addr, entry in component_cache.items():
        cached_timestamp = datetime.fromtimestamp(entry["timestamp"])
        if datetime.now() - cached_timestamp >= timedelta(days=1):
            addrs_to_delete.add(addr)

    for addr in addrs_to_delete:
        del component_cache[addr]

    save_cache()

@cache
def _get_generic_from_db(component_addr: str) -> dict[str, Any]:
    """
    Return the MPN for a component given its address
    """
    log.debug("Fetching component for %s", component_addr)

    specd_data = instance_methods.get_data_dict(component_addr)

    specd_data_dict = {
        k: v.to_dict() if isinstance(v, RangedValue) else v for k, v in specd_data.items()
    }

    # check if there are any Physical objects in the specd_data, if not, throw a warning
    if specd_data:  # Check that specd_data is not empty
        if not any(isinstance(v, RangedValue) for v in specd_data.values()):
            log.warning(
                "Component %s is under-constrained, does not have any Physical types (e.g., value = 10kohm +/- 10%%).",
                component_addr)
    else:
        log.warning("No specification data provided for %s.", component_addr)

    # if there is no type, use the get_specd_type function to get it
    if "type" not in specd_data_dict:
        specd_data_dict["type"] = _get_specd_type(component_addr)

    # if there is a footprint, strip the leading letter and add the rest as 'package', remove the footprint
    if "footprint" in specd_data_dict:
        # if there is a package, use the package and remove the footprint
        type = _get_specd_type(component_addr)
        if "package" in specd_data_dict:
            del specd_data_dict["footprint"]
        # check if it is a resistor or capacitor
        elif type == "resistor" or type == "capacitor":
            specd_data_dict["package"] = specd_data_dict["footprint"][1:]
            del specd_data_dict["footprint"]


    cached_component = get_component_from_cache(component_addr, specd_data_dict)
    if cached_component:
        log.debug("Using cache for %s", component_addr)
        return cached_component

    url = config.get_project_context().config.services.components
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=specd_data_dict, timeout=20, headers=headers)
        response.raise_for_status()
    except requests.HTTPError as ex:
        if ex.response.status_code == 404:
            friendly_dict = " && ".join(f"{k} == {v}" for k, v in specd_data_dict.items())
            raise NoMatchingComponent(
                f"No valid component found for spec {friendly_dict}: please check the part specs above, if they look right, we probably dont have it yet, we are working on it!",
                addr=component_addr
            ) from ex

        raise errors.AtoInfraError(
            f"""
            Failed to fetch component data from database.
            Error: {str(ex)}
            Response status code: {ex.response.status_code}
            Response text: {ex.response.text}
            """,
            addr=component_addr
        ) from ex
    except requests.RequestException as ex:
        raise errors.AtoInfraError(
            f"Error connecting to database: {str(ex)}",
            addr=component_addr
        ) from ex

    response_data = response.json() or {}

    best_component = response_data.get("bestComponent")
    # FIXME: Not returning something isn't a great mechanism to express
    # that we didn't find a component. It's not easy to distinguish between
    # a component not existing and other failure modes.
    if not best_component:
        raise NoMatchingComponent("No valid component found", addr=component_addr)

    lcsc = best_component["lcsc_id"]
    log.info("Fetched component %s for %s", lcsc, component_addr)

    # Now that we have a working component, update the cache with it for later
    update_cache(component_addr, best_component, specd_data_dict)

    return best_component


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
    if _is_generic(addr):
        return _get_generic_from_db(addr)["lcsc_id"]

    return specd_mpn


def get_specd_value(addr: AddrStr) -> str:
    """
    Return the MPN for a component given its address
    """
    try:
        return str(instance_methods.get_data(addr, "value"))
    except KeyError as ex:
        if not _is_generic(addr):
            # it's cool if there's no value for non-generics
            return ""
        raise MissingData(
            "$addr has no value spec'd",
            title="No value",
            addr=addr
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
            return db_data.get("description", "")
        else:
            return "?"

    return get_specd_value(addr)


# FIXME: this function's requirements might cause a circular dependency
def download_footprint(addr: AddrStr, footprint_dir: Path):
    """
    Take the footprint from the database and make a .kicad_mod file for it
    TODO: clean this mess up
    """
    if not _is_generic(addr):
        return
    db_data = _get_generic_from_db(addr)

    # convert the footprint to a .kicad_mod file
    try:
        footprint = db_data.get("footprint_data", {})["kicad"]
    except KeyError as ex:
        raise MissingData(
            "db component for $addr has no footprint", title="No Footprint", addr=addr
        ) from ex

    if footprint == "standard_library":
        log.debug("Footprint is standard library, skipping")
        return

    try:
        file_name = db_data.get("footprint", {}).get("kicad")
        file_path = Path(footprint_dir) / str(file_name)

        # Create the directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w") as footprint_file:
            footprint_file.write(footprint)
    except Exception as ex:
        raise errors.AtoInfraError("Failed to write footprint file", addr=addr) from ex


# Footprints come from the users' code, so we reference that directly
@cache
def get_footprint(addr: AddrStr) -> str:
    """
    Return the footprint for a component
    """
    if _is_generic(addr):
        db_data = _get_generic_from_db(addr)

        try:
            footprint = db_data.get("footprint", {})["kicad"]
            # strip .kicad_mod from the end of the footprint if it's there
            if footprint.endswith(".kicad_mod"):
                footprint = footprint.removesuffix(".kicad_mod")
        except KeyError as ex:
            raise errors.AtoInfraError(
                "db component for $addr has no footprint",
                addr=addr
            ) from ex
        return footprint

    try:
        return instance_methods.get_data(addr, "footprint")
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

    try:
        return instance_methods.get_data(addr, "footprint")
    except KeyError as ex:
        raise MissingData("$addr has no package", title="No Package", addr=addr) from ex


class DesignatorManager:
    """
    Ensure unique designators for all components.
    """

    def __init__(self) -> None:
        self._designators: dict[AddrStr, str] = {}

    def _make_designators(self, root: str) -> dict[str, str]:
        designators: dict[str, str] = {}
        unnamed_components = []
        used_designators = set()

        # FIXME: add lock-file data
        # first pass: grab all the designators from the lock data
        for err_handler, component in errors.iter_through_errors(filter(
            instance_methods.match_components, instance_methods.all_descendants(root)
        )):
            with err_handler():
                try:
                    designator = instance_methods.get_data(component, "designator")
                except KeyError:
                    designator = None

                if designator:
                    if designator in used_designators:
                        raise errors.AtoError(
                            f"Designator {designator} already in use", addr=component
                        )
                    used_designators.add(designator)
                    designators[component] = designator
                else:
                    unnamed_components.append(component)

        # second pass: assign designators to the unnamed components
        for component in unnamed_components:
            try:
                prefix = instance_methods.get_data(component, "designator_prefix")
            except KeyError:
                prefix = "U"

            i = 1
            while f"{prefix}{i}" in used_designators:
                i += 1

            designators[component] = f"{prefix}{i}"
            used_designators.add(designators[component])

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
