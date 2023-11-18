import collections
import enum
import logging
from typing import Any, Dict, List, Union, Optional

from atopile.model.model import Model
from atopile.project.config import BaseConfig, BuildConfig
from atopile.project.project import Project

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

class TargetNotFoundError(Exception):
    """
    The target you are looking for does not exist.
    """

def find_target(target_name: str) -> "Target":
    """Find a target by name."""
    #TODO: fix this entire function and premise
    if target_name == "netlist-kicad6":
        import atopile.targets.netlist.kicad6
        return atopile.targets.netlist.kicad6.Kicad6NetlistTarget
    if target_name == "designators":
        import atopile.targets.designators
        return atopile.targets.designators.Designators
    if target_name == "bom-jlcpcb":
        import atopile.targets.bom.bom_jlcpcb
        return atopile.targets.bom.bom_jlcpcb.BomJlcpcbTarget
    if target_name == "part-map":
        import atopile.targets.part_map
        return atopile.targets.part_map.PartMapTarget
    if target_name == "sch-view":
        import atopile.targets.schematic_view
        return atopile.targets.schematic_view.SchematicViewTarget
    if target_name == "kicad-lib-paths":
        import atopile.targets.netlist.kicad_lib_paths
        return atopile.targets.netlist.kicad_lib_paths.KicadLibPath
    raise TargetNotFoundError(target_name)

class TargetMuster:
    def __init__(self, project: Project, model: Model, build_config: BuildConfig) -> None:
        self.project = project
        self.model = model
        self.build_config = build_config
        self._targets: collections.OrderedDict[str, Target] = collections.OrderedDict()

    @property
    def target_names(self) -> List[str]:
        return list(self._targets.keys())

    @property
    def targets(self) -> List["Target"]:
        return list(self._targets.values())

    @property
    def target_dict(self) -> Dict[str, "Target"]:
        return self._targets

    def ensure_target(self, target: Union[str, "Target"]):
        if target is Target:
            new_target_type = target
        else:
            new_target_type = find_target(target)

        if new_target_type.name not in self._targets:
            new_target: Target = new_target_type(self)
            self._targets[new_target.name] = new_target
            return new_target
        return self._targets[new_target_type.name]

    def reset_target(self, target: Union[str, "Target"]):
        if target is Target:
            new_target_type = target
        else:
            new_target_type = find_target(target)

        self._targets[new_target_type.name] = new_target_type(self)

    def try_add_targets(self, target_names: List[str]) -> None:
        for target_name in target_names:
            try:
                self.ensure_target(target_name)
            except TargetNotFoundError:
                log.error(f"Target {target_name} not found. Attempting to generate remaining targets.")

class TargetCheckResult(enum.IntEnum):
    # data is fully specified so anything
    # untouched between revs will be the same
    COMPLETE = 0

    # there's additional, extraneous data, but what we need is there
    UNTIDY = 1

    # there's enough data to solve deterministically,
    # but if there are any changes in the source,
    # significant changes in the output may occur
    SOLVABLE = 2

    # there's not enough data to solve deterministically
    UNSOLVABLE = 3

class Target:
    def __init__(self, muster: TargetMuster) -> None:
        self.muster = muster
        self._check_result: Optional[TargetCheckResult] = None

    @property
    def project(self) -> Project:
        return self.muster.project

    @property
    def model(self) -> Model:
        return self.muster.model

    @property
    def build_config(self) -> BuildConfig:
        return self.muster.build_config

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def config(self) -> BaseConfig:
        return self.project.config.targets.get(self.name, BaseConfig({}, self.project, self.name))

    @property
    def check_result(self) -> TargetCheckResult:
        # FIXME: I don't think pretending everything is find and dandy is a long-term solution
        if self._check_result is None:
            return TargetCheckResult.COMPLETE
        return self._check_result

    def build(self) -> None:
        """
        Build this targets output and save it to the build directory.
        What gets called when you run `ato build <target>`
        """
        raise NotImplementedError

    def resolve(self, *args, clean=None, **kwargs) -> None:
        """
        Interactively solve for missing data, potentially:
        - prompting the user for more info
        - outputting template files for a user to fill out
        This function is expected to be called manually, and is
        therefore allowed to write to version controlled files.
        This is what's run with the `ato resolve <target>` command.
        """
        raise NotImplementedError

    def check(self) -> TargetCheckResult:
        """
        Check whether all the data required to build this target is available and valid.
        This is what's run with the `ato check <target>` command.
        """
        raise NotImplementedError

    @property
    def check_has_been_run(self) -> bool:
        if self._check_result is None:
            return False
        return True

    def elevate_check_result(self, result: TargetCheckResult) -> None:
        if self._check_result is None or result > self._check_result:
            self._check_result = result

    def generate(self) -> Any:
        """
        Generate and return the underlying data behind the target.
        This isn't available from the command-line and is instead only used internally.
        It provides other targets with access to the data generated by this target.
        """
        raise NotImplementedError
