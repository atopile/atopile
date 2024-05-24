import logging
from functools import cache
from pathlib import Path

import requests
from pydantic import BaseModel

import atopile.config
from atopile import address, errors, instance_methods
from atopile.address import AddrStr
from atopile.components import abstract

log = logging.getLogger(__name__)


class Component(BaseModel):
    __type__ = None  # Must be replaced in subclasses

    address: AddrStr

    mpn: str
    footprint: str
    get_user_facing_value: str


def ensure_concrete_component(
    component_model: abstract.Component,
) -> Component:
    """Fetch a concrete component from the lock-file or component server."""
    # If the component is already concrete, return it
    if component_model.mpn is not None:
        return component_model

    # Otherwise, see if it's in the lock-file
    with atopile.config.lock_file_context() as lock_file:
        selected_components = lock_file.setdefault("manufacturing_data", {})
        component_key = repr(component_model)
        if component_key in selected_components:
            return component_model.__class__(lock_file[component_key])

        # Otherwise, fetch it from the component server
        concrete_component = fetch_component(component_model)
        selected_components[component_key] = (
            concrete_component.model_dump()
        )  # Cache the component

    return concrete_component


def fetch_component(component_model: abstract.Component) -> Component:
    """Fetch a component from the component server."""
    api_query = component_model.to_api()
    endpoint_base = atopile.config.get_project_context().config.services.components
    endpoint = f"{endpoint_base}/{component_model.__endpoint__}"

    # Make the noise!
    try:
        response = requests.post(endpoint, json=api_query.model_dump(), timeout=10)
        response.raise_for_status()  # Raises an HTTPError if the response status code is 4xx or 5xx
    except requests.HTTPError as ex:
        if response.status_code == 404:
            raise atopile.errors.AtoInfraError(
                "Could not connect to server. Check internet, or please try again later!"
            ) from ex
        # TODO: handle component not found
        raise atopile.errors.AtoInfraError from ex

    return component_model.from_api(response.json()[0]["component_data"])


# FIXME: in the future, we should have a model that provides this information throughout our pipeline
# For the minute, let's use this function
@cache
def _get_component_data(component_addr: str) -> Component:
    """
    Return the MPN and data fields for a component given its address
    """
    # The process is the following:
    # 1. Get the specd data from the instance methods
    # 2. If the component can be fetched from the server and doesn't have an MPN attached, we try to fetch it
    # 2.1. Fetch from the lock file. If we can find a component there, great. If we can't proceed to the next step.
    # 2.2. Fetch from the database. If we can find a component, great. If we can't, throw an error
    # 3. Else, provide the data back
    specd_data = instance_methods.get_data_dict(component_addr)

    # 2. check if the component can be fetched from the database.
    if "mpn" in specd_data:
        log.log(logging.NOTSET, "Component %s has a provided MPN", component_addr)
        return specd_data

    # In this case the component isn't generic, and there's no MPN provided
    # which means the user has neglected to provide one. We can't do anything
    # TODO: does this shove the error in the middle of querying the value, for
    # example? Shouldn't we be able to get the value independently of the MPN?
    if "__type__" not in specd_data:
        raise errors.AtoError("Component is missing an mpn", addr=component_addr)

    ato_model = abstract.construct_ato_model(specd_data)
    return abstract.ensure_concrete_component(ato_model)


# We cache the MPNs to ensure we select the same component if it's hit multiple times
# in a build
@cache
def get_mpn(addr: AddrStr) -> str:
    """
    Return the MPN for a component
    """
    component_data = _get_component_data(addr)
    return component_data.value


# Values come from the finally selected
# component, so we need to arbitrate via that data
@cache
# FIXME: what even is a user facing value?
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
        raise abstract.MissingData(
            "$addr has no footprint", title="No footprint", addr=addr
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
        for err_handler, component in errors.iter_through_errors(
            filter(
                instance_methods.match_components,
                instance_methods.all_descendants(root),
            )
        ):
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
