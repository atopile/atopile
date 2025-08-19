import contextlib
import json
import logging
import tempfile
from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from pathlib import Path

from atopile.config import config
from atopile.errors import UserExportError
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver
from faebryk.exporters.bom.jlcpcb import write_bom_jlcpcb
from faebryk.exporters.documentation.i2c import export_i2c_tree
from faebryk.exporters.netlist.kicad.netlist_kicad import (
    attach_kicad_info,
    faebryk_netlist_to_kicad,
)
from faebryk.exporters.netlist.netlist import make_fbrk_netlist_from_graph
from faebryk.exporters.parameters.parameters_to_file import export_parameters_to_file
from faebryk.exporters.pcb.kicad.artifacts import (
    KicadCliExportError,
    export_3d_board_render,
    export_dxf,
    export_gerber,
    export_glb,
    export_pick_and_place,
    export_step,
    export_svg,
    githash_layout,
)
from faebryk.exporters.pcb.pick_and_place.jlcpcb import (
    convert_kicad_pick_and_place_to_jlcpcb,
)
from faebryk.exporters.pcb.testpoints.testpoints import export_testpoints
from faebryk.libs.exceptions import accumulate
from faebryk.libs.util import DAG


@contextlib.contextmanager
def _githash_layout(layout: Path) -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_layout = githash_layout(layout, Path(tmpdir) / layout.name)
        yield tmp_layout


MusterFuncType = Callable[[Module, Solver], None]


@dataclass
class MusterTarget:
    name: str
    aliases: list[str]
    requires_kicad: bool
    func: MusterFuncType
    implicit: bool = True
    virtual: bool = False
    dependencies: list["MusterTarget"] = field(default_factory=list)

    def __call__(self, app: Module, solver: Solver) -> None:
        return self.func(app, solver)


