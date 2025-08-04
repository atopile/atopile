import json
import logging
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from atopile.config import config
from atopile.errors import UserExportError
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver
from faebryk.exporters.bom.jlcpcb import write_bom_jlcpcb
from faebryk.exporters.documentation.i2c import export_i2c_tree
from faebryk.exporters.parameters.parameters_to_file import export_parameters_to_file
from faebryk.exporters.pcb.kicad.artifacts import (
    KicadCliExportError,
    export_dxf,
    export_gerber,
    export_glb,
    export_pick_and_place,
    export_step,
    githash_layout,
)
from faebryk.exporters.pcb.pick_and_place.jlcpcb import (
    convert_kicad_pick_and_place_to_jlcpcb,
)
from faebryk.exporters.pcb.testpoints.testpoints import export_testpoints
from faebryk.libs.exceptions import accumulate


@dataclass
class MusterTarget:
    name: str
    default: bool
    requires_kicad: bool
    func: Callable[[Module, Solver], None]
    implicit: bool = True

    def __call__(self, app: Module, solver: Solver) -> None:
        return self.func(app, solver)


class Muster:
    """A class to register targets to."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.targets: dict[str, MusterTarget] = {}
        self.log = logger or logging.getLogger(__name__)

    def add_target(self, target: MusterTarget) -> MusterTarget:
        """Register a function as a target."""
        self.targets[target.name] = target
        return target

    def register(
        self,
        name: str | None = None,
        default: bool = True,
        requires_kicad: bool = False,
    ) -> Callable[[Callable[[Module, Solver], None]], MusterTarget]:
        """Register a target under a given name."""

        def decorator(func: Callable[[Module, Solver], None]) -> MusterTarget:
            target_name = name or func.__name__
            target = MusterTarget(
                name=target_name,
                default=default,
                requires_kicad=requires_kicad,
                func=func,
            )
            self.add_target(target)
            return target

        return decorator


muster = Muster()


@muster.register("bom")
def generate_bom(app: Module, solver: Solver) -> None:
    """Generate a BOM for the project."""
    write_bom_jlcpcb(
        app.get_children_modules(types=Module),
        config.build.paths.output_base.with_suffix(".bom.csv"),
    )


@muster.register("3d-model", default=False, requires_kicad=True)
def generate_3d_model(app: Module, solver: Solver) -> None:
    """Generate PCBA 3D model as GLB. Used for 3D preview in extension."""

    try:
        export_glb(
            config.build.paths.layout,
            glb_file=config.build.paths.output_base.with_suffix(".pcba.glb"),
            project_dir=config.build.paths.layout.parent,
        )
    except KicadCliExportError as e:
        raise UserExportError(f"Failed to generate 3D model: {e}") from e


@muster.register("mfg-data", default=False, requires_kicad=True)
def generate_manufacturing_data(app: Module, solver: Solver) -> None:
    """
    Generate manufacturing artifacts for the project.
    - STEP
    - GLB
    - DXF
    - Gerber zip
    - Pick and place (default and JLCPCB)
    - Testpoint-location
    """
    # Create temp copy of layout file with git hash substituted
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_layout = githash_layout(
            config.build.paths.layout,
            Path(tmpdir) / config.build.paths.layout.name,
        )

        try:
            export_step(
                tmp_layout,
                step_file=config.build.paths.output_base.with_suffix(".pcba.step"),
                project_dir=config.build.paths.layout.parent,
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate STEP file: {e}") from e

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
