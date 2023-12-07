#%%
import logging
import shutil
from pathlib import Path
import csv
import pandas as pd

from atopile import address
from atopile.address import AddrStr
from atopile.config import Config
from atopile.instance_methods import (
    all_descendants,
    get_data_dict,
    get_lock_data_dict,
    match_components,
)

# %%
# load csv into pandas dataframe
components_df = pd.read_csv("Basic_Parts.csv")


#%%

def get_resistor_lcsc(min_value: float, max_value: float, package: str) -> list[str]:
    """
    Return the LCSC Part # for a resistor given a value and package.
    """
    try:
        component_data = pd.read_csv("Basic_Parts.csv")
        resistors = component_data[component_data["type"] == "Resistor"]
        # Ensure input values are valid
        if min_value > max_value:
            raise ValueError("Minimum value cannot be greater than maximum value")

        filtered_resistors = resistors[(resistors["min_value"] >= min_value) &
                                       (max_value >= resistors["max_value"])&
                                       (resistors["Package"] == package)]


        if filtered_resistors.empty:
            return ""
        # return a list of LCSC Part #s
        return filtered_resistors["LCSC Part #"].to_list()

    except Exception as e:
        return f"Error: {e}"


def get_capacitor_lcsc(min_value: float, max_value: float, package: str, voltage: float = None) -> str:
    """
    Return the LCSC Part # for a capacitor given a value, package, and optional voltage.
    """
    try:
        component_data = pd.read_csv("Basic_Parts.csv")
        capacitors = component_data[component_data["type"] == "Capacitor"]
        # Ensure input values are valid
        if min_value > max_value:
            raise ValueError("Minimum value cannot be greater than maximum value")
        filtered_capacitors = capacitors[(capacitors["min_value"] >= min_value) &
                                        (capacitors["max_value"] <= max_value) &
                                        (capacitors["Package"] == package)]

        if voltage is not None:
            filtered_capacitors = filtered_capacitors[filtered_capacitors["voltage"] >= voltage]

        if filtered_capacitors.empty:
            return ""
        return filtered_capacitors["LCSC Part #"].to_list()

    except Exception as e:
        return f"Error: {e}"

# function to return all data for a component given LCSC Part #
def get_component_data_by_lscs(lcsc: str) -> dict:
    """
    Return all data for a component given LCSC Part #
    """
    # get the LCSC Part # for the component
    # lcsc = get_mpn(addr)

    # filter the components dataframe by LCSC Part #
    filtered_components = components_df[lcsc == components_df["LCSC Part #"]]

    # if the filtered dataframe is empty, return an empty dictionary
    if filtered_components.empty:
        return {}

    # otherwise, return the dictionary of data for the component
    return filtered_components.to_dict(orient="records")[0]


#%%

# lcsc = get_capacitor_lcsc(components_df, 0, 1, "0603", 10)
lcsc = (get_resistor_lcsc(min_value=1500, max_value=3000, package="0402"))

for lcsc in lcsc:
    print(get_component_data_by_lscs(lcsc))
    # print(lcsc)
#%%
lcsc = get_capacitor_lcsc(min_value=1e-12, max_value=9.5e-12, package="0603", voltage=10)
for lcsc in lcsc:
    print(get_component_data_by_lscs(lcsc))
    print(lcsc)
#%%

def get_mpn(addr: AddrStr) -> str:
    """
    Return the MPN for a component
    """
    # TODO: write me irl
    comp_data = get_data_dict(addr)
    return comp_data["mpn"]


def get_value(addr: AddrStr) -> str:
    """
    Return the value for a component
    """
    # TODO: write me irl
    comp_data = get_data_dict(addr)
    return comp_data["value"]


def get_footprint(addr: AddrStr) -> str:
    """
    Return the footprint for a component
    """
    # TODO: write me irl
    comp_data = get_data_dict(addr)
    user_footprint_name = comp_data["footprint"]
    return user_footprint_name


class DesignatorManager:
    """TODO:"""

    def __init__(self) -> None:
        self._designators: dict[AddrStr, str] = {}

    def _make_designators(self, root: str) -> dict[str, str]:
        designators: dict[str, str] = {}
        unnamed_components = []
        used_designators = set()

        # first pass: grab all the designators from the lock data
        for component in filter(match_components, all_descendants(root)):
            designator = get_lock_data_dict(component).get("designator")
            if designator:
                used_designators.add(designator)
                designators[component] = designator
            else:
                unnamed_components.append(component)

        # second pass: assign designators to the unnamed components
        for component in unnamed_components:
            prefix = get_data_dict(component).get("designator_prefix", "U")

            i = 1
            while f"{prefix}{i}" in used_designators:
                i += 1

            designators[component] = f"{prefix}{i}"
            used_designators.add(designators[component])
            get_lock_data_dict(component)["designator"] = designators[component]

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


def consolidate_footprints(project_config: Config) -> None:
    """Consolidate all the project's footprints into a single directory."""
    log = logging.getLogger("build.footprints")

    fp_target = project_config.paths.abs_build / "footprints" / "footprints.pretty"
    fp_target.mkdir(exist_ok=True)

    for fp in project_config.paths.abs_src.glob("**/*.kicad_mod"):
        try:
            shutil.copy(fp, fp_target)
        except shutil.SameFileError:
            log.warning("Footprint %s already exists in the target directory", fp)
