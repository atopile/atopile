import logging
from functools import cache
from pathlib import Path

import pandas as pd

from atopile import address, errors, instance_methods, units
from atopile.address import AddrStr

log = logging.getLogger(__name__)


@cache
def _get_pandas_data() -> pd.DataFrame:
    current_file = Path(__file__)
    current_dir = current_file.parent
    data_file = current_dir / "jlc_parts.csv"
    return pd.read_csv(data_file)


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
_GENERICS_MPNS = [_GENERIC_RESISTOR, _GENERIC_CAPACITOR]


_generic_to_type_map = {
    _GENERIC_RESISTOR: "Resistor",
    _GENERIC_CAPACITOR: "Capacitor",
}

# FIXME:
_generic_to_tolerance_map = {
    _GENERIC_RESISTOR: 0.105,
    _GENERIC_CAPACITOR: 0.25,
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


@cache
def _get_generic_from_db(component_addr: str) -> dict:
    """
    Return the MPN for a component given its address
    """
    specd_mpn = _get_specd_mpn(component_addr)
    specd_data = instance_methods.get_data_dict(component_addr)

    df = _get_pandas_data()
    filters = []

    specd_type = _generic_to_type_map[specd_mpn]
    filters.append(f"type == '{specd_type}'")

    # Apply filters we know how to process
    # FIXME: currently this is hard-coded, but once we have the infra for it
    # these params should be toleranced and come straight from the generic
    # component definitions

    # Ensure the component's value is completely contained within the specd value
    try:
        float_value = units.parse_number(specd_data["value"])
    except units.InvalidPhysicalValue as ex:
        ex.addr = component_addr + ".value"
        raise ex

    tolerance = _generic_to_tolerance_map[specd_mpn]

    filters.append(f"min_value > {float_value * (1 - tolerance)}")
    filters.append(f"max_value < {float_value * (1 + tolerance)}")

    # Ensure the component's footprint is correct
    filters.append(f"Package == '{_generics_to_db_fp_map[specd_data['footprint']]}'")

    # Combine filters using reduce
    combined_filter = " & ".join(filters)
    filtered_df = df.query(combined_filter)
    if filtered_df.empty:
        msg = "No component matching spec for $addr \n"
        msg += "\n & ".join(filters)
        raise NoMatchingComponent(msg, addr=component_addr)

    # FIXME: Currently our cost function is dumb - it only knows dollars
    # In the future this cost function should incorporate other things the user is
    # likely to care about
    idx_min = filtered_df["Price (USD)"].idxmin(skipna=True)

    # In this case we seem to hit NaN, which implies we don't have
    # cost info - which is really a bug in the db, but for the users' sake
    # we'll just return the first component
    if pd.isna(idx_min):
        return filtered_df.iloc[0].to_dict()

    return filtered_df.loc[idx_min].to_dict()


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
        return comp_data.get("value", "")

    try:
        return comp_data["value"]
    except KeyError as ex:
        raise MissingData("$addr has no value spec'd", title="No value", addr=addr) from ex


# Values come from the finally selected
# component, so we need to arbitrate via that data
@cache
def get_value(addr: AddrStr) -> str:
    """
    Return the value for a component
    """
    if _is_generic(addr):
        db_data = _get_generic_from_db(addr)
        return f"{db_data['value']} {db_data['unit']}"

    comp_data = instance_methods.get_data_dict(addr)
    # The default is okay here, because we're only generics must have a value
    return comp_data.get("value", "")


# Footprints come from the users' code, so we reference that directly
@cache
def get_footprint(addr: AddrStr) -> str:
    """
    Return the footprint for a component
    """
    comp_data = instance_methods.get_data_dict(addr)
    try:
        return comp_data["footprint"]
    except KeyError as ex:
        raise MissingData(
            "$addr has no footprint", title="No Footprint", addr=addr
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
