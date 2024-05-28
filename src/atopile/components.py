import json
import logging
import time
import yaml
import os
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any, Optional
from fastapi import HTTPException

import requests

from atopile import address, errors, instance_methods, config

from atopile.database.schemas import Resistor, Inductor, Capacitor, DBRangedValue

from atopile.address import AddrStr
from atopile.front_end import RangedValue

log = logging.getLogger(__name__)

class NoMatchingComponent(errors.AtoError):
    """
    Raised when there's no component matching the given parameters in jlc_parts.csv
    """

    title = "No component matches parameters"


_component_lock: Optional[dict[str, Any]] = None
def get_component_lock() -> dict[str, Any]:
    """Return the component lock file data."""
    global _component_lock
    if _component_lock is None:
        configure_component_lock()
    return _component_lock

def configure_component_lock():
    """Configure the component lock file data to be used by the component module."""
    global _component_lock
    lock_file_path = config.get_project_context().lock_file_path
    if lock_file_path.exists():
        with open(lock_file_path, "r") as lock_file:
                lock_file_data = yaml.safe_load(lock_file)
                lock_file_data.setdefault("manufacturing data", {})
                if lock_file_data is None or "manufacturing data" not in lock_file_data or lock_file_data["manufacturing data"] is None:
                    _component_lock = {}
                else:
                    _component_lock = lock_file_data.get("manufacturing data", {})
    else:
        _component_lock = {}

def update_lock_file(component_addr, abstract_component_data: Inductor | Capacitor | Resistor, manufacturing_component_data: Inductor | Capacitor | Resistor):
    """Update the lock file with new component data and save it."""
    get_component_lock()[component_addr] = {
        "abstract_data": abstract_component_data.model_dump(),
        #TODO: fix this to an actual defined scheme
        "manufacturing_data": dict(manufacturing_component_data),
    }
    save_component_lock_file()

def save_component_lock_file():
    """Saves the current state of the component lock file."""
    lock_file_path = config.get_project_context().lock_file_path
    if os.path.exists(lock_file_path):
        try:
            with open(lock_file_path, 'r') as file:
                lock_file_data = yaml.safe_load(file)
            if lock_file_data is None:
                lock_file_data = {}
            lock_file_data.setdefault("manufacturing data", {})
            lock_file_data["manufacturing data"] = get_component_lock()

            with open(lock_file_path, 'w') as file:
                yaml.safe_dump(lock_file_data, file)

        except Exception as e:
            raise errors.AtoInfraError(f"Error saving component lock file: {str(e)}") from e
    else:
        try:
            with open(lock_file_path, 'w') as file:
                yaml.safe_dump(lock_file_data, file)

        except Exception as e:
            raise errors.AtoInfraError(f"Error saving component lock file: {str(e)}") from e


def get_component_from_lock_file(component_addr: AddrStr, current_component: Inductor | Capacitor | Resistor) -> Optional[dict]:
    """Retrieve a component from lock file, if available and unchanged."""
     # Check if this component is already in the lock file

    component_lock_file_abstract_data = get_component_lock().get(component_addr, {}).get('abstract_data', None)

    if component_lock_file_abstract_data != current_component.model_dump():
        log.info(f"Lock file data differs from current component data for {component_addr}")
        return None

    component_lock_file_manufacturing_data = get_component_lock().get(component_addr, {}).get('manufacturing_data', None)
    return component_lock_file_manufacturing_data



