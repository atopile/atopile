import logging
import itertools
from pathlib import Path
from typing import Optional

import ruamel.yaml

from atopile.model.accessors import ModelVertexView
from atopile.model.model import VertexType
from atopile.project.config import BaseConfig
from atopile.project.project import Project
from atopile.targets.targets import Target, TargetCheckResult, TargetMuster

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

yaml = ruamel.yaml.YAML()
yaml.preserve_quotes = True


class KicadLibPathConfig(BaseConfig):
    @property
    def kicad_project_dir(self) -> Path:
        rel_path = self._config_data.get("kicad-project-dir", "../layout")
        return (self.project.root / rel_path).resolve().absolute()


class KicadLibPath(Target):
    name = "kicad_lib_paths"

    def __init__(self, muster: TargetMuster) -> None:
        self.component_path_to_lib_name: Optional[dict[str, str]] = None
        self.lib_name_to_lib_path: Optional[dict[str, Path]] = None
        super().__init__(muster)

    @property
    def config(self) -> KicadLibPathConfig:
        return KicadLibPathConfig.from_config(super().build_config)

    def generate(self) -> None:
        # iterate over all the footprint properties in the project
        # name to absolute path map
        # dictionary 1: map for kicad netlist generator eg lib1 = /home/user/elec/layout/lib1.pretty
        # dicationary 2: ato component path to lib name map

        # project.py get_abs import path
        self.component_path_to_lib_name = {}
        self.lib_name_to_lib_path = {}

        root_node = ModelVertexView.from_path(self.model, self.build_config.root_node)
        components = root_node.get_descendants(VertexType.component)
        component_path_to_project_root: dict[str, Path] = {}
        for component in components:
            # FIXME: this trash
            footprint_definer = None

            component_footprint: str = component.data.get("footprint")
            if not component_footprint:
                log.error("Component %s has no footprint", component.path)
                continue

            for candidate_footprint_definer in itertools.chain([component, component.instance_of], component.instance_of.superclasses):
                if candidate_footprint_definer.data.get("footprint") == component.data.get("footprint"):
                    footprint_definer = candidate_footprint_definer
                else:
                    break

            if not footprint_definer:
                log.error("Could not find footprint definer for %s", component.path)
                self.elevate_check_result(TargetCheckResult.UNSOLVABLE)
                continue

            if ":" in component_footprint and not component_footprint.startswith("lib:"):
                log.info("Component %s has a lib spec'd for its footprint %s.\n Ignoring in fp-lib-path", component.path, component_footprint)
                continue

            footprint_definer_path = self.project.get_abs_import_path_from_std_path(
                Path(footprint_definer.file_path)
            )
            component_path_to_project_root[component.path] = Project.from_path(footprint_definer_path).root

        # find unique lib paths
        unique_project_roots = set(component_path_to_project_root.values())
        project_root_to_lib_name: dict[Path, str] = {}

        for i, project_root in enumerate(unique_project_roots):
            project = Project.from_path(project_root)
            path = project.config.paths.lib_path
            name = "lib" + str(i)
            self.lib_name_to_lib_path[name] = path
            project_root_to_lib_name[project_root] = name

        # component name to lib name
        for component_path, project_root in component_path_to_project_root.items():
            self.component_path_to_lib_name[component_path] = project_root_to_lib_name[
                project_root
            ]

    def check(self) -> TargetCheckResult:
        return TargetCheckResult.SOLVABLE

    def build(self) -> None:
        """Builds fp-lib-table"""
        if self.component_path_to_lib_name is None or self.lib_name_to_lib_path is None:
            self.generate()

        fp_lib_table = ["(fp_lib_table", "  (version 7)"]

        for lib_name, lib_path in self.lib_name_to_lib_path.items():
            lib_entry = f'  (lib (name "{lib_name}")(type "KiCad")(uri "{lib_path}")(options "")(descr ""))'
            fp_lib_table.append(lib_entry)

        fp_lib_table.append(")")

        fp_lib_table_str = "\n".join(fp_lib_table)

        # Now you have the fp-lib-table as a string. You can write it to a file in the project under elec/layout.
        kicad_project_dir = self.config.kicad_project_dir
        with open(kicad_project_dir / "fp-lib-table", "w", encoding="utf-8") as f:
            f.write(fp_lib_table_str)

    def resolve(self, *args, clean=None, **kwargs) -> None:
        log.info("Nothing to see here folks")
