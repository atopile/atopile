import contextlib
import itertools
import json
import logging
import tempfile
import time
from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from textwrap import dedent

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile import buildutil, layout
from atopile.buildutil import BuildContext, BuildStepContext
from atopile.cli.logging_ import LoggingStage
from atopile.compiler import format_message
from atopile.compiler.build import build_stage_2
from atopile.config import BuildType, config
from atopile.errors import (
    UserBadParameterError,
    UserException,
    UserExportError,
    UserPickError,
)
from faebryk.core.solver.solver import Solver
from faebryk.exporters.bom.jlcpcb import write_bom
from faebryk.exporters.documentation.datasheets import export_datasheets

# from faebryk.exporters.documentation.i2c import export_i2c_tree
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
from faebryk.exporters.pcb.layout.layout_sync import LayoutSync
from faebryk.exporters.pcb.pick_and_place.jlcpcb import (
    convert_kicad_pick_and_place_to_jlcpcb,
)
from faebryk.exporters.pcb.testpoints.testpoints import export_testpoints
from faebryk.exporters.power_tree.power_tree import export_power_tree
from faebryk.libs.app.checks import check_design
from faebryk.libs.app.designators import (
    attach_random_designators,
    load_kicad_pcb_designators,
)
from faebryk.libs.app.erc import needs_erc_check
from faebryk.libs.app.keep_picked_parts import load_part_info_from_pcb
from faebryk.libs.app.pcb import (
    check_net_names,
    load_net_names,
)
from faebryk.libs.app.picking import save_part_info_to_pcb
from faebryk.libs.exceptions import accumulate, iter_leaf_exceptions
from faebryk.libs.kicad.fileformats import Property, kicad
from faebryk.libs.net_naming import attach_net_names
from faebryk.libs.nets import bind_electricals_to_fbrk_nets
from faebryk.libs.picker.picker import (
    PickError,
    pick_part_recursively,
)
from faebryk.libs.util import DAG, md_table

logger = logging.getLogger(__name__)


MAX_PCB_DIFF_LENGTH = 100


class Tags(StrEnum):
    REQUIRES_KICAD = "requires_kicad"


@contextlib.contextmanager
def _githash_layout(layout: Path) -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_layout = githash_layout(layout, Path(tmpdir) / layout.name)
        yield tmp_layout


MusterFuncType = Callable[[BuildStepContext, LoggingStage], None]


@dataclass
class MusterTarget:
    name: str
    aliases: list[str]
    func: MusterFuncType
    description: str | None = None
    implicit: bool = True
    virtual: bool = False
    dependencies: list["MusterTarget"] = field(default_factory=list)
    tags: set[Tags] = field(default_factory=set)
    produces_artifact: bool = False  # TODO: as list of file paths
    success: bool | None = None

    def __call__(self, ctx: BuildStepContext) -> None:
        if not self.virtual:
            try:
                with LoggingStage(
                    self.name,
                    self.description or f"Building '{self.name}'",
                ) as log_context:
                    self.func(ctx, log_context)
            except Exception:
                self.success = False
                raise

        self.success = True

    @property
    def succeeded(self) -> bool:
        return self.success is True


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
        description: str | None = None,
        virtual: bool = False,
        dependencies: list["MusterTarget"] | None = None,
        tags: set[Tags] | None = None,
        produces_artifact: bool = False,
    ) -> Callable[[MusterFuncType], MusterTarget]:
        """Register a target under a given name."""

        def decorator(func: MusterFuncType) -> MusterTarget:
            target_name = name or getattr(func, "__name__", "unnamed")
            target = MusterTarget(
                name=target_name,
                aliases=aliases or [],
                func=func,
                description=description,
                dependencies=dependencies or [],
                virtual=virtual,
                tags=tags or set(),
                produces_artifact=produces_artifact,
            )
            self.add_target(target)
            return target

        return decorator

    def select(self, selected_targets: set[str]) -> Generator[MusterTarget, None, None]:
        """
        Returns selected targets in topologically sorted order based on dependencies.
        """
        with accumulate() as accumulator:
            for target in selected_targets:
                with accumulator.collect():
                    if target not in self.targets:
                        raise UserBadParameterError(
                            f"Target `{target}` not recognized."
                        )

        subgraph = self.dependency_dag.get_subgraph(
            selector_func=lambda name: name in selected_targets
            or any(alias in selected_targets for alias in self.targets[name].aliases)
        )

        sorted_names = subgraph.topologically_sorted()

        for target in self.targets.values():
            if target.name in selected_targets:
                target.implicit = False

        for target in [
            self.targets[name] for name in sorted_names if name in self.targets
        ]:
            if all(dep.succeeded for dep in target.dependencies or []):
                yield target