#FIXME: in the future, we should have a model that provides this information throughout our pipeline
# For the minute, let's use this function
@cache
def _get_component_data(component_addr: str) -> dict[str, Any]:
    """
    Return the MPN and data fields for a component given its address
    """
    # The process is the following:
    # 1 Get the specd data from the instance methods
    # 2 If the component can be fetched from the server and doesn't have an MPN attached, we try to fetch it
    # 2.1 Fetch from the lock file. If we can find a component there, great. If we can't proceed to the next step.
    # 2.2 Fetch from the database. If we can find a component, great. If we can't, throw an error
    # 3 Else, provide the data back

    specd_data = instance_methods.get_data_dict(component_addr)

    # 2 check if the component can be fetched from the database.
    if "mpn" in specd_data:
        log.debug(f"Component {component_addr} has a provided MPN")
        return specd_data

    if "__type__" not in specd_data:
        raise errors.AtoError(
            f"Component is missing an mpn",
            addr=component_addr
        )

    else:
        type = specd_data["__type__"]
        # Process the specd_data to transform RangedValues to DBRangedValues
        db_processedspecd_data = {
            k: DBRangedValue.from_ranged_value(v) if isinstance(v, RangedValue) else v for k, v in specd_data.items()
        }
        if type == "inductor":
            try:
                component = Inductor(**db_processedspecd_data)
            except Exception as ex:
                raise errors.AtoInfraError(
                    f"Error creating inductor: {str(ex)}",
                    addr=component_addr
                ) from ex
        elif type == "capacitor":
            try:
                component = Capacitor(**db_processedspecd_data)
            except Exception as ex:
                raise errors.AtoInfraError(
                    f"Error creating capacitor: {str(ex)}",
                    addr=component_addr
                ) from ex
        elif type == "resistor":
            try:
                component = Resistor(**db_processedspecd_data)
            except Exception as ex:
                raise errors.AtoInfraError(
                    f"Error creating resistor: {str(ex)}",
                    addr=component_addr
                ) from ex
        else:
            raise errors.AtoError(
                f"Unknown component type: {type}",
                addr=component_addr
            )

    # Get component from lock file
    component_data = get_component_from_lock_file(component_addr, component)
    #Forcing fetch from the server
    component_data = None
    # if not available, get component from server
    if component_data == None:
        log.debug(f"Fetching component {component_addr} from server")
        # url = config.get_project_context().config.services.components
        url = "http://127.0.0.1:8000/resistor"
        # headers = {"accept": "application/json", "Content-Type": "application/json"}
        outgoing_data = component.model_dump()
        try:
            response = requests.post(url, json=outgoing_data)
            response.raise_for_status()  # Raises an HTTPError if the response status code is 4xx or 5xx

            component_data['best_component'] = response.json() or {}
        except requests.HTTPError as exc:
            if exc.response.status_code == 404:
                raise NoMatchingComponent(
                    f"No valid component found for $addr",
                    addr=component_addr
                ) from exc
                # raise HTTPException(status_code=404, detail="Resistor not found")
            else:
                raise HTTPException(status_code=exc.response.status_code, detail="An unexpected error occurred")
        except requests.RequestException as exc:
            raise HTTPException(status_code=500, detail=f"An error occurred while requesting: {exc}")


        #TODO: handle errors coming back from the server
        update_lock_file(component_addr, component, component_data)

    #TODO: figure out how to provide the data back to the other functions
    specd_data["mpn"] = component_data["mpn"]
    specd_data["value"] = component_data["value"]
    specd_data["footprint"] = component_data["footprint"]
    specd_data["package"] = component_data["package"]

    return specd_data


# why is this not defined in errors?
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
    component_data = _get_component_data(addr)
    try:
        return component_data["mpn"]
    except KeyError as ex:
        raise MissingData(
            "$addr has no mpn",
            title="No value",
            addr=addr
        ) from ex


def get_specd_value(addr: AddrStr) -> str:
    """
    Return the MPN for a component given its address
    """
    component_data = _get_component_data(addr)
    try:
        return str(component_data["value"])
    except KeyError as ex:
        raise MissingData(
            "$addr has no value",
            title="No value",
            addr=addr
        ) from ex


# Values come from the finally selected
# component, so we need to arbitrate via that data
@cache
#FIXME: what even is a user facing value?
def get_user_facing_value(addr: AddrStr) -> str:
    """
    Return a "value" of a component we can slap in things like
    the BoM and netlist. Doesn't need to be perfect, just
    something to look at.
    """
    component_data = _get_component_data(addr)
    if "value" in component_data:
        return str(component_data["value"])
    else:
        return "?"


# Footprints come from the users' code, so we reference that directly
@cache
def get_footprint(addr: AddrStr) -> str:
    """
    Return the footprint for a component
    """
    component_data = _get_component_data(addr)
    try:
        return component_data["footprint"]
    except KeyError as ex:
        raise MissingData(
            "$addr has no footprint",
            title="No footprint",
            addr=addr
        ) from ex

@cache
def get_package(addr: AddrStr) -> str:
    """
    Return the package for a component
    """
    component_data = _get_component_data(addr)
    try:
        return component_data["package"]
    except KeyError as ex:
        raise MissingData(
            "$addr has no package",
            title="No package",
            addr=addr
        ) from ex


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



# FIXME: this function's requirements might cause a circular dependency
def download_footprint(addr: AddrStr, footprint_dir: Path):
    """
    Take the footprint from the database and make a .kicad_mod file for it
    TODO: clean this mess up
    """
    # Can't deal with this
    return
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