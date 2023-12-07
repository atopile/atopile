import logging
import shutil
from pathlib import Path

from atopile import address
from atopile.address import AddrStr
from atopile.config import Config
from atopile.instance_methods import (
    all_descendants,
    get_data_dict,
    get_lock_data_dict,
    match_components,
)


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