class Muster:
    """A class to register targets to."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.targets: dict[str, MusterTarget] = {}
        self.dependency_dag: DAG[str] = DAG()
        self.log = logger or logging.getLogger(__name__)

    def add_target(self, target: MusterTarget) -> MusterTarget:
        """Register a function as a target."""
        assert target.name not in self.targets, (
            f"Target '{target.name}' already registered"
        )
        self.targets[target.name] = target

        self.dependency_dag.add_or_get(target.name)
        for dep in target.dependencies:
            assert dep.name in self.targets, (
                f"Dependency '{dep.name}' for target '{target.name}' not yet registered"
            )
            self.dependency_dag.add_edge(dep.name, target.name)

        return target

    def register(
        self,
        name: str | None = None,
        aliases: list[str] | None = None,
        requires_kicad: bool = False,
        dependencies: list["MusterTarget"] | None = None,
        virtual: bool = False,
    ) -> Callable[[Callable[[Module, Solver], None]], MusterTarget]:
        """Register a target under a given name."""

        def decorator(func: Callable[[Module, Solver], None]) -> MusterTarget:
            target_name = name or func.__name__
            target = MusterTarget(
                name=target_name,
                aliases=aliases or [],
                requires_kicad=requires_kicad,
                func=func,
                dependencies=dependencies or [],
                virtual=virtual,
            )
            self.add_target(target)
            return target

        return decorator

    def select(self, selected_targets: set[str] = {"all"}) -> list[MusterTarget]:
        """
        Returns selected targets in topologically sorted order based on dependencies.
        """
        subgraph = self.dependency_dag.get_subgraph(
            selector_func=lambda name: name in selected_targets
            or any(alias in selected_targets for alias in self.targets[name].aliases)
        )

        sorted_names = subgraph.topologically_sorted()

        for target in self.targets.values():
            if target.name in selected_targets:
                target.implicit = False

        return [self.targets[name] for name in sorted_names if name in self.targets]

    def get_dependency_tree(self) -> str:
        tree = self.dependency_dag.to_tree()
        return tree.pretty()


muster = Muster()


@muster.register("bom")
def generate_bom(app: Module, solver: Solver) -> None:
    """Generate a BOM for the project."""
    write_bom_jlcpcb(
        app.get_children_modules(types=Module),
        config.build.paths.output_base.with_suffix(".bom.csv"),
    )


@muster.register("netlist")
def generate_netlist(app: Module, solver: Solver) -> None:
    """Generate a netlist for the project."""
    attach_kicad_info(app.get_graph())

    fbrk_netlist = make_fbrk_netlist_from_graph(app.get_graph())
    kicad_netlist = faebryk_netlist_to_kicad(fbrk_netlist)

    netlist_path = config.build.paths.netlist
    netlist_path.parent.mkdir(parents=True, exist_ok=True)
    kicad_netlist.dumps(netlist_path)


@muster.register(name="glb", aliases=["3d-model"], requires_kicad=True)
def generate_glb(app: Module, solver: Solver) -> None:
    """Generate PCBA 3D model as GLB. Used for 3D preview in extension."""
    with _githash_layout(config.build.paths.layout) as tmp_layout:
        try:
            export_glb(
                tmp_layout,
                glb_file=config.build.paths.output_base.with_suffix(".pcba.glb"),
                project_dir=config.build.paths.layout.parent,
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate 3D model: {e}") from e


@muster.register(name="step", requires_kicad=True)
def generate_step(app: Module, solver: Solver) -> None:
    """Generate PCBA 3D model as STEP."""
    with _githash_layout(config.build.paths.layout) as tmp_layout:
        try:
            export_step(
                tmp_layout,
                step_file=config.build.paths.output_base.with_suffix(".pcba.step"),
                project_dir=config.build.paths.layout.parent,
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate STEP file: {e}") from e


@muster.register("3d-models", dependencies=[generate_glb, generate_step], virtual=True)
def generate_3d_models(app: Module, solver: Solver) -> None:
    """Generate PCBA 3D model as GLB and STEP."""
    pass


@muster.register(name="3d-image", requires_kicad=True)
def generate_3d_render(app: Module, solver: Solver) -> None:
    """Generate PCBA 3D rendered image."""
    with _githash_layout(config.build.paths.layout) as tmp_layout:
        try:
            export_3d_board_render(
                tmp_layout,
                image_file=config.build.paths.output_base.with_suffix(".pcba.png"),
                project_dir=config.build.paths.layout.parent,
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate 3D rendered image: {e}") from e


@muster.register(name="2d-image", requires_kicad=True)
def generate_2d_render(app: Module, solver: Solver) -> None:
    """Generate PCBA 2D rendered image."""
    with _githash_layout(config.build.paths.layout) as tmp_layout:
        try:
            export_svg(
                tmp_layout,
                svg_file=config.build.paths.output_base.with_suffix(".pcba.svg"),
                flip_board=False,
                project_dir=config.build.paths.layout.parent,
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate 2D rendered image: {e}") from e


@muster.register("mfg-data", requires_kicad=True, dependencies=[generate_3d_models])
def generate_manufacturing_data(app: Module, solver: Solver) -> None:
    """
    Generate manufacturing artifacts for the project.
    - DXF
    - Gerber zip
    - Pick and place (default and JLCPCB)
    - Testpoint-location
    """
    with _githash_layout(config.build.paths.layout) as tmp_layout:
        try:
            export_dxf(
                tmp_layout,
                dxf_file=config.build.paths.output_base.with_suffix(".pcba.dxf"),
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate DXF file: {e}") from e

        try:
            export_gerber(
                tmp_layout,
                gerber_zip_file=config.build.paths.output_base.with_suffix(
                    ".gerber.zip"
                ),
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate Gerber file: {e}") from e

        pnp_file = config.build.paths.output_base.with_suffix(".pick_and_place.csv")
        try:
            export_pick_and_place(tmp_layout, pick_and_place_file=pnp_file)
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate Pick and Place file: {e}") from e

        convert_kicad_pick_and_place_to_jlcpcb(
            pnp_file,
            config.build.paths.output_base.with_suffix(".jlcpcb_pick_and_place.csv"),
        )

        export_testpoints(
            app,
            testpoints_file=config.build.paths.output_base.with_suffix(
                ".testpoints.json"
            ),
        )


@muster.register("manifest")
def generate_manifest(app: Module, solver: Solver) -> None:
    """Generate a manifest for the project."""
    with accumulate() as accumulator:
        with accumulator.collect():
            manifest = {}
            manifest["version"] = "2.0"
            for build in config.builds:
                with build:
                    if config.build.paths.layout:
                        by_layout_manifest = manifest.setdefault(
                            "by-layout", {}
                        ).setdefault(str(config.build.paths.layout), {})
                        by_layout_manifest["layouts"] = str(
                            config.build.paths.output_base.with_suffix(".layouts.json")
                        )

            manifest_path = config.project.paths.manifest
            manifest_path.parent.mkdir(exist_ok=True, parents=True)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=4)


@muster.register("variable-report")
def generate_variable_report(app: Module, solver: Solver) -> None:
    """Generate a report of all the variable values in the design."""
    # TODO: support other file formats
    export_parameters_to_file(
        app, solver, config.build.paths.output_base.with_suffix(".variables.md")
    )


@muster.register("i2c-tree")
def generate_i2c_tree(app: Module, solver: Solver) -> None:
    """Generate a Mermaid diagram of the I2C bus tree."""
    export_i2c_tree(
        app, solver, config.build.paths.output_base.with_suffix(".i2c_tree.md")
    )


@muster.register(
    "__default__",
    dependencies=[
        generate_bom,
        generate_netlist,
        generate_manifest,
        generate_variable_report,
        generate_i2c_tree,
    ],
    virtual=True,
)
def default(app: Module, solver: Solver) -> None:
    pass


@muster.register(
    "all",
    aliases=["*"],
    dependencies=[
        generate_bom,
        generate_netlist,
        generate_manufacturing_data,
        generate_3d_models,
        generate_i2c_tree,
        generate_variable_report,
        generate_manifest,
    ],
    virtual=True,
)
def all(app: Module, solver: Solver) -> None:
    """Generate all targets."""
    pass
