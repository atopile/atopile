import json
import logging
import time
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

from atopile import address, errors, instance_methods, units
from atopile.address import AddrStr
from git import Repo, InvalidGitRepositoryError, NoSuchPathError
import warnings

# Filter out specific warnings
warnings.filterwarnings("ignore", message="Detected filter using positional arguments. Prefer using the 'filter' keyword argument instead.")


log = logging.getLogger(__name__)


service_account_path = Path(__file__).parent / 'atopile-dacc978ae7cd.json'

if not firebase_admin._apps:  # Check if already initialized to prevent reinitialization
    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()
_components_db = db.collection('components')  # Replace 'modules' with your actual collection name

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
    if current_data != cached_entry['address_data']:
        log.info(f"Component data has changed for updating cache")
        return True
    return False

def get_component_from_cache(component_addr, current_data):
    """Retrieve a component from the cache, if available, not stale, and unchanged."""
    cached_entry = component_cache.get(component_addr)
    if cached_entry:
        cached_timestamp = datetime.fromtimestamp(cached_entry['timestamp'])
        if (datetime.now() - cached_timestamp < timedelta(days=1)
                and not has_component_changed(cached_entry, current_data)):
            return cached_entry['data']
    return None

def update_cache(component_addr, component_data, address_data):
    """Update the cache with new component data and save it."""
    component_cache[component_addr] = {
        'data': component_data,
        'timestamp': time.time(),  # Current time as a timestamp
        'address_data': dict(address_data)  # Data used to detect changes
    }
    save_cache()

def clean_cache():
    """Clean out entries older than 1 day."""
    for addr, entry in list(component_cache.items()):
        cached_timestamp = datetime.fromtimestamp(entry['timestamp'])
        if datetime.now() - cached_timestamp >= timedelta(days=1):
            del component_cache[addr]
    save_cache()

def _get_generic_from_db(component_addr: str) -> dict:
    """
    Return the MPN for a component given its address
    """
    name = component_addr.split("::")[1]
    # First, try to get the component from the cache
    specd_data = instance_methods.get_data_dict(component_addr)

    # First, try to get the component from the cache
    cached_component = get_component_from_cache(component_addr, specd_data)
    if cached_component:
        log.info(f"Fetching component from cache for {name}")
        return cached_component
    # split component_addr into its parts at the : and take the second part
    log.info(f"Fetching component from db for {name}")
    specd_mpn = _get_specd_mpn(component_addr)
    specd_data = instance_methods.get_data_dict(component_addr)

    specd_type = _generic_to_type_map[specd_mpn]
    tolerance = _generic_to_tolerance_map[specd_mpn]

    try:
        float_value = units.parse_number(specd_data["value"])
    except units.InvalidPhysicalValue as ex:
        ex.addr = component_addr + ".value"
        raise ex

    # Start building your Firestore query
    query = db.collection("components").where("type", "==", specd_type)

    # First, query with one range filter
    min_value = float_value * (1 - tolerance)
    query = query.where("min_value", ">", min_value)

    # Fetch the results
    results = query.stream()
    components = [doc.to_dict() for doc in results]

    # Then, filter in your application code for the second condition
    max_value = float_value * (1 + tolerance)
    filtered_components = [comp for comp in components if comp["max_value"] < max_value]

    # Ensure the component's footprint is correct
    footprint = _generics_to_db_fp_map[specd_data['footprint']]
    query = query.where("Package", "==", footprint)

    # Execute the query
    try:
        results = query.stream()
        components = [doc.to_dict() for doc in results]
    except Exception as e:
        raise e

    min_price_comp = min(components, key=lambda x: x.get('Price (USD)', float('inf')))

    if min_price_comp is None:
        # Handle case where no component is found or all components have NaN or missing price
        raise NoMatchingComponent("No valid component found with a price", addr=component_addr)
    update_cache(component_addr, min_price_comp, specd_data)
    return min_price_comp

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
