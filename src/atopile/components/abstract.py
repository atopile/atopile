"""
Module to interact with the component server.
"""

from typing import Optional

import requests
from pydantic import BaseModel, ValidationError, model_validator

import atopile.config
import atopile.errors
import atopile.front_end
from atopile.address import AddrStr
from atopile.front_end import RangedValue
from atopile.instance_methods import get_data


# why is this not defined in errors?
class MissingData(atopile.errors.AtoError):
    """
    Raised when a component is missing data in the Basic_Parts.csv file.
    """


class NoMatchingComponent(atopile.errors.AtoError):
    """
    Raised when there's no component matching the given parameters in jlc_parts.csv
    """

    title = "No component matches parameters"


class Component(BaseModel):
    __type__ = None  # Must be replaced in subclasses

    mpn: Optional[str]
    footprint: Optional[str] = None
    package: Optional[str] = None


class Resistor(BaseModel):
    """Resistor component model."""
    resistance_ohms_min: Optional[float] = None
    rated_power_watts: Optional[float] = None
    rated_temp: RangedValue = None


def get_specd_value(addr: AddrStr) -> str:
    """
    Return the MPN for a component given its address
    """
    try:
        return str(get_data(addr, "value"))
    except KeyError as ex:
        raise MissingData("$addr has no value", title="No value", addr=addr) from ex


def construct_ato_model(ato_data: dict) -> model.Capacitor | model.Resistor | model.Inductor:
    """Make an API query from an ato data dictionary."""
    # In this case the component isn't generic, and there's no MPN provided
    # which means the user has neglected to provide one. We can't do anything
    # TODO: does this shove the error in the middle of querying the value, for
    # example? Shouldn't we be able to get the value independently of the MPN?
    if "__type__" not in ato_data:
        raise TypeError

    type_name = ato_data["__type__"]

    if type_name not in _type_name_to_ato_query_map:
        raise atopile.errors.AtoTypeError(f"Unknown component type: {type_name}")

    ato_type = _type_name_to_ato_query_map[type_name]

    # Find the schema for the API schema for the component
    try:
        return ato_type(**ato_data)
    except ValidationError as ex:
        raise atopile.errors.AtoError(f"Invalid component data: {ex}")


def ensure_concrete_component(component_model: model.ATOPILE_COMPONENTS) -> model.ATOPILE_COMPONENTS:
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
        selected_components[component_key] = concrete_component.model_dump() # Cache the component

    return concrete_component


def fetch_component(component_model: model.ATOPILE_COMPONENTS) -> model.ATOPILE_COMPONENTS:
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