muster = Muster()


@muster.register(
    "init-build-context",
    description="Initializing build context",
)
def init_build_context_step(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    if ctx.build is not None or ctx.app is not None:
        return

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    match config.build.build_type:
        case BuildType.ATO:
            from atopile.compiler.build import Linker, StdlibRegistry, build_file

            stdlib = StdlibRegistry(tg)
            linker = Linker(config, stdlib, tg)
            result = build_file(
                g=g,
                tg=tg,
                import_path=config.build.entry_file_path.name,
                path=config.build.entry_file_path,
            )
            build_stage_2(g=g, tg=tg, linker=linker, result=result)

            app_type = result.state.type_roots[config.build.entry_section]
            ctx.build = BuildContext(
                g=g,
                tg=tg,
                build_type=config.build.build_type,
                app_type=app_type,
                linker=linker,
                result=result,
            )
        case BuildType.PYTHON:
            app_class = buildutil._load_python_app_class()
            ctx.build = BuildContext(
                g=g,
                tg=tg,
                build_type=config.build.build_type,
                app_class=app_class,
            )
        case _:
            raise ValueError(f"Unknown build type: {config.build.build_type}")


@muster.register(
    "modify-typegraph",
    description="Modify type graph",
    dependencies=[init_build_context_step],
)
def modify_typegraph(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """Hook for typegraph mutations before instantiation."""
    if ctx.build is None:
        return


@muster.register(
    "instantiate-app",
    description="Instantiate app",
    dependencies=[modify_typegraph],
)
def instantiate_app_step(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    if ctx.app is not None:
        return
    build_ctx = ctx.require_build()

    match build_ctx.build_type:
        case BuildType.ATO:
            from atopile.compiler import DslRichException, DslTypeError

            if build_ctx.app_type is None:
                raise ValueError("Missing app_type for ATO build context")

            try:
                app_root = build_ctx.tg.instantiate_node(
                    type_node=build_ctx.app_type,
                    attributes={},
                )
            except fbrk.TypeGraphInstantiationError as e:
                message = format_message(e)
                raise DslRichException(
                    message=message,
                    original=DslTypeError(message),
                    source_node=fabll.Node.bind_instance(e.node) if e.node else None,
                ) from e

            app = fabll.Node.bind_instance(app_root)
            F.Parameters.NumericParameter.infer_units_in_tree(app)
            F.Parameters.NumericParameter.validate_predicate_units_in_tree(app)
        case BuildType.PYTHON:
            from atopile import errors

            if build_ctx.app_class is None:
                raise ValueError("Missing app_class for PYTHON build context")

            try:
                app = build_ctx.app_class.bind_typegraph(
                    tg=build_ctx.tg
                ).create_instance(g=build_ctx.g)
            except Exception as e:
                raise errors.UserPythonConstructionError(
                    f"Cannot construct build entry {config.build.address}"
                ) from e

            fabll.Traits.create_and_add_instance_to(app, F.is_app_root)
            app.no_include_parents_in_full_name = True
        case _:
            raise ValueError(f"Unknown build type: {build_ctx.build_type}")

    build_ctx.app = app
    ctx.app = app


@muster.register(
    "prepare-build",
    description="Preparing build",
    dependencies=[instantiate_app_step],
)
def prepare_build(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    app = ctx.require_app()
    ctx.solver = Solver()
    if ctx.pcb is None:
        ctx.pcb = (
            F.PCB.bind_typegraph(app.tg)
            .create_instance(g=app.g)
            .setup(
                path=str(config.build.paths.layout),
                app=app,
            )
        )

    solver = ctx.require_solver()
    pcb = ctx.require_pcb()

    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)
    fabll.Traits.create_and_add_instance_to(app, F.PCB.has_pcb).setup(pcb)

    layout.attach_sub_pcbs_to_entry_points(app)

    # TODO remove, once erc split up
    fabll.Traits.create_and_add_instance_to(app, needs_erc_check)


@muster.register(
    "post-instantiation-graph-check",
    description="Verify instance graph",
    dependencies=[prepare_build],
)
def post_instantiation_graph_check(
    ctx: BuildStepContext, log_context: LoggingStage
) -> None:
    """
    Run POST_INSTANTIATION_GRAPH_CHECK checks for early graph validation.

    This runs FIRST and includes:
    - Applying default constraints (has_default_constraint)
    - Early graph validation to catch malformed connections
    """
    app = ctx.require_app()
    check_design(
        app,
        stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_GRAPH_CHECK,
        exclude=tuple(set(config.build.exclude_checks)),
    )


@muster.register(
    "post-instantiation-setup",
    description="Modify instance graph",
    dependencies=[post_instantiation_graph_check],
)
def post_instantiation_setup(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """
    Run POST_INSTANTIATION_SETUP checks which modify the graph structure.

    This includes:
    - Connecting deprecated aliases (ElectricPower vcc/gnd)
    - Connecting electric references (has_single_electric_reference)
    """
    app = ctx.require_app()
    check_design(
        app,
        stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP,
        exclude=tuple(set(config.build.exclude_checks)),
    )

    F.is_alias_bus_parameter.resolve_bus_parameters(app.g, app.tg)
    F.is_sum_bus_parameter.resolve_bus_parameters(app.g, app.tg)


@muster.register(
    "post-instantiation-design-check",
    description="Verify electrical design",
    dependencies=[post_instantiation_setup],
)
def post_instantiation_design_check(
    ctx: BuildStepContext, log_context: LoggingStage
) -> None:
    """
    Run POST_INSTANTIATION_DESIGN_CHECK checks for verification and late setup.

    This includes:
    - Setting address lines based on solved offset (Addressor)
    - Other verification checks
    """
    app = ctx.require_app()
    check_design(
        app,
        stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_DESIGN_CHECK,
        exclude=tuple(set(config.build.exclude_checks)),
    )


@muster.register(
    "load-pcb",
    description="Loading PCB",
    dependencies=[post_instantiation_design_check],
)
def load_pcb(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    pcb = ctx.require_pcb()
    pcb.run_transformer()
    if config.build.keep_designators:
        load_kicad_pcb_designators(pcb.tg, attach=True)


@muster.register("picker", description="Picking parts", dependencies=[load_pcb])
def pick_parts(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    app = ctx.require_app()
    solver = ctx.require_solver()
    if config.build.keep_picked_parts:
        pcb = ctx.require_pcb()
        load_part_info_from_pcb(pcb.transformer.pcb, app.tg)
    try:
        pick_part_recursively(app, solver, progress=log_context)
    except* PickError as ex:
        raise ExceptionGroup(
            "Failed to pick parts for some modules",
            [UserPickError(str(e)) for e in iter_leaf_exceptions(ex)],
        ) from ex
    save_part_info_to_pcb(app)


@muster.register(
    "prepare-nets", description="Preparing nets", dependencies=[pick_parts]
)
def prepare_nets(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    app = ctx.require_app()
    pcb = ctx.require_pcb()
    logger.info("Preparing nets")
    attach_random_designators(app.tg)
    nets = bind_electricals_to_fbrk_nets(app.tg, app.g)

    if len(nets) == 0:
        logger.warning("No nets found")
    for net in nets:
        if net.get_name() is None:
            continue
        logger.info(f"Net with name '{net.get_name()}' found")
    # We have to re-attach the footprints, and subsequently nets, because the first
    # attachment is typically done before the footprints have been created
    # and therefore many nets won't be re-attached properly. Also, we just created
    # and attached them to the design above, so they weren't even there to attach

    pcb.transformer.attach()

    if config.build.keep_net_names:
        loaded_nets = load_net_names(app.tg)
        nets |= loaded_nets

    attach_net_names(nets)
    check_net_names(app.tg)


@muster.register(
    "post-solve-checks",
    description="Running post-solve checks",
    dependencies=[prepare_nets],
)
def post_solve_checks(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    app = ctx.require_app()
    logger.info("Running checks")
    check_design(
        app,
        stage=F.implements_design_check.CheckStage.POST_SOLVE,
        exclude=tuple(set(config.build.exclude_checks)),
    )


@muster.register(
    "update-pcb", description="Updating PCB", dependencies=[post_solve_checks]
)
def update_pcb(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    app = ctx.require_app()
    pcb = ctx.require_pcb()

    def _update_layout(
        pcb_file: kicad.pcb.PcbFile, original_pcb_file: kicad.pcb.PcbFile
    ) -> None:
        pcb_diff = kicad.compare_without_uuid(
            original_pcb_file,
            pcb_file,
        )

        if config.build.frozen:
            if pcb_diff:
                original_path = config.build.paths.output_base.with_suffix(
                    ".original.kicad_pcb"
                )
                updated_path = config.build.paths.output_base.with_suffix(
                    ".updated.kicad_pcb"
                )
                kicad.dumps(original_pcb_file, original_path)
                kicad.dumps(pcb_file, updated_path)

                # TODO: make this a real util
                def _try_relative(path: Path) -> Path:
                    try:
                        return path.relative_to(Path.cwd(), walk_up=True)
                    except ValueError:
                        return path

                original_relative = _try_relative(original_path)
                updated_relative = _try_relative(updated_path)

                diff_length = len(pcb_diff)
                truncated = diff_length > MAX_PCB_DIFF_LENGTH
                truncated_items = diff_length - MAX_PCB_DIFF_LENGTH
                pcb_diff_items = (
                    itertools.islice(pcb_diff.items(), MAX_PCB_DIFF_LENGTH)
                    if truncated
                    else pcb_diff.items()
                )

                raise UserException(
                    dedent(
                        """
                        Built as frozen, but layout changed.

                        Original layout: **{original_relative}**

                        Updated layout: **{updated_relative}**

                        Diff:
                        {diff}{truncated_msg}
                        """
                    ).format(
                        original_relative=original_relative,
                        updated_relative=updated_relative,
                        diff=md_table(
                            [
                                [f"**{path}**", diff["before"], diff["after"]]
                                for path, diff in pcb_diff_items
                            ],
                            headers=["Path", "Before", "After"],
                        ),
                        truncated_msg=f"\n... ({truncated_items} more)"
                        if truncated
                        else "",
                    ),
                    title="Frozen failed",
                )
            else:
                logger.info("No changes to layout. Passed --frozen check.")
        # TODO this is always false
        elif original_pcb_file == pcb_file:
            logger.info(
                "No changes to layout. Not writing %s", config.build.paths.layout
            )
        else:
            logger.info(f"Updating layout {config.build.paths.layout}")
            sync = LayoutSync(pcb_file.kicad_pcb)
            original_fps = {
                addr: fp
                for fp in original_pcb_file.kicad_pcb.footprints
                if (addr := Property.try_get_property(fp.propertys, "atopile_address"))
            }
            current_fps = {
                addr: fp
                for fp in pcb_file.kicad_pcb.footprints
                if (addr := Property.try_get_property(fp.propertys, "atopile_address"))
            }
            new_fps = {k: v for k, v in current_fps.items() if k not in original_fps}
            sync.sync_groups()
            groups_to_update = {
                gname
                for gname, fps in sync.groups.items()
                if {
                    addr
                    for fp, _ in fps
                    if (
                        addr := Property.try_get_property(
                            fp.propertys, "atopile_address"
                        )
                    )
                }.issubset(new_fps)
            }

            for group_name in groups_to_update:
                sync.pull_group_layout(group_name)

            kicad.dumps(pcb_file, config.build.paths.layout)

    # attach subaddresses for lifecycle manager to use
    layout.attach_subaddresses_to_modules(app)

    original_pcb = kicad.copy(pcb.pcb_file)
    pcb.transformer.apply_design()
    pcb.transformer.check_unattached_fps()

    # set layout
    if config.build.hide_designators:
        pcb.transformer.hide_all_designators()

    # Backup layout
    backup_dir = config.build.paths.output_base.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = config.build.paths.output_base.stem
    backup_file = (backup_dir / artifact_name).with_suffix(
        f".{time.strftime('%Y%m%d-%H%M%S')}.kicad_pcb"
    )
    logger.info(f"Backing up layout to {backup_file}")
    backup_file.write_bytes(config.build.paths.layout.read_bytes())
    _update_layout(pcb.pcb_file, original_pcb)


@muster.register(
    "post-pcb-checks", description="Running post-pcb checks", dependencies=[update_pcb]
)
def post_pcb_checks(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    pcb = ctx.require_pcb()
    _ = fabll.Traits.create_and_add_instance_to(pcb, F.PCB.requires_drc_check)
    try:
        check_design(
            pcb,
            stage=F.implements_design_check.CheckStage.POST_PCB,
            exclude=tuple(set(config.build.exclude_checks)),
        )
    except F.PCB.requires_drc_check.DrcException as ex:
        raise UserException(f"Detected DRC violations: \n{ex.pretty()}") from ex


@muster.register("build-design", dependencies=[post_pcb_checks], virtual=True)
def build_design(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    pass


@muster.register(
    "bom",
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_bom(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """Generate a BOM for the project."""
    app = ctx.require_app()
    parts = [
        m.get_trait(F.Pickable.has_part_picked)
        for m in app.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.Pickable.has_part_picked,
        )
        if not m.has_trait(F.has_part_removed)
    ]
    write_bom(parts, config.build.paths.output_base.with_suffix(".bom.csv"))


@muster.register(
    name="glb",
    aliases=["3d-model"],
    tags={Tags.REQUIRES_KICAD},
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_glb(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """Generate PCBA 3D model as GLB. Used for 3D preview in extension."""
    ctx.require_app()
    with _githash_layout(config.build.paths.layout) as tmp_layout:
        try:
            export_glb(
                tmp_layout,
                glb_file=config.build.paths.output_base.with_suffix(".pcba.glb"),
                project_dir=config.build.paths.layout.parent,
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate 3D model: {e}") from e


@muster.register(
    name="step",
    tags={Tags.REQUIRES_KICAD},
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_step(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """Generate PCBA 3D model as STEP."""
    ctx.require_app()
    with _githash_layout(config.build.paths.layout) as tmp_layout:
        try:
            export_step(
                tmp_layout,
                step_file=config.build.paths.output_base.with_suffix(".pcba.step"),
                project_dir=config.build.paths.layout.parent,
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate STEP file: {e}") from e


@muster.register(
    "3d-models",
    dependencies=[generate_glb, generate_step],
    virtual=True,
    produces_artifact=True,
)
def generate_3d_models(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """Generate PCBA 3D model as GLB and STEP."""
    pass


@muster.register(
    name="3d-image",
    tags={Tags.REQUIRES_KICAD},
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_3d_render(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """Generate PCBA 3D rendered image."""
    ctx.require_app()
    with _githash_layout(config.build.paths.layout) as tmp_layout:
        try:
            export_3d_board_render(
                tmp_layout,
                image_file=config.build.paths.output_base.with_suffix(".pcba.png"),
                project_dir=config.build.paths.layout.parent,
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate 3D rendered image: {e}") from e


@muster.register(
    name="2d-image",
    tags={Tags.REQUIRES_KICAD},
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_2d_render(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """Generate PCBA 2D rendered image."""
    ctx.require_app()
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


@muster.register(
    "mfg-data",
    tags={Tags.REQUIRES_KICAD},
    dependencies=[generate_3d_models, post_pcb_checks],
    produces_artifact=True,
)
def generate_manufacturing_data(
    ctx: BuildStepContext, log_context: LoggingStage
) -> None:
    """
    Generate manufacturing artifacts for the project.
    - DXF
    - Gerber zip
    - Pick and place (default and JLCPCB)
    - Testpoint-location
    """
    app = ctx.require_app()
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


@muster.register(
    "manifest",
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_manifest(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """Generate a manifest for the project."""
    ctx.require_app()
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


@muster.register(
    "variable-report",
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_variable_report(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """Generate a report of all the variable values in the design."""
    app = ctx.require_app()
    solver = ctx.require_solver()
    # TODO: support other file formats
    export_parameters_to_file(
        app, solver, config.build.paths.output_base.with_suffix(".variables.md")
    )


@muster.register(
    "power-tree",
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_power_tree(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """Generate power tree visualization and data exports."""
    app = ctx.require_app()
    solver = ctx.require_solver()
    output_dir = config.build.paths.output_base.parent
    export_power_tree(
        app,
        solver,
        mermaid_path=output_dir / "power_tree.md",
    )


@muster.register(
    "datasheets",
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_datasheets(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    app = ctx.require_app()
    export_datasheets(
        app, config.build.paths.documentation / "datasheets", progress=log_context
    )


# @muster.register(
#     "i2c-tree",
#     dependencies=[build_design],
#     produces_artifact=True,
# )
# def generate_i2c_tree(
#     app: fabll.Node, solver: Solver, pcb: F.PCB, log_context: LoggingStage
# ) -> None:
#     """Generate a Mermaid diagram of the I2C bus tree."""
#     export_i2c_tree(
#         app, solver, config.build.paths.output_base.with_suffix(".i2c_tree.md")
#     )


@muster.register(
    "default",
    aliases=["__default__"],  # for backwards compatibility
    dependencies=[
        generate_bom,
        generate_manifest,
        generate_variable_report,
        # generate_power_tree,
        generate_datasheets,
    ],
    virtual=True,
)
def generate_default(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    pass


@muster.register(
    "all",
    aliases=["*"],
    dependencies=[
        generate_default,
        generate_manufacturing_data,
        generate_3d_models,
    ],
    virtual=True,
)
def generate_all(ctx: BuildStepContext, log_context: LoggingStage) -> None:
    """Generate all targets."""
    pass


if __name__ == "__main__":
    # uv run python src/atopile/build_steps.py | dot -T png | imgcat
    print(muster.dependency_dag._to_graphviz().source)
