import contextlib
import itertools
import json
import os
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
from atopile.compiler import format_message
from atopile.compiler.build import build_stage_2
from atopile.config import PROJECT_CONFIG_FILENAME, BuildType, config
from atopile.errors import (
    UserBadParameterError,
    UserException,
    UserExportError,
    UserPickError,
    accumulate,
    iter_leaf_exceptions,
)
from atopile.logging import AtoLogger, get_logger
from atopile.logging_utils import get_status_style, print_bar
from faebryk.core.solver.solver import Solver
from faebryk.exporters.bom.jlcpcb import write_bom
from faebryk.exporters.bom.json_bom import write_json_bom
from faebryk.exporters.documentation.datasheets import export_datasheets

# from faebryk.exporters.documentation.i2c import export_i2c_tree
from faebryk.exporters.parameters.parameters_to_file import export_parameters_to_file
from faebryk.exporters.pcb.kicad.artifacts import (
    KicadCliExportError,
    export_3d_board_render,
    export_dxf,
    export_gerber,
    export_glb,
    export_pcb_summary,
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
    ensure_board_appearance,
    load_net_names,
)
from faebryk.libs.app.picking import save_part_info_to_pcb
from faebryk.libs.kicad.fileformats import Property, kicad
from faebryk.libs.net_naming import attach_net_names
from faebryk.libs.nets import bind_electricals_to_fbrk_nets
from faebryk.libs.picker.picker import PickError, pick_parts_recursively
from faebryk.libs.util import DAG, md_table

logger = get_logger(__name__)


MAX_PCB_DIFF_LENGTH = 100


def _run_stage_ticker(
    *,
    build_id: str,
    build_name: str,
    display_name: str,
    project_root: str,
    target: str,
    stage_name: str,
    stage_id: str,
    stage_display_name: str | None,
    build_started_at: float,
    stage_started_at: float,
    stop_event,
    interval_s: float = 0.25,
) -> None:
    import time

    from atopile.dataclasses import Build, BuildStatus, StageStatus
    from atopile.model.sqlite import BuildHistory

    while not stop_event.wait(interval_s):
        now = time.time()
        elapsed_stage = round(now - stage_started_at, 2)
        elapsed_build = now - build_started_at

        build_info = BuildHistory.get(build_id)
        current_stages = build_info.stages if build_info else []
        updated = False
        new_stages: list[dict] = []

        for stage in current_stages:
            stage_key = stage.get("stageId") or stage.get("stage_id")
            if stage_key == stage_id:
                updated = True
                new_stages.append(
                    {
                        **stage,
                        "name": stage_name,
                        "stageId": stage_id,
                        "displayName": stage_display_name,
                        "status": StageStatus.RUNNING.value,
                        "elapsedSeconds": elapsed_stage,
                    }
                )
            else:
                new_stages.append(stage)

        if not updated:
            new_stages.append(
                {
                    "name": stage_name,
                    "stageId": stage_id,
                    "displayName": stage_display_name,
                    "status": StageStatus.RUNNING.value,
                    "elapsedSeconds": elapsed_stage,
                }
            )

        BuildHistory.set(
            Build(
                build_id=build_id,
                name=build_name,
                display_name=display_name,
                project_root=project_root,
                target=target,
                status=BuildStatus.BUILDING,
                started_at=build_started_at,
                elapsed_seconds=elapsed_build,
                stages=new_stages,
            )
        )


class Tags(StrEnum):
    REQUIRES_KICAD = "requires_kicad"


@contextlib.contextmanager
def _githash_layout(layout: Path) -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_layout = githash_layout(layout, Path(tmpdir) / layout.name)
        yield tmp_layout


MusterFuncType = Callable[[BuildStepContext], None]


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
        if self.virtual:
            self.success = True
            return

        import multiprocessing
        import time

        from atopile.dataclasses import Build, BuildStage, BuildStatus, StageStatus
        from atopile.logging import BuildLogger
        from atopile.model.sqlite import BuildHistory

        ctx.stage = self.name
        BuildLogger.update_stage(self.name)

        start = time.time()
        running_stage = BuildStage(
            name=self.description or self.name,
            stage_id=self.name,
            status=StageStatus.RUNNING,
        )

        build_started_at = start
        if ctx.build_id:
            existing = BuildHistory.get(ctx.build_id)
            if existing and existing.started_at:
                build_started_at = existing.started_at
            BuildHistory.set(
                Build(
                    build_id=ctx.build_id,
                    name=config.build.name,
                    display_name=config.build.name,
                    project_root=str(config.project.paths.root),
                    target=config.build.name,
                    status=BuildStatus.BUILDING,
                    started_at=build_started_at,
                    elapsed_seconds=time.time() - build_started_at,
                    stages=[s.model_dump(by_alias=True) for s in ctx.completed_stages]
                    + [running_stage.model_dump(by_alias=True)],
                )
            )

        stop_event = multiprocessing.Event()
        ticker: multiprocessing.Process | None = None
        if ctx.build_id:
            ticker = multiprocessing.Process(
                target=_run_stage_ticker,
                kwargs={
                    "build_id": ctx.build_id,
                    "build_name": config.build.name,
                    "display_name": config.build.name,
                    "project_root": str(config.project.paths.root),
                    "target": config.build.name,
                    "stage_name": self.description or self.name,
                    "stage_id": self.name,
                    "stage_display_name": None,
                    "build_started_at": build_started_at,
                    "stage_started_at": start,
                    "stop_event": stop_event,
                },
                daemon=True,
            )
            ticker.start()

        succeeded = False
        try:
            self.func(ctx)
            succeeded = True
        finally:
            stop_event.set()
            if ticker and ticker.is_alive():
                ticker.terminate()
            elapsed = round(time.time() - start, 2)
            stage_status = StageStatus.SUCCESS if succeeded else StageStatus.FAILED
            stage_name = self.description or self.name
            ctx.completed_stages.append(
                BuildStage(
                    name=stage_name,
                    stage_id=self.name,
                    elapsed_seconds=elapsed,
                    status=stage_status,
                )
            )
            # In verbose mode, print stage completion bar immediately
            # (so it appears in correct order relative to logs)
            if os.environ.get("ATO_VERBOSE") == "1":
                icon, color = get_status_style(stage_status)
                print_bar(f"{icon} {stage_name} [{elapsed:.1f}s]", style=color)

            if ctx.build_id:
                existing = BuildHistory.get(ctx.build_id)
                started_at = (
                    existing.started_at if existing and existing.started_at else start
                )
                BuildHistory.set(
                    Build(
                        build_id=ctx.build_id,
                        name=config.build.name,
                        display_name=config.build.name,
                        project_root=str(config.project.paths.root),
                        target=config.build.name,
                        status=BuildStatus.BUILDING,
                        started_at=started_at,
                        elapsed_seconds=time.time() - started_at,
                        stages=[
                            s.model_dump(by_alias=True) for s in ctx.completed_stages
                        ],
                    )
                )
            self.success = succeeded

    @property
    def succeeded(self) -> bool:
        return self.success is True


class Muster:
    """A class to register targets to."""

    def __init__(self, log: AtoLogger | None = None) -> None:
        self.targets: dict[str, MusterTarget] = {}
        self.dependency_dag: DAG[str] = DAG()
        self.log = log or get_logger(__name__)

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
def init_build_context_step(ctx: BuildStepContext) -> None:
    if ctx.build is not None or ctx.app is not None:
        return

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    match config.build.build_type:
        case BuildType.ATO:
            from atopile.compiler.build import Linker, StdlibRegistry, build_file

            stdlib = StdlibRegistry(tg)
            linker = Linker(config, stdlib, tg)

            entry_file_path = config.build.entry_file_path
            if not entry_file_path.exists():
                config_file = (config.project_dir / PROJECT_CONFIG_FILENAME).resolve()
                raise UserException(
                    f"Entry file not found: `{entry_file_path.name}`\n\n"
                    f"Expected at:\n{entry_file_path.resolve()}\n\n"
                    f"Check the entry path in your config:\n{config_file}"
                )

            result = build_file(
                g=g,
                tg=tg,
                import_path=entry_file_path.name,
                path=entry_file_path,
            )
            build_stage_2(g=g, tg=tg, linker=linker, result=result)

            entry_section = config.build.entry_section
            if entry_section not in result.state.type_roots:
                available_modules = sorted(result.state.type_roots.keys())
                entry_file = config.build.entry_file_path.resolve()
                config_file = (config.project_dir / PROJECT_CONFIG_FILENAME).resolve()

                if available_modules:
                    modules_list = "\n".join(f"  - `{m}`" for m in available_modules)
                    raise UserException(
                        f"Entry point `{entry_section}` not found in "
                        f"`{entry_file.name}`.\n\n"
                        f"**Available modules in this file:**\n{modules_list}\n\n"
                        f"Check the entry point in your config:\n{config_file}"
                    )
                else:
                    raise UserException(
                        f"Entry point `{entry_section}` not found in "
                        f"`{entry_file.name}`.\n\n"
                        f"No modules, components, or interfaces were found "
                        f"in this file.\n\n"
                        f"Check the entry point in your config:\n{config_file}"
                    )

            app_type = result.state.type_roots[entry_section]
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
def modify_typegraph(ctx: BuildStepContext) -> None:
    """Hook for typegraph mutations before instantiation."""
    if ctx.build is None:
        return


@muster.register(
    "instantiate-app",
    description="Instantiate app",
    dependencies=[modify_typegraph],
)
def instantiate_app_step(ctx: BuildStepContext) -> None:
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
def prepare_build(ctx: BuildStepContext) -> None:
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
def post_instantiation_graph_check(ctx: BuildStepContext) -> None:
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
def post_instantiation_setup(ctx: BuildStepContext) -> None:
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
def post_instantiation_design_check(ctx: BuildStepContext) -> None:
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
    "spice-netlist",
    description="Generating SPICE netlist",
    dependencies=[post_instantiation_design_check],
    produces_artifact=True,
)
def generate_spice_netlist_step(ctx: BuildStepContext) -> None:
    """Generate a SPICE netlist from the atopile graph."""
    try:
        from faebryk.exporters.simulation.ngspice import generate_spice_netlist

        app = ctx.require_app()
        solver = ctx.require_solver()
        netlist, _aliases = generate_spice_netlist(app, solver)
        output_path = config.build.paths.output_base.with_suffix(".spice")
        netlist.write(output_path)
        logger.info(f"SPICE netlist written to {output_path}")
    except Exception:
        logger.warning(
            "SPICE netlist generation failed — skipping simulation", exc_info=True
        )


def _signal_unit(key: str) -> str:
    """Infer unit from signal key."""
    return "A" if key.startswith("i(") else "V"


# ---------------------------------------------------------------------------
# LTTB (Largest-Triangle-Three-Buckets) downsampling
# ---------------------------------------------------------------------------
_MAX_POINTS = 2000  # Visual fidelity limit — no chart is wider than ~2000px


def _lttb_downsample(
    x: list[float], ys: dict[str, list[float]], target: int
) -> tuple[list[float], dict[str, list[float]]]:
    """Downsample time-series using LTTB on the *primary* signal (first in ys).

    All signals share the same index selection so they stay aligned.
    Returns new (x, ys) with at most *target* points.
    """
    n = len(x)
    if n <= target:
        return x, ys

    keys = list(ys.keys())
    primary = ys[keys[0]]  # downsample decision based on primary signal

    # Always keep first and last point
    indices = [0]
    bucket_size = (n - 2) / (target - 2)

    a_idx = 0
    for i in range(1, target - 1):
        # Next bucket boundaries
        b_start = int((i) * bucket_size) + 1
        b_end = int((i + 1) * bucket_size) + 1
        b_end = min(b_end, n)

        # Average of the *next* bucket (look-ahead)
        c_start = int((i + 1) * bucket_size) + 1
        c_end = int((i + 2) * bucket_size) + 1
        c_end = min(c_end, n)
        if c_start >= n:
            c_start = n - 1
        if c_end > n:
            c_end = n
        avg_x = sum(x[c_start:c_end]) / max(c_end - c_start, 1)
        avg_y = sum(primary[c_start:c_end]) / max(c_end - c_start, 1)

        # Pick point in current bucket that maximises triangle area
        best_idx = b_start
        max_area = -1.0
        pa_x = x[a_idx]
        pa_y = primary[a_idx]
        for j in range(b_start, b_end):
            area = abs(
                (x[j] - pa_x) * (avg_y - pa_y) - (avg_x - pa_x) * (primary[j] - pa_y)
            )
            if area > max_area:
                max_area = area
                best_idx = j

        indices.append(best_idx)
        a_idx = best_idx

    indices.append(n - 1)

    new_x = [x[i] for i in indices]
    new_ys = {k: [v[i] for i in indices] for k, v in ys.items()}
    return new_x, new_ys


_limit_expr_cache: dict[str, dict[str, str]] = {}


def _extract_limit_expr(source_file: str, var_name: str) -> str | None:
    """Extract the limit expression from an assertion like
    ``assert req_001.limit within 5V +/- 10%`` in the .ato source file.
    Returns the expression after 'within', e.g. ``5V +/- 10%``.
    """
    import re

    # Cache per file to avoid re-reading for every requirement
    if source_file not in _limit_expr_cache:
        try:
            content = Path(source_file).read_text(encoding="utf-8")
        except Exception:
            return None
        cache: dict[str, str] = {}
        for m in re.finditer(
            r"assert\s+(\w+)\.limit\s+within\s+(.+?)$",
            content,
            re.MULTILINE,
        ):
            cache[m.group(1)] = m.group(2).strip()
        _limit_expr_cache[source_file] = cache

    return _limit_expr_cache.get(source_file, {}).get(var_name)


def _write_requirements_json(
    results, tran_data, group_key_fn, ac_data=None, ac_group_key_fn=None,
    multi_dut_data=None, sim_stats=None, source_file=None,
) -> None:
    """Serialize requirement results + time-series to a JSON artifact."""
    from datetime import datetime, timezone

    import math

    from faebryk.exporters.simulation.simulation_runner import MultiDutResult

    multi_dut_data = multi_dut_data or {}

    reqs_json = []
    for r in results:
        req = r.requirement
        net = r.resolved_net or req.get_net()
        net_key = f"v({net})" if not net.startswith(("v(", "i(")) else net
        try:
            capture = req.get_capture()
        except Exception:
            # Infer capture type from simulation result
            key = group_key_fn(req)
            if key in tran_data:
                capture = "transient"
            elif ac_data and ac_group_key_fn and ac_group_key_fn(req) in ac_data:
                capture = "ac"
            else:
                capture = "transient"  # default
        measurement = req.get_measurement()

        # Determine unit
        if measurement == "overshoot":
            unit = "%"
        elif measurement == "settling_time":
            unit = "s"
        elif measurement == "gain_db":
            unit = "dB"
        elif measurement == "phase_deg":
            unit = "deg"
        elif measurement == "bandwidth_3db":
            unit = "Hz"
        elif measurement == "bode_plot":
            unit = "dB"
        elif measurement == "frequency":
            unit = "Hz"
        elif measurement == "efficiency":
            unit = "%"
        else:
            unit = _signal_unit(net_key)

        actual = r.actual if math.isfinite(r.actual) else None
        context_nets = r.resolved_ctx_nets if r.resolved_ctx_nets is not None else req.get_context_nets()

        # Extract bounds safely (may not be set for some multi-DUT configs)
        try:
            min_val = req.get_min_val()
            typical = req.get_typical()
            max_val = req.get_max_val()
        except ValueError:
            min_val = None
            typical = None
            max_val = None

        entry: dict = {
            "id": req.get_name().replace(" ", "_").replace(":", ""),
            "name": req.get_name(),
            "net": net,
            "capture": capture,
            "measurement": measurement,
            "minVal": min_val,
            "typical": typical,
            "maxVal": max_val,
            "actual": actual,
            "passed": r.passed,
            "unit": unit,
            "contextNets": context_nets,
        }

        # Source metadata for UI editing
        parent_info = req.get_parent()
        if parent_info is not None:
            entry["varName"] = parent_info[1]
        if source_file is not None:
            entry["sourceFile"] = str(source_file)

            # Extract original limit assertion text from .ato source
            var_name = entry.get("varName")
            if var_name:
                limit_expr = _extract_limit_expr(source_file, var_name)
                if limit_expr:
                    entry["limitExpr"] = limit_expr

        # Attach plot specs from render_multi_dut
        if r.plot_specs:
            entry["plotSpecs"] = r.plot_specs

        if r.display_net:
            entry["displayNet"] = r.display_net

        justification = req.get_justification()
        if justification:
            entry["justification"] = justification

        settling_tol = req.get_settling_tolerance()
        if settling_tol is not None:
            entry["settlingTolerance"] = settling_tol

        # Simulation name (override)
        sim_name = req.get_simulation()
        if sim_name:
            entry["simulationName"] = sim_name

        # SPICE source override
        src_override = req.get_source_override()
        if src_override:
            entry["sourceName"] = src_override[0]
            entry["sourceSpec"] = src_override[1]

        # Extra SPICE commands
        extra = req.get_extra_spice()
        if extra:
            entry["extraSpice"] = extra

        # Attach transient config and time-series
        if capture == "transient":
            tran_start = req.get_tran_start() or 0
            tran_stop = req.get_tran_stop()
            tran_step = req.get_tran_step()
            entry["tranStart"] = tran_start
            if tran_stop is not None:
                entry["tranStop"] = tran_stop
            if tran_step is not None:
                entry["tranStep"] = tran_step

            key = group_key_fn(req)
            td = tran_data.get(key)
            if td is not None:
                # Collect relevant signals: primary + context
                # (ngspice already limits data to [start, stop])
                sig_keys = [net_key]
                for ctx_net in context_nets:
                    ctx_key = (
                        f"v({ctx_net})"
                        if not ctx_net.startswith(("v(", "i("))
                        else ctx_net
                    )
                    if ctx_key in td.signals:
                        sig_keys.append(ctx_key)

                signals = {}
                for sk in sig_keys:
                    if sk in td.signals:
                        signals[sk] = list(td.signals[sk])

                time_list = list(td.time)
                time_list, signals = _lttb_downsample(
                    time_list, signals, _MAX_POINTS
                )

                entry["timeSeries"] = {
                    "time": time_list,
                    "signals": signals,
                }

        # Attach AC config
        if capture == "ac":
            ac_start = req.get_ac_start_freq()
            ac_stop = req.get_ac_stop_freq()
            ac_ppd = req.get_ac_points_per_dec()
            ac_src = req.get_ac_source_name()
            ac_mf = req.get_ac_measure_freq()
            ac_ref = req.get_ac_ref_net()
            if ac_start is not None:
                entry["acStartFreq"] = ac_start
            if ac_stop is not None:
                entry["acStopFreq"] = ac_stop
            if ac_ppd is not None:
                entry["acPointsPerDec"] = ac_ppd
            if ac_src is not None:
                entry["acSourceName"] = ac_src
            if ac_mf is not None:
                entry["acMeasureFreq"] = ac_mf
            if ac_ref is not None:
                entry["acRefNet"] = ac_ref

        # Attach frequency-series for AC requirements
        if capture == "ac" and ac_data and ac_group_key_fn:
            key = ac_group_key_fn(req)
            ad = ac_data.get(key)
            if ad is not None:
                sig_key = f"v({net})" if not net.startswith(("v(", "i(")) else net
                ref_net = req.get_ac_ref_net()
                if ref_net:
                    gain = ad.gain_db_relative(sig_key, ref_net)
                    phase = ad.phase_deg_relative(sig_key, ref_net)
                else:
                    gain = ad.gain_db(sig_key)
                    phase = ad.phase_deg(sig_key)
                freq_list = list(ad.freq)
                freq_signals = {"gain_db": gain, "phase_deg": phase}
                freq_list, freq_signals = _lttb_downsample(
                    freq_list, freq_signals, _MAX_POINTS
                )
                entry["frequencySeries"] = {
                    "freq": freq_list,
                    "gain_db": freq_signals["gain_db"],
                    "phase_deg": freq_signals["phase_deg"],
                }

        # Attach multi-DUT time series
        if multi_dut_data:
            from faebryk.exporters.simulation.ngspice import TransientResult

            key = group_key_fn(req)
            md = multi_dut_data.get(key)
            if md is not None and isinstance(md, MultiDutResult):
                entry["multiDut"] = True
                duts_series = {}
                for dut_name, (dut_result, dut_aliases) in md.results.items():
                    dut_net = net
                    if dut_net.startswith("dut_"):
                        dut_net = f"{dut_name}_{dut_net[4:]}"
                    dn_norm = dut_net.replace(".", "_")
                    resolved_dn = dut_aliases.get(
                        dut_net, dut_aliases.get(dn_norm, dn_norm)
                    )
                    sk = (
                        f"v({resolved_dn})"
                        if not resolved_dn.startswith(("v(", "i("))
                        else resolved_dn
                    )
                    if isinstance(dut_result, TransientResult):
                        try:
                            sig = list(dut_result[sk])
                        except KeyError:
                            continue
                        t_list = list(dut_result.time)
                        t_list, s_map = _lttb_downsample(
                            t_list, {sk: sig}, _MAX_POINTS
                        )
                        duts_series[dut_name] = {
                            "time": t_list,
                            "signals": s_map,
                        }
                if duts_series:
                    entry["dutTimeSeries"] = duts_series

        reqs_json.append(entry)

    artifact: dict = {
        "requirements": reqs_json,
        "buildTime": datetime.now(timezone.utc).isoformat(),
    }

    if sim_stats:
        artifact["simStats"] = [
            {
                "name": s.name,
                "simType": s.sim_type,
                "elapsedS": round(s.elapsed_s, 2),
                "dataPoints": s.data_points,
            }
            for s in sorted(sim_stats, key=lambda x: x.elapsed_s, reverse=True)
        ]

    output_path = config.build.paths.output_base.with_suffix(".requirements.json")
    output_path.write_text(json.dumps(artifact))
    logger.info(f"Requirements artifact written to {output_path}")


@muster.register(
    "load-pcb",
    description="Loading PCB",
    dependencies=[post_instantiation_design_check],
)
def load_pcb(ctx: BuildStepContext) -> None:
    pcb = ctx.require_pcb()
    pcb.run_transformer()
    if config.build.keep_designators:
        load_kicad_pcb_designators(pcb.tg, attach=True)


@muster.register("picker", description="Picking parts", dependencies=[load_pcb])
def pick_parts(ctx: BuildStepContext) -> None:
    app = ctx.require_app()
    solver = ctx.require_solver()
    if config.build.keep_picked_parts:
        pcb = ctx.require_pcb()
        load_part_info_from_pcb(pcb.transformer.pcb, app.tg)
    try:
        pick_parts_recursively(app, solver, progress=None)
    except* PickError as ex:
        raise ExceptionGroup(
            "Failed to pick parts for some modules",
            [UserPickError(str(e)) for e in iter_leaf_exceptions(ex)],
        ) from ex
    save_part_info_to_pcb(app)


@muster.register(
    "run-simulations",
    description="Running SPICE simulations",
    dependencies=[pick_parts],
)
def run_simulations_step(ctx: BuildStepContext) -> None:
    """Phase 1: Run all SimulationTransient/Sweep/AC nodes and cache results."""
    try:
        from faebryk.exporters.simulation.simulation_runner import (
            run_simulations_scoped,
        )

        app = ctx.require_app()
        solver = ctx.require_solver()
        output_dir = config.build.paths.output_base.parent

        results_registry, sim_stats = run_simulations_scoped(
            app, solver, output_dir
        )

        # Cache on the context for verify-requirements
        ctx._simulation_results = results_registry
        ctx._simulation_stats = sim_stats

        if sim_stats:
            total_time = sum(s.elapsed_s for s in sim_stats)
            total_pts = sum(s.data_points for s in sim_stats)
            logger.info(
                f"Ran {len(sim_stats)} simulation(s) in {total_time:.1f}s "
                f"({total_pts:,} data points)"
            )
            for s in sorted(sim_stats, key=lambda x: x.elapsed_s, reverse=True):
                logger.info(
                    f"  {s.name}: {s.sim_type} {s.elapsed_s:.1f}s "
                    f"({s.data_points:,} pts)"
                )
    except Exception:
        logger.warning(
            "Simulation runner failed — skipping", exc_info=True
        )
        ctx._simulation_results = {}
        ctx._simulation_stats = []


def _downsample_trace(trace_json: dict, max_points: int = 2000) -> dict:
    """Downsample a Plotly trace dict to at most max_points for JSON size."""
    x = trace_json.get("x")
    y = trace_json.get("y")
    if not isinstance(x, (list, tuple)) or len(x) <= max_points:
        return trace_json
    step = max(1, len(x) // max_points)
    trace_json = dict(trace_json)
    trace_json["x"] = x[::step]
    trace_json["y"] = y[::step] if isinstance(y, (list, tuple)) else y
    return trace_json


def _extract_plot_specs(fig, meta: dict | None = None) -> list[dict] | None:
    """Extract Plotly figure specs (data + layout) for JSON embedding."""
    try:
        spec: dict = {
            "data": [_downsample_trace(t.to_plotly_json()) for t in fig.data],
            "layout": fig.layout.to_plotly_json(),
        }
        if meta:
            spec["meta"] = meta
        return [spec]
    except Exception:
        return None


def _plot_multi_dut_requirement(
    result,
    multi_result,
    path,
    req,
) -> list[dict] | None:
    """Generate a per-requirement plot for multi-DUT simulation results.

    Overlays one trace per DUT on the same chart.
    Returns extracted Plotly specs for JSON embedding.
    """
    from pathlib import Path

    from faebryk.exporters.simulation.ngspice import TransientResult
    from faebryk.exporters.simulation.requirement import (
        _auto_scale_time,
        _measure_tran,
        _slice_from,
    )
    from faebryk.exporters.simulation.simulation_runner import MultiDutResult

    if not isinstance(multi_result, MultiDutResult):
        return None

    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    measurement = req.get_measurement()
    raw_net = req.get_net()
    settling_tol = req.get_settling_tolerance()

    n_duts = len(multi_result.results)

    from faebryk.library.Plots import _viridis_hex

    dut_colors = _viridis_hex(n_duts)

    fig = go.Figure()
    t_unit = "s"

    for idx, (dut_name, (dut_result, dut_aliases)) in enumerate(
        multi_result.results.items()
    ):
        # Resolve net for this DUT
        dut_net = raw_net
        if dut_net.startswith("dut_"):
            dut_net = f"{dut_name}_{dut_net[4:]}"
        elif dut_net.startswith("dut."):
            dut_net = f"{dut_name}_{dut_net[4:].replace('.', '_')}"
        normalized = dut_net.replace(".", "_")
        resolved = dut_aliases.get(
            dut_net, dut_aliases.get(normalized, normalized)
        )

        sig_key = (
            f"v({resolved})"
            if not resolved.startswith(("v(", "i("))
            else resolved
        )
        color = dut_colors[idx % len(dut_colors)]

        # Build legend label with DUT params
        dut_params = multi_result.dut_params.get(dut_name, {})
        vin = next(
            (v for k, v in dut_params.items() if "power_in" in k and "voltage" in k),
            None,
        )
        vout = next(
            (v for k, v in dut_params.items() if "power_out" in k and "voltage" in k),
            None,
        )
        label = dut_name
        if vin is not None and vout is not None:
            label += f" ({vin:.0f}V→{vout:.1f}V)"

        if isinstance(dut_result, TransientResult):
            try:
                signal_data = dut_result[sig_key]
            except KeyError:
                continue
            time_data = list(dut_result.time)

            tran_start = req.get_tran_start()
            if tran_start and tran_start > 0:
                time_data, signal_data = _slice_from(
                    time_data, signal_data, tran_start
                )

            t_max = max(time_data) if time_data else 1.0
            scale, t_unit = _auto_scale_time(t_max)
            t_scaled = [t * scale for t in time_data]
            fig.add_trace(
                go.Scatter(
                    x=t_scaled,
                    y=list(signal_data),
                    mode="lines",
                    name=label,
                    line=dict(color=color, width=2),
                )
            )

    # Add pass band if applicable
    try:
        vout_pct = req.get_vout_tolerance_pct()
        if vout_pct is None:
            min_val = req.get_min_val()
            max_val = req.get_max_val()
            fig.add_hrect(
                y0=min_val, y1=max_val,
                fillcolor="green", opacity=0.08, line_width=0,
            )
            fig.add_hline(
                y=min_val, line=dict(color="red", dash="dot", width=1.5),
            )
            fig.add_hline(
                y=max_val, line=dict(color="red", dash="dot", width=1.5),
            )
    except Exception:
        pass

    # Title with PASS/FAIL badge appended
    status = "PASS" if result.passed else "FAIL"
    status_color = "#2ecc71" if result.passed else "#e74c3c"
    badge = f"  <span style='color:{status_color};font-size:14px'>[{status}]</span>"
    title_text = (
        f"<b>{req.get_name()}</b>{badge}"
        f"<br><span style='font-size:12px;color:gray'>"
        f"{n_duts} DUTs | {measurement.replace('_', ' ')}</span>"
    )

    fig.update_layout(
        title=dict(text=title_text, x=0.5, font=dict(size=16)),
        xaxis_title=f"Time ({t_unit})",
        yaxis_title=measurement.replace("_", " "),
        template="plotly_white",
        width=960,
        height=540,
        margin=dict(t=80, b=60, l=60, r=30),
        showlegend=True,
    )

    path = Path(path)
    fig.write_html(str(path), include_plotlyjs="cdn")
    return _extract_plot_specs(fig)


def _plot_sweep_requirement(
    result,
    sweep_dict: dict,
    net_aliases: dict,
    path,
) -> list[dict] | None:
    """Generate a per-requirement plot for sweep simulation results.

    Computes the measurement at each sweep point and plots measurement vs
    sweep parameter value.
    """
    from pathlib import Path
    from faebryk.exporters.simulation.ngspice import TransientResult
    from faebryk.exporters.simulation.requirement import _measure_tran

    try:
        import plotly.graph_objects as go
    except ImportError:
        return

    req = result.requirement
    measurement = req.get_measurement()
    raw_net = req.get_net()
    resolved_net = net_aliases.get(
        raw_net, net_aliases.get(raw_net.replace(".", "_"), raw_net)
    )
    settling_tol = req.get_settling_tolerance()

    # Resolve context nets
    resolved_ctx = []
    for ctx_net in req.get_context_nets():
        normalized = ctx_net.replace(".", "_")
        resolved = net_aliases.get(
            ctx_net, net_aliases.get(normalized, ctx_net)
        )
        resolved_ctx.append(resolved)

    # Compute measurement at each sweep point
    x_vals = []
    y_vals = []

    for pval in sorted(sweep_dict.keys()):
        point_result = sweep_dict[pval]
        if not isinstance(point_result, TransientResult):
            continue

        sig_key = (
            f"v({resolved_net})"
            if not resolved_net.startswith(("v(", "i("))
            else resolved_net
        )
        signal_data = point_result[sig_key]
        time_data = point_result.time

        val = _measure_tran(
            measurement,
            signal_data,
            time_data,
            settling_tolerance=settling_tol,
            sim_result=point_result,
            context_nets=resolved_ctx,
        )
        x_vals.append(pval)
        y_vals.append(val)

    if not x_vals:
        return

    min_val = req.get_min_val()
    max_val = req.get_max_val()
    colors = ["#2ecc71" if min_val <= y <= max_val else "#e74c3c" for y in y_vals]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals,
        mode="lines+markers",
        name="Measured",
        line=dict(color="#31688e", width=2.5),
        marker=dict(color=colors, size=10, line=dict(color="white", width=2)),
    ))

    # Pass band
    fig.add_hrect(
        y0=min_val, y1=max_val,
        fillcolor="green", opacity=0.08, line_width=0,
    )
    fig.add_hline(
        y=min_val, line=dict(color="red", dash="dot", width=1.5),
    )
    fig.add_hline(
        y=max_val, line=dict(color="red", dash="dot", width=1.5),
    )

    # Unit for Y axis
    if measurement == "efficiency":
        y_unit = "%"
    elif measurement in ("settling_time",):
        y_unit = "s"
    elif measurement in ("frequency",):
        y_unit = "Hz"
    elif measurement in ("duty_cycle",):
        y_unit = ""
    elif req.get_net().startswith("i("):
        y_unit = "A"
    else:
        y_unit = "V"

    n_pass = sum(1 for y in y_vals if min_val <= y <= max_val)
    status = "ALL PASS" if n_pass == len(y_vals) else f"{len(y_vals) - n_pass} FAIL"
    status_color = "#2ecc71" if n_pass == len(y_vals) else "#e74c3c"
    badge = f"  <span style='color:{status_color};font-size:14px'>[{status}]</span>"
    title_text = (
        f"<b>{req.get_name()}</b>{badge}"
        f"<br><span style='font-size:12px;color:gray'>"
        f"{n_pass}/{len(y_vals)} points | {measurement.replace('_', ' ')}</span>"
    )

    fig.update_layout(
        title=dict(text=title_text, x=0.5, font=dict(size=16)),
        xaxis_title="Sweep Parameter",
        yaxis_title=f"{measurement.replace('_', ' ')} ({y_unit})",
        template="plotly_white",
        width=960,
        height=540,
        margin=dict(t=80, b=60, l=60, r=30),
    )

    path = Path(path)
    fig.write_html(str(path), include_plotlyjs="cdn")
    return _extract_plot_specs(fig)


# ---------------------------------------------------------------------------
# Unified chart renderer for LineChart nodes (x/y/color declarative plots)
# ---------------------------------------------------------------------------

import re as _re

_MEASUREMENT_PATTERN = _re.compile(r"^(\w+)\((.+)\)$")

# SPICE probe prefixes — i(element) / v(node) are signal references, not measurements
_SPICE_PROBE_PREFIXES = {"i", "v"}

# User-friendly measurement aliases → internal measurement names
_MEASUREMENT_ALIASES: dict[str, str] = {
    "settle_time": "settling_time",
    "settling": "settling_time",
    "pp": "peak_to_peak",
    "p2p": "peak_to_peak",
    "avg": "average",
    "mean": "average",
    "final": "final_value",
}


def _parse_y_axis(y_str: str) -> tuple[str | None, str]:
    """Parse y-axis spec into (measurement_fn, net) or (None, net).

    Examples:
        "dut.power_out.hv"             → (None, "dut.power_out.hv")
        "settle_time(dut.power_out.hv)" → ("settling_time", "dut.power_out.hv")
    """
    m = _MEASUREMENT_PATTERN.match(y_str)
    if m:
        fn = m.group(1)
        # i(xxx) / v(xxx) are SPICE probes, not measurements
        if fn.lower() in _SPICE_PROBE_PREFIXES:
            return None, y_str
        fn = _MEASUREMENT_ALIASES.get(fn, fn)
        return fn, m.group(2)
    return None, y_str


def _resolve_dut_param(
    all_dut_params: dict[str, dict[str, float]],
    dut_name: str,
    param_path: str,
) -> float | None:
    """Resolve a parameter path like 'dut.switching_frequency' for a DUT."""
    param = param_path
    if param.startswith("dut."):
        param = param[4:]

    params = all_dut_params.get(dut_name, {})

    # Exact match
    if param in params:
        return params[param]

    # Dots → underscores
    normalized = param.replace(".", "_")
    if normalized in params:
        return params[normalized]

    # Partial match on last segment (e.g. "power_out.switching_frequency" → "switching_frequency")
    last = param.split(".")[-1]
    for k, v in params.items():
        if k == last or k.endswith("." + last) or k.endswith("_" + last):
            return v

    return None


def _resolve_dut_net_key(
    raw_net: str,
    dut_name: str,
    dut_aliases: dict[str, str],
) -> str:
    """Resolve a dut.xxx net reference to a SPICE signal key for one DUT."""
    from faebryk.library.Requirement import Requirement as ReqClass

    net = ReqClass._sanitize_net_name(raw_net)
    if net.startswith("dut_"):
        net = f"{dut_name}_{net[4:]}"
    normalized = net.replace(".", "_")
    resolved = dut_aliases.get(net, dut_aliases.get(normalized, normalized))
    if not resolved.startswith(("v(", "i(")):
        return f"v({resolved})"
    return resolved


def _render_chart(
    plot_node,
    sim_result,
    req,
    output_dir,
    net_aliases: dict,
) -> list[dict] | None:
    """Render a LineChart node attached to a requirement.

    Reads x/y/color from the plot node's is_plot trait and dispatches to
    the appropriate rendering path:
    - x="time" → time-domain trace(s)
    - x="dut.<param>" → parameter vs measurement scatter
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    from faebryk.exporters.simulation.ngspice import TransientResult
    from faebryk.exporters.simulation.requirement import (
        _measure_tran,
        _slice_from,
    )
    from faebryk.exporters.simulation.simulation_runner import MultiDutResult
    from faebryk.library.Plots import (
        _viridis_hex,
        auto_scale_time,
        format_eng,
        signal_unit,
    )

    # Read axis specs directly from the plot node's StringParameter fields.
    # The is_plot trait delegation may not resolve for ato-instantiated nodes,
    # so we access the fields directly.
    def _read_str(node, field_name: str) -> str | None:
        try:
            return getattr(node, field_name).get().try_extract_singleton()
        except Exception:
            return None

    title = _read_str(plot_node, "title") or req.get_name()
    x_spec = _read_str(plot_node, "x")
    y_spec = _read_str(plot_node, "y")
    y_secondary_spec = _read_str(plot_node, "y_secondary")
    color_spec = _read_str(plot_node, "color")
    plot_limits_raw = _read_str(plot_node, "plot_limits")
    show_limits = plot_limits_raw is None or plot_limits_raw.lower() not in (
        "false", "0", "no", "off",
    )

    # Detect and strip ac_coupled() signal transform
    ac_coupled = False
    if y_spec and "ac_coupled(" in y_spec:
        ac_match = _re.search(r"ac_coupled\(([^)]+)\)", y_spec)
        if ac_match:
            ac_coupled = True
            y_spec = y_spec.replace(
                f"ac_coupled({ac_match.group(1)})", ac_match.group(1)
            )

    def _ac_couple(data: list[float]) -> list[float]:
        """Remove DC component from signal data."""
        if not data:
            return data
        mean = sum(data) / len(data)
        return [s - mean for s in data]

    # Extract y_range bounds from NumericParameter (if constrained)
    y_range_min = None
    y_range_max = None
    try:
        y_range_param = plot_node.y_range.get()
        numbers = y_range_param.try_extract_superset()
        if numbers is not None:
            import math as _math
            lo = numbers.get_min_value()
            hi = numbers.get_max_value()
            if not _math.isinf(lo) and not _math.isinf(hi):
                y_range_min = lo
                y_range_max = hi
    except Exception:
        pass

    if not x_spec or not y_spec:
        return None

    measurement_fn, y_net = _parse_y_axis(y_spec)
    has_secondary = y_secondary_spec is not None
    if has_secondary:
        sec_measurement_fn, sec_y_net = _parse_y_axis(y_secondary_spec)

    name_slug = title.replace(" ", "_").replace(":", "").replace("/", "_")
    plot_path = Path(output_dir) / f"plot_{name_slug}.html"

    # ===================================================================
    # x = "time" — time-domain trace(s)
    # ===================================================================
    if x_spec == "time":
        # Use subplots with secondary_y if we have a secondary axis
        if has_secondary:
            from plotly.subplots import make_subplots

            fig = make_subplots(specs=[[{"secondary_y": True}]])
        else:
            fig = go.Figure()
        t_unit = "s"
        scale = 1.0
        settling_tol = req.get_settling_tolerance()

        # Infer primary y-axis unit
        primary_unit = signal_unit(y_net) if y_net.startswith("i(") else "V"
        secondary_unit = ""
        if has_secondary:
            secondary_unit = (
                signal_unit(sec_y_net)
                if sec_y_net.startswith("i(")
                else "V"
            )

        if isinstance(sim_result, MultiDutResult):
            n_duts = len(sim_result.results)
            dut_colors = _viridis_hex(n_duts)

            for idx, (dut_name, (dut_result, dut_aliases)) in enumerate(
                sim_result.results.items()
            ):
                if isinstance(dut_result, TransientResult):
                    # Single transient per DUT
                    sig_key = _resolve_dut_net_key(y_net, dut_name, dut_aliases)
                    try:
                        signal_data = dut_result[sig_key]
                    except KeyError:
                        continue
                    time_data = list(dut_result.time)

                    tran_start = req.get_tran_start()
                    if tran_start and tran_start > 0:
                        time_data, signal_data = _slice_from(
                            time_data, signal_data, tran_start
                        )
                    if ac_coupled:
                        signal_data = _ac_couple(signal_data)

                    t_max = max(time_data) if time_data else 1.0
                    scale, t_unit = auto_scale_time(t_max)
                    t_scaled = [t * scale for t in time_data]

                    # Build legend label — omit DUT name for single-DUT
                    dut_params = sim_result.dut_params.get(dut_name, {})
                    vin = next(
                        (
                            v
                            for k, v in dut_params.items()
                            if "power_in" in k and "voltage" in k
                        ),
                        None,
                    )
                    vout = next(
                        (
                            v
                            for k, v in dut_params.items()
                            if "power_out" in k and "voltage" in k
                        ),
                        None,
                    )
                    if n_duts == 1:
                        if vin is not None and vout is not None:
                            label = f"{vin:.0f}V\u2192{vout:.1f}V"
                        else:
                            label = y_net
                    else:
                        label = dut_name
                        if vin is not None and vout is not None:
                            label += f" ({vin:.0f}V\u2192{vout:.1f}V)"

                    trace_color = dut_colors[idx % len(dut_colors)]

                    fig.add_trace(
                        go.Scatter(
                            x=t_scaled,
                            y=list(signal_data),
                            mode="lines",
                            name=label,
                            line=dict(color=trace_color, width=2),
                        ),
                        **{"secondary_y": False} if has_secondary else {},
                    )

                    # Secondary y-axis trace (same color, dashed)
                    if has_secondary:
                        sec_key = _resolve_dut_net_key(
                            sec_y_net, dut_name, dut_aliases
                        )
                        try:
                            sec_data = dut_result[sec_key]
                        except KeyError:
                            continue
                        sec_time = list(dut_result.time)
                        if tran_start and tran_start > 0:
                            sec_time, sec_data = _slice_from(
                                sec_time, sec_data, tran_start
                            )
                        sec_t_scaled = [t * scale for t in sec_time]

                        fig.add_trace(
                            go.Scatter(
                                x=sec_t_scaled,
                                y=list(sec_data),
                                mode="lines",
                                name=f"{label} ({secondary_unit})",
                                line=dict(
                                    color=trace_color, width=2, dash="dash"
                                ),
                                showlegend=True,
                            ),
                            secondary_y=True,
                        )

                elif isinstance(dut_result, dict):
                    # Sweep: dict[float, TransientResult] — overlay all
                    # sweep points with Viridis colors per point.
                    sorted_points = sorted(dut_result.items())
                    sweep_colors = _viridis_hex(len(sorted_points))
                    param_unit = sim_result.sweep_param_unit or ""
                    tran_start = req.get_tran_start()
                    single_dut = n_duts == 1

                    for sp_idx, (pval, point_result) in enumerate(
                        sorted_points
                    ):
                        if not isinstance(point_result, TransientResult):
                            continue
                        sig_key = _resolve_dut_net_key(
                            y_net, dut_name, dut_aliases
                        )
                        try:
                            signal_data = point_result[sig_key]
                        except KeyError:
                            continue
                        time_data = list(point_result.time)

                        if tran_start and tran_start > 0:
                            time_data, signal_data = _slice_from(
                                time_data, signal_data, tran_start
                            )
                        if ac_coupled:
                            signal_data = _ac_couple(signal_data)

                        t_max = max(time_data) if time_data else 1.0
                        scale, t_unit = auto_scale_time(t_max)
                        t_scaled = [t * scale for t in time_data]

                        if single_dut:
                            label = format_eng(pval, param_unit)
                        else:
                            label = f"{dut_name} {format_eng(pval, param_unit)}"
                        fig.add_trace(
                            go.Scatter(
                                x=t_scaled,
                                y=list(signal_data),
                                mode="lines",
                                name=label,
                                line=dict(
                                    color=sweep_colors[sp_idx], width=2
                                ),
                            ),
                            **{"secondary_y": False}
                            if has_secondary
                            else {},
                        )

                        # Secondary y-axis trace per sweep point
                        if has_secondary:
                            sec_key = _resolve_dut_net_key(
                                sec_y_net, dut_name, dut_aliases
                            )
                            try:
                                sec_data = point_result[sec_key]
                            except KeyError:
                                continue
                            sec_time = list(point_result.time)
                            if tran_start and tran_start > 0:
                                sec_time, sec_data = _slice_from(
                                    sec_time, sec_data, tran_start
                                )
                            sec_t_scaled = [t * scale for t in sec_time]

                            fig.add_trace(
                                go.Scatter(
                                    x=sec_t_scaled,
                                    y=list(sec_data),
                                    mode="lines",
                                    name=f"{label} ({secondary_unit})",
                                    line=dict(
                                        color=sweep_colors[sp_idx],
                                        width=2,
                                        dash="dash",
                                    ),
                                    showlegend=False,
                                ),
                                secondary_y=True,
                            )
                else:
                    continue

        elif isinstance(sim_result, TransientResult):
            raw_net = req.get_net()
            normalized = raw_net.replace(".", "_")
            resolved = net_aliases.get(
                raw_net, net_aliases.get(normalized, raw_net)
            )
            sig_key = (
                f"v({resolved})"
                if not resolved.startswith(("v(", "i("))
                else resolved
            )
            try:
                signal_data = sim_result[sig_key]
            except KeyError:
                return None
            time_data = list(sim_result.time)

            tran_start = req.get_tran_start()
            if tran_start and tran_start > 0:
                time_data, signal_data = _slice_from(
                    time_data, signal_data, tran_start
                )
            if ac_coupled:
                signal_data = _ac_couple(signal_data)

            t_max = max(time_data) if time_data else 1.0
            scale, t_unit = auto_scale_time(t_max)
            t_scaled = [t * scale for t in time_data]

            trace_color = "#31688e"
            fig.add_trace(
                go.Scatter(
                    x=t_scaled,
                    y=list(signal_data),
                    mode="lines",
                    name=y_net,
                    line=dict(color=trace_color, width=2.5),
                ),
                **{"secondary_y": False} if has_secondary else {},
            )

            # Secondary y-axis trace for single-DUT
            if has_secondary:
                sec_resolved = sec_y_net.replace(".", "_")
                sec_resolved = net_aliases.get(
                    sec_y_net, net_aliases.get(sec_resolved, sec_resolved)
                )
                sec_sig_key = (
                    f"v({sec_resolved})"
                    if not sec_resolved.startswith(("v(", "i("))
                    else sec_resolved
                )
                try:
                    sec_data = sim_result[sec_sig_key]
                    sec_time = list(sim_result.time)
                    if tran_start and tran_start > 0:
                        sec_time, sec_data = _slice_from(
                            sec_time, sec_data, tran_start
                        )
                    sec_t_scaled = [t * scale for t in sec_time]
                    fig.add_trace(
                        go.Scatter(
                            x=sec_t_scaled,
                            y=list(sec_data),
                            mode="lines",
                            name=f"{sec_y_net} ({secondary_unit})",
                            line=dict(
                                color=trace_color, width=2, dash="dash"
                            ),
                        ),
                        secondary_y=True,
                    )
                except KeyError:
                    pass
        else:
            return None

        # Add pass band from requirement limits
        if show_limits:
            try:
                vout_pct = req.get_vout_tolerance_pct()
                if vout_pct is None:
                    min_val = req.get_min_val()
                    max_val = req.get_max_val()
                    measurement = req.get_measurement()
                    if measurement in ("settling_time",):
                        min_scaled = min_val * scale
                        max_scaled = max_val * scale
                        fig.add_vline(
                            x=min_scaled,
                            line=dict(color="red", dash="dot", width=2),
                        )
                        fig.add_vline(
                            x=max_scaled,
                            line=dict(color="red", dash="dot", width=2),
                        )
                    else:
                        fig.add_hrect(
                            y0=min_val,
                            y1=max_val,
                            fillcolor="green",
                            opacity=0.08,
                            line_width=0,
                        )
                        fig.add_hline(
                            y=min_val,
                            line=dict(color="red", dash="dot", width=1.5),
                        )
                        fig.add_hline(
                            y=max_val,
                            line=dict(color="red", dash="dot", width=1.5),
                        )
            except Exception:
                pass

        legend_kwargs = dict(
            font=dict(size=10),
            x=1.02,
            y=1,
            xanchor="left",
            yanchor="top",
        )
        if color_spec:
            legend_kwargs["title"] = dict(text=color_spec)

        layout_kwargs = dict(
            title=dict(
                text=f"<b>{title}</b>",
                x=0.5,
                font=dict(size=16),
            ),
            xaxis_title=f"Time ({t_unit})",
            width=900,
            height=500,
            template="plotly_white",
            showlegend=True,
            legend=legend_kwargs,
        )

        if has_secondary:
            fig.update_yaxes(
                title_text=f"{primary_unit}", secondary_y=False
            )
            fig.update_yaxes(
                title_text=f"{secondary_unit}", secondary_y=True
            )
        else:
            layout_kwargs["yaxis_title"] = f"Voltage ({primary_unit})"

        fig.update_layout(**layout_kwargs)

        # Auto y-range: 10% larger than limits or data envelope, whichever
        # is bigger.  Overridden by explicit y_range from the plot node.
        if show_limits and y_range_min is None and y_range_max is None:
            try:
                req_min = req.get_min_val()
                req_max = req.get_max_val()
                meas = req.get_measurement()
                # Only auto-range for non-time measurements (hrect limits)
                if meas not in ("settling_time",):
                    # Data envelope from primary-axis traces
                    all_y = []
                    for trace in fig.data:
                        yaxis = getattr(trace, "yaxis", None)
                        if yaxis in (None, "y", "y1"):
                            yd = trace.y
                            if yd is not None and len(yd) > 0:
                                all_y.extend(yd)
                    if all_y:
                        limit_span = req_max - req_min
                        limit_lo = req_min - 0.1 * limit_span
                        limit_hi = req_max + 0.1 * limit_span
                        data_span = max(all_y) - min(all_y)
                        data_span = max(data_span, 1e-9)
                        data_lo = min(all_y) - 0.1 * data_span
                        data_hi = max(all_y) + 0.1 * data_span
                        auto_lo = min(limit_lo, data_lo)
                        auto_hi = max(limit_hi, data_hi)
                        if has_secondary:
                            fig.update_yaxes(
                                range=[auto_lo, auto_hi], secondary_y=False
                            )
                        else:
                            fig.update_yaxes(range=[auto_lo, auto_hi])
            except Exception:
                pass

        # Apply explicit y-axis range if constrained (overrides auto-range)
        if y_range_min is not None and y_range_max is not None:
            if has_secondary:
                fig.update_yaxes(
                    range=[y_range_min, y_range_max], secondary_y=False
                )
            else:
                fig.update_yaxes(range=[y_range_min, y_range_max])

        fig.write_html(str(plot_path), include_plotlyjs="cdn")
        return _extract_plot_specs(fig)

    # ===================================================================
    # x = "dut.<param>" — parameter vs measurement scatter
    # ===================================================================
    if not isinstance(sim_result, MultiDutResult):
        return None

    if measurement_fn is None:
        return None

    settling_tol = req.get_settling_tolerance()
    fig = go.Figure()

    x_vals: list[float] = []
    y_vals: list[float] = []
    y_mins: list[float] = []  # for envelope plots
    y_maxs: list[float] = []  # for envelope plots
    labels: list[str] = []
    is_envelope = measurement_fn == "envelope"

    # Check if x_spec matches the sweep parameter name
    sweep_param = sim_result.sweep_param_name or ""

    def _collect_point(pval, signal_data, time_data, point_result, label):
        """Helper to collect a single sweep point."""
        tran_start = req.get_tran_start()
        if tran_start and tran_start > 0:
            time_data, signal_data = _slice_from(
                time_data, signal_data, tran_start
            )
        if ac_coupled:
            signal_data = _ac_couple(signal_data)
        if is_envelope:
            x_vals.append(pval)
            y_mins.append(min(signal_data))
            y_maxs.append(max(signal_data))
            labels.append(label)
        else:
            try:
                val = _measure_tran(
                    measurement_fn,
                    signal_data,
                    time_data,
                    settling_tolerance=settling_tol,
                    sim_result=point_result,
                )
            except Exception:
                return
            x_vals.append(pval)
            y_vals.append(val)
            labels.append(label)

    for dut_name, (dut_result, dut_aliases) in sim_result.results.items():
        # Resolve y-axis signal key
        sig_key = _resolve_dut_net_key(y_net, dut_name, dut_aliases)

        if isinstance(dut_result, dict) and sweep_param:
            # Sweep results: iterate sweep points as x-axis values
            for pval in sorted(dut_result.keys()):
                point_result = dut_result[pval]
                if not isinstance(point_result, TransientResult):
                    continue
                try:
                    signal_data = point_result[sig_key]
                except KeyError:
                    continue
                time_data = list(point_result.time)
                _collect_point(pval, signal_data, time_data, point_result, dut_name)

        elif isinstance(dut_result, TransientResult):
            # Single transient per DUT: x from dut_params
            param_val = _resolve_dut_param(
                sim_result.dut_params, dut_name, x_spec
            )
            if param_val is None:
                continue
            try:
                signal_data = dut_result[sig_key]
            except KeyError:
                continue
            time_data = list(dut_result.time)
            _collect_point(param_val, signal_data, time_data, dut_result, dut_name)

    if not x_vals:
        return None

    try:
        min_val = req.get_min_val()
        max_val = req.get_max_val()
    except Exception:
        min_val = None
        max_val = None

    if is_envelope:
        # Envelope plot: upper/lower smooth lines with shaded fill
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_maxs,
                mode="lines+markers",
                name="Max",
                line=dict(color="#e74c3c", width=2, shape="spline"),
                marker=dict(size=6),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_mins,
                mode="lines+markers",
                name="Min",
                line=dict(color="#3498db", width=2, shape="spline"),
                marker=dict(size=6),
                fill="tonexty",
                fillcolor="rgba(52, 152, 219, 0.15)",
            )
        )
    else:
        # Determine pass/fail colors
        if min_val is not None and max_val is not None:
            colors = [
                "#2ecc71" if min_val <= y <= max_val else "#e74c3c"
                for y in y_vals
            ]
        else:
            colors = ["#31688e"] * len(y_vals)

        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines+markers",
                name="Measured",
                line=dict(color="#31688e", width=2.5),
                marker=dict(
                    color=colors, size=10, line=dict(color="white", width=2)
                ),
                text=labels,
                textposition="top center",
            )
        )

    # Pass band
    if min_val is not None and max_val is not None and show_limits:
        fig.add_hrect(
            y0=min_val,
            y1=max_val,
            fillcolor="green",
            opacity=0.08,
            line_width=0,
        )
        fig.add_hline(
            y=min_val, line=dict(color="red", dash="dot", width=1.5)
        )
        fig.add_hline(
            y=max_val, line=dict(color="red", dash="dot", width=1.5)
        )

    # Infer axis units
    if measurement_fn in ("settling_time",):
        y_unit = "s"
    elif measurement_fn in ("frequency",):
        y_unit = "Hz"
    elif measurement_fn in ("overshoot",):
        y_unit = "%"
    elif measurement_fn in ("duty_cycle",):
        y_unit = ""
    elif y_net.startswith("i("):
        y_unit = "A"
    else:
        y_unit = "V"

    # X-axis label from parameter path
    x_label = x_spec
    if x_label.startswith("dut."):
        x_label = x_label[4:]
    x_label = x_label.replace(".", " ").replace("_", " ").title()
    x_unit = sim_result.sweep_param_unit or ""
    if x_unit:
        x_label = f"{x_label} ({x_unit})"
        # Format tick labels with engineering notation
        fig.update_xaxes(
            tickvals=x_vals,
            ticktext=[format_eng(v, x_unit) for v in x_vals],
        )

    y_label = f"{measurement_fn.replace('_', ' ')} ({y_unit})" if y_unit else measurement_fn.replace("_", " ")

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            x=0.5,
            font=dict(size=16),
        ),
        xaxis_title=x_label,
        yaxis_title=y_label,
        width=900,
        height=500,
        template="plotly_white",
        showlegend=True,
        legend=dict(
            font=dict(size=10),
            x=1.02,
            y=1,
            xanchor="left",
            yanchor="top",
        ),
    )

    fig.write_html(str(plot_path), include_plotlyjs="cdn")
    return _extract_plot_specs(fig)


def _render_bar_chart(
    plot_node,
    sim_result,
    req,
    output_dir,
    net_aliases: dict,
) -> list[dict] | None:
    """Render a BarChart node: measurement vs sweep parameter as bars.

    Reads x (sweep param name) and y (measurement(net)) from the plot node,
    iterates sweep points in the sim result, computes the measurement at
    each point, and renders as a Plotly bar chart with pass/fail coloring.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    from faebryk.exporters.simulation.ngspice import TransientResult
    from faebryk.exporters.simulation.requirement import (
        _measure_tran,
        _slice_from,
    )
    from faebryk.exporters.simulation.simulation_runner import MultiDutResult
    from faebryk.library.Plots import format_eng

    def _read_str(node, field_name: str) -> str | None:
        try:
            return getattr(node, field_name).get().try_extract_singleton()
        except Exception:
            return None

    title = _read_str(plot_node, "title") or req.get_name()
    x_spec = _read_str(plot_node, "x")
    y_spec = _read_str(plot_node, "y")
    plot_limits_raw = _read_str(plot_node, "plot_limits")
    show_limits = plot_limits_raw is None or plot_limits_raw.lower() not in (
        "false", "0", "no", "off",
    )

    if not x_spec or not y_spec:
        return None

    measurement_fn, y_net = _parse_y_axis(y_spec)
    if measurement_fn is None:
        return None

    name_slug = title.replace(" ", "_").replace(":", "").replace("/", "_")
    plot_path = Path(output_dir) / f"plot_{name_slug}.html"
    settling_tol = req.get_settling_tolerance()
    tran_start = req.get_tran_start()

    try:
        min_val = req.get_min_val()
        max_val = req.get_max_val()
    except Exception:
        min_val = None
        max_val = None

    x_vals: list[float] = []
    y_vals: list[float] = []
    bar_labels: list[str] = []

    # Infer param unit from MultiDutResult or use x_spec as label
    param_unit = ""
    if isinstance(sim_result, MultiDutResult):
        param_unit = sim_result.sweep_param_unit or ""

    if isinstance(sim_result, MultiDutResult):
        for dut_name, (dut_result, dut_aliases) in sim_result.results.items():
            if not isinstance(dut_result, dict):
                continue
            sig_key = _resolve_dut_net_key(y_net, dut_name, dut_aliases)

            for pval in sorted(dut_result.keys()):
                point_result = dut_result[pval]
                if not isinstance(point_result, TransientResult):
                    continue
                try:
                    signal_data = point_result[sig_key]
                except KeyError:
                    continue
                time_data = list(point_result.time)
                if tran_start and tran_start > 0:
                    time_data, signal_data = _slice_from(
                        time_data, signal_data, tran_start
                    )
                try:
                    val = _measure_tran(
                        measurement_fn,
                        signal_data,
                        time_data,
                        settling_tolerance=settling_tol,
                        sim_result=point_result,
                    )
                except Exception:
                    continue
                x_vals.append(pval)
                y_vals.append(val)
                bar_labels.append(format_eng(pval, param_unit))

    elif isinstance(sim_result, dict):
        # Single-DUT sweep: dict[float, TransientResult]
        raw_net = req.get_net()
        normalized = raw_net.replace(".", "_")
        resolved = net_aliases.get(
            raw_net, net_aliases.get(normalized, raw_net)
        )
        sig_key = (
            f"v({resolved})"
            if not resolved.startswith(("v(", "i("))
            else resolved
        )
        for pval in sorted(sim_result.keys()):
            point_result = sim_result[pval]
            if not isinstance(point_result, TransientResult):
                continue
            try:
                signal_data = point_result[sig_key]
            except KeyError:
                continue
            time_data = list(point_result.time)
            if tran_start and tran_start > 0:
                time_data, signal_data = _slice_from(
                    time_data, signal_data, tran_start
                )
            try:
                val = _measure_tran(
                    measurement_fn,
                    signal_data,
                    time_data,
                    settling_tolerance=settling_tol,
                    sim_result=point_result,
                )
            except Exception:
                continue
            x_vals.append(pval)
            y_vals.append(val)
            bar_labels.append(format_eng(pval, param_unit))
    else:
        return None

    if not x_vals:
        return None

    # Color bars by pass/fail (only when limits are shown)
    if show_limits and min_val is not None and max_val is not None:
        colors = [
            "#2ecc71" if min_val <= y <= max_val else "#e74c3c"
            for y in y_vals
        ]
    else:
        colors = ["#31688e"] * len(y_vals)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=bar_labels,
            y=y_vals,
            marker_color=colors,
            text=[f"{v:.4g}" for v in y_vals],
            textposition="outside",
        )
    )

    # Pass band lines (only when limits are enabled)
    if show_limits and min_val is not None and max_val is not None:
        fig.add_hrect(
            y0=min_val,
            y1=max_val,
            fillcolor="green",
            opacity=0.08,
            line_width=0,
        )
        fig.add_hline(
            y=min_val, line=dict(color="red", dash="dot", width=1.5)
        )
        fig.add_hline(
            y=max_val, line=dict(color="red", dash="dot", width=1.5)
        )

    # Infer y-axis unit
    if measurement_fn in ("settling_time",):
        y_unit = "s"
    elif measurement_fn in ("frequency",):
        y_unit = "Hz"
    elif measurement_fn in ("overshoot",):
        y_unit = "%"
    elif measurement_fn in ("duty_cycle",):
        y_unit = ""
    elif y_net.startswith("i("):
        y_unit = "A"
    else:
        y_unit = "V"

    y_label = measurement_fn.replace("_", " ")
    if y_unit:
        y_label = f"{y_label} ({y_unit})"

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            x=0.5,
            font=dict(size=16),
        ),
        xaxis_title=x_spec,
        yaxis_title=y_label,
        width=900,
        height=500,
        template="plotly_white",
        margin=dict(t=60, b=60),
    )

    # Auto y-range: leave ~15% headroom above bars for outside text labels,
    # and 10% below for symmetry / limit lines.
    if y_vals:
        data_min = min(y_vals)
        data_max = max(y_vals)
        if show_limits and min_val is not None and max_val is not None:
            envelope_lo = min(data_min, min_val)
            envelope_hi = max(data_max, max_val)
        else:
            envelope_lo = data_min
            envelope_hi = data_max
        span = envelope_hi - envelope_lo if envelope_hi != envelope_lo else abs(envelope_hi) * 0.2 or 1.0
        auto_lo = envelope_lo - 0.10 * span
        auto_hi = envelope_hi + 0.20 * span  # extra headroom for text labels
        fig.update_yaxes(range=[auto_lo, auto_hi])

    fig.write_html(str(plot_path), include_plotlyjs="cdn")
    return _extract_plot_specs(fig)


def _render_plots_for_requirement(
    req,
    sim_results: dict,
    default_sim_result,
    default_net_aliases: dict,
    output_dir,
    plot_nodes: list | None = None,
) -> list[dict] | None:
    """Render all chart plots (LineChart or BarChart) for a Requirement node.

    If *plot_nodes* is provided (discovered externally via requirement field),
    use those.  Otherwise fall back to ``req.get_plots()`` (direct children).

    Each plot may carry its own ``simulation`` field; if set and found in
    *sim_results*, that simulation's result/aliases are used instead of the
    requirement's default.

    Returns aggregated Plotly specs from all charts, or None if no plots.
    """
    from faebryk.library.Plots import BarChart

    def _read_str(node, field_name: str) -> str | None:
        try:
            return getattr(node, field_name).get().try_extract_singleton()
        except Exception:
            return None

    plots = plot_nodes if plot_nodes is not None else req.get_plots()
    if not plots:
        return None

    all_specs: list[dict] = []
    for plot_node in plots:
        try:
            # Resolve per-plot simulation override
            plot_sim_name = _read_str(plot_node, "simulation")
            if plot_sim_name and plot_sim_name in sim_results:
                use_result, use_aliases = sim_results[plot_sim_name]
            else:
                use_result, use_aliases = default_sim_result, default_net_aliases

            # Collect plot metadata for frontend editing
            plot_meta: dict = {}
            pn_parent = plot_node.get_parent()
            if pn_parent is not None:
                plot_meta["varName"] = pn_parent[1]
            for fld in ("title", "x", "y", "y_secondary", "color",
                        "simulation", "plot_limits"):
                val = _read_str(plot_node, fld)
                if val is not None:
                    plot_meta[fld] = val

            if isinstance(plot_node, BarChart):
                specs = _render_bar_chart(
                    plot_node, use_result, req, output_dir, use_aliases
                )
            else:
                specs = _render_chart(
                    plot_node, use_result, req, output_dir, use_aliases
                )
            if specs:
                for s in specs:
                    if plot_meta:
                        s.setdefault("meta", {}).update(plot_meta)
                all_specs.extend(specs)
        except Exception:
            logger.warning(
                f"Failed to render plot '{plot_node}' for "
                f"'{req.get_name()}'",
                exc_info=True,
            )

    return all_specs if all_specs else None


@muster.register(
    "verify-requirements",
    description="Verifying simulation requirements",
    dependencies=[run_simulations_step],
    produces_artifact=True,
)
def verify_requirements_step(ctx: BuildStepContext) -> None:
    """Phase 2: Verify requirements against cached simulation results."""
    try:
        from faebryk.exporters.simulation.requirement import (
            RequirementResult,
            _measure_ac,
            _measure_tran,
            _slice_from,
            plot_requirement,
        )
        from faebryk.exporters.simulation.ngspice import (
            ACResult,
            TransientResult,
        )
        from faebryk.exporters.simulation.simulation_runner import MultiDutResult

        app = ctx.require_app()
        output_dir = config.build.paths.output_base.parent

        # Get cached simulation results from Phase 1
        sim_results = getattr(ctx, "_simulation_results", {})

        # Find all Requirement nodes
        reqs = app.get_children(direct_only=False, types=F.Requirement)
        if not reqs:
            return

        # Build a lookup: plot attr name → plot node (for resolving
        # requirement.required_plot / supplementary_plot references).
        plot_by_attr: dict[str, object] = {}
        try:
            all_plot_nodes = app.get_children(
                direct_only=False,
                types=(F.Plots.LineChart, F.Plots.BarChart),
            )
            for pn in all_plot_nodes:
                pn_parent = pn.get_parent()
                if pn_parent is not None:
                    plot_by_attr[pn_parent[1]] = pn
        except Exception:
            pass

        results: list[RequirementResult] = []

        for req in reqs:
            try:
                sim_name = req.get_simulation()
                if sim_name is None:
                    continue

                if sim_name not in sim_results:
                    logger.warning(
                        f"Requirement '{req.get_name()}' references simulation "
                        f"'{sim_name}' which was not found in cached results"
                    )
                    continue

                sim_result, net_aliases = sim_results[sim_name]
                measurement = req.get_measurement()
                raw_net = req.get_net()
                settling_tol = req.get_settling_tolerance()

                # ----- Multi-DUT handling -----
                if isinstance(sim_result, MultiDutResult):
                    raw_addr = req.net.get().try_extract_singleton() or ""
                    actuals_per_dut: dict[str, float] = {}

                    for dut_name, (dut_result, dut_aliases) in (
                        sim_result.results.items()
                    ):
                        # Resolve dut.xxx → dut_name_xxx for net lookup
                        dut_net = raw_net
                        if dut_net.startswith("dut_"):
                            dut_net = f"{dut_name}_{dut_net[4:]}"
                        elif dut_net.startswith("dut."):
                            dut_net = f"{dut_name}_{dut_net[4:].replace('.', '_')}"
                        normalized_dut_net = dut_net.replace(".", "_")
                        resolved_dut_net = dut_aliases.get(
                            dut_net,
                            dut_aliases.get(
                                normalized_dut_net, normalized_dut_net
                            ),
                        )

                        # Resolve context nets for this DUT
                        dut_ctx = []
                        for ctx_net in req.get_context_nets():
                            cn = ctx_net
                            if cn.startswith("dut_"):
                                cn = f"{dut_name}_{cn[4:]}"
                            elif cn.startswith("dut."):
                                cn = f"{dut_name}_{cn[4:].replace('.', '_')}"
                            cn_norm = cn.replace(".", "_")
                            dut_ctx.append(
                                dut_aliases.get(
                                    cn, dut_aliases.get(cn_norm, cn_norm)
                                )
                            )

                        sig_key = (
                            f"v({resolved_dut_net})"
                            if not resolved_dut_net.startswith(("v(", "i("))
                            else resolved_dut_net
                        )

                        try:
                            if isinstance(dut_result, TransientResult):
                                signal_data = dut_result[sig_key]
                                time_data = dut_result.time
                                tran_start = req.get_tran_start()
                                if tran_start and tran_start > 0:
                                    time_data, signal_data = _slice_from(
                                        time_data, signal_data, tran_start
                                    )
                                val = _measure_tran(
                                    measurement,
                                    signal_data,
                                    time_data,
                                    settling_tolerance=settling_tol,
                                    sim_result=dut_result,
                                    context_nets=dut_ctx,
                                    min_val=req.get_min_val() if measurement == "envelope" else None,
                                    max_val=req.get_max_val() if measurement == "envelope" else None,
                                )
                                actuals_per_dut[dut_name] = val
                            elif isinstance(dut_result, dict):
                                # Sweep result per DUT: dict[float, TransientResult]
                                sweep_actuals = []
                                for pval, point_result in dut_result.items():
                                    if not isinstance(point_result, TransientResult):
                                        continue
                                    try:
                                        sd = point_result[sig_key]
                                    except KeyError:
                                        continue
                                    td = point_result.time
                                    tran_start = req.get_tran_start()
                                    if tran_start and tran_start > 0:
                                        td, sd = _slice_from(td, sd, tran_start)
                                    try:
                                        v = _measure_tran(
                                            measurement, sd, td,
                                            settling_tolerance=settling_tol,
                                            sim_result=point_result,
                                            context_nets=dut_ctx,
                                            min_val=req.get_min_val() if measurement == "envelope" else None,
                                            max_val=req.get_max_val() if measurement == "envelope" else None,
                                        )
                                    except Exception:
                                        continue
                                    sweep_actuals.append(v)
                                if sweep_actuals:
                                    min_v = req.get_min_val()
                                    max_v = req.get_max_val()
                                    mid = (min_v + max_v) / 2
                                    actuals_per_dut[dut_name] = max(
                                        sweep_actuals,
                                        key=lambda v: abs(v - mid),
                                    )
                        except Exception:
                            logger.warning(
                                f"  Multi-DUT '{dut_name}' measurement failed "
                                f"for req '{req.get_name()}'",
                                exc_info=True,
                            )

                    if not actuals_per_dut:
                        actual = float("nan")
                        passed = False
                    else:
                        # Determine bounds and pass/fail
                        vout_pct = req.get_vout_tolerance_pct()
                        if vout_pct is not None:
                            # Per-DUT bounds based on VOUT
                            all_passed = True
                            worst_actual = None
                            worst_dist = -1.0
                            for dn, act in actuals_per_dut.items():
                                dp = sim_result.dut_params.get(dn, {})
                                vout = next(
                                    (
                                        v
                                        for k, v in dp.items()
                                        if "power_out" in k
                                        and "voltage" in k
                                    ),
                                    None,
                                )
                                if vout is None:
                                    all_passed = False
                                    continue
                                mn = vout * (1 - vout_pct / 100)
                                mx = vout * (1 + vout_pct / 100)
                                dut_pass = mn <= act <= mx
                                all_passed &= dut_pass
                                dist = abs(act - (mn + mx) / 2)
                                if dist > worst_dist:
                                    worst_dist = dist
                                    worst_actual = act
                            actual = (
                                worst_actual
                                if worst_actual is not None
                                else float("nan")
                            )
                            passed = all_passed
                        else:
                            # Shared bounds — worst case
                            min_v = req.get_min_val()
                            max_v = req.get_max_val()
                            mid = (min_v + max_v) / 2
                            actual = max(
                                actuals_per_dut.values(),
                                key=lambda v: abs(v - mid),
                            )
                            import math

                            passed = (
                                not math.isnan(actual)
                                and min_v <= actual <= max_v
                            )

                    r = RequirementResult(
                        requirement=req,
                        actual=actual,
                        passed=passed,
                        display_net=raw_addr,
                        resolved_net=raw_net,
                        resolved_diff_ref=None,
                        resolved_ctx_nets=req.get_context_nets(),
                    )
                    results.append(r)

                    # Generate plots: try explicit LineChart nodes first
                    plot_names = req.get_all_plot_names()
                    req_plot_nodes = [
                        plot_by_attr[n] for n in plot_names
                        if n in plot_by_attr
                    ]
                    explicit_specs = _render_plots_for_requirement(
                        req, sim_results, sim_result, net_aliases,
                        output_dir,
                        plot_nodes=req_plot_nodes or None,
                    )
                    if explicit_specs:
                        r.plot_specs = explicit_specs
                    else:
                        # Fall back to auto-generated multi-DUT plot
                        name_slug = (
                            req.get_name()
                            .replace(" ", "_")
                            .replace(":", "")
                        )
                        plot_path = output_dir / f"req_{name_slug}.html"
                        r.plot_specs = _plot_multi_dut_requirement(
                            r, sim_result, plot_path, req
                        )
                    continue

                # ----- Single-DUT handling (original path) -----
                # Resolve net alias (normalize dots→underscores for lookup)
                normalized_net = raw_net.replace(".", "_")
                resolved_net = net_aliases.get(
                    raw_net, net_aliases.get(normalized_net, raw_net)
                )
                raw_addr = req.net.get().try_extract_singleton() or ""

                # Resolve context nets (normalize dots→underscores for alias lookup)
                resolved_ctx = []
                for ctx_net in req.get_context_nets():
                    # Try exact match first, then normalized (dot→underscore)
                    normalized = ctx_net.replace(".", "_")
                    resolved = net_aliases.get(
                        ctx_net,
                        net_aliases.get(normalized, ctx_net),
                    )
                    resolved_ctx.append(resolved)

                # Resolve diff_ref_net
                raw_diff = req.get_diff_ref_net()
                resolved_diff = None
                if raw_diff:
                    resolved_diff = net_aliases.get(raw_diff, raw_diff)

                if isinstance(sim_result, TransientResult):
                    # Construct signal key
                    sig_key = (
                        f"v({resolved_net})"
                        if not resolved_net.startswith(("v(", "i("))
                        else resolved_net
                    )

                    # Handle differential measurement
                    if resolved_diff:
                        ref_key = (
                            f"v({resolved_diff})"
                            if not resolved_diff.startswith(("v(", "i("))
                            else resolved_diff
                        )
                        signal_data = [
                            a - b
                            for a, b in zip(sim_result[sig_key], sim_result[ref_key])
                        ]
                    else:
                        signal_data = sim_result[sig_key]

                    time_data = sim_result.time

                    # Apply tran_start filtering if requirement specifies it
                    tran_start = req.get_tran_start()
                    if tran_start and tran_start > 0:
                        time_data, signal_data = _slice_from(
                            time_data, signal_data, tran_start
                        )

                    actual = _measure_tran(
                        measurement,
                        signal_data,
                        time_data,
                        settling_tolerance=settling_tol,
                        sim_result=sim_result,
                        context_nets=resolved_ctx,
                        min_val=req.get_min_val() if measurement == "envelope" else None,
                        max_val=req.get_max_val() if measurement == "envelope" else None,
                    )
                elif isinstance(sim_result, ACResult):
                    ref_net = req.get_ac_ref_net()
                    measure_freq = req.get_ac_measure_freq()
                    actual = _measure_ac(
                        measurement, sim_result, resolved_net,
                        ref_net, measure_freq,
                    )
                elif isinstance(sim_result, dict):
                    # Sweep result: dict[float, TransientResult]
                    # Measure each point and take the worst case
                    actuals = []
                    for pval, point_result in sim_result.items():
                        if not isinstance(point_result, TransientResult):
                            continue
                        sig_key = (
                            f"v({resolved_net})"
                            if not resolved_net.startswith(("v(", "i("))
                            else resolved_net
                        )
                        try:
                            signal_data = point_result[sig_key]
                        except KeyError:
                            continue
                        time_data = point_result.time

                        # Apply tran_start filtering for sweeps too
                        tran_start = req.get_tran_start()
                        if tran_start and tran_start > 0:
                            time_data, signal_data = _slice_from(
                                time_data, signal_data, tran_start
                            )

                        try:
                            val = _measure_tran(
                                measurement,
                                signal_data,
                                time_data,
                                settling_tolerance=settling_tol,
                                sim_result=point_result,
                                context_nets=resolved_ctx,
                                min_val=req.get_min_val() if measurement == "envelope" else None,
                                max_val=req.get_max_val() if measurement == "envelope" else None,
                            )
                        except Exception:
                            continue
                        actuals.append(val)
                    if actuals:
                        # For sweep: use worst-case (furthest from bounds)
                        min_v = req.get_min_val()
                        max_v = req.get_max_val()
                        mid = (min_v + max_v) / 2
                        actual = max(actuals, key=lambda v: abs(v - mid))
                    else:
                        actual = float("nan")
                else:
                    logger.warning(
                        f"Unsupported result type for requirement "
                        f"'{req.get_name()}': {type(sim_result)}"
                    )
                    continue

                import math

                passed = (
                    not math.isnan(actual)
                    and req.get_min_val() <= actual <= req.get_max_val()
                )
                r = RequirementResult(
                    requirement=req,
                    actual=actual,
                    passed=passed,
                    display_net=raw_addr,
                    resolved_net=resolved_net,
                    resolved_diff_ref=resolved_diff,
                    resolved_ctx_nets=resolved_ctx,
                )
                results.append(r)

                # Generate plots: try explicit LineChart nodes first
                plot_names = req.get_all_plot_names()
                req_plot_nodes = [
                    plot_by_attr[n] for n in plot_names
                    if n in plot_by_attr
                ]
                explicit_specs = _render_plots_for_requirement(
                    req, sim_results, sim_result, net_aliases,
                    output_dir,
                    plot_nodes=req_plot_nodes or None,
                )
                if explicit_specs:
                    r.plot_specs = explicit_specs
                else:
                    # Fall back to auto-generated plots
                    name_slug = (
                        req.get_name()
                        .replace(" ", "_")
                        .replace(":", "")
                    )
                    plot_path = output_dir / f"req_{name_slug}.html"
                    if isinstance(sim_result, TransientResult):
                        r.plot_specs = plot_requirement(r, sim_result, plot_path)
                    elif isinstance(sim_result, ACResult):
                        r.plot_specs = plot_requirement(
                            r, None, plot_path, ac_data=sim_result
                        )
                    elif isinstance(sim_result, dict):
                        r.plot_specs = _plot_sweep_requirement(
                            r, sim_result, net_aliases, plot_path
                        )
            except Exception as e:
                logger.warning(
                    f"Error processing requirement "
                    f"'{req.get_name() if hasattr(req, 'get_name') else '?'}'"
                    f": {e}",
                    exc_info=True,
                )

        if not results:
            return

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        logger.info(f"Requirements: {passed}/{total} passed")
        if passed < total:
            for r in results:
                if not r.passed:
                    logger.warning(
                        f"FAIL: {r.requirement.get_name()} = {r.actual:.4g} "
                        f"[{r.requirement.get_min_val()}, "
                        f"{r.requirement.get_max_val()}]"
                    )

        # Build tran_data/ac_data maps keyed by simulation name for JSON export
        def _sim_name_key(req):
            return req.get_simulation()

        tran_data: dict = {}
        ac_data_map: dict = {}
        multi_dut_data: dict = {}
        for req in reqs:
            sim_name = req.get_simulation()
            if sim_name is None or sim_name not in sim_results:
                continue
            sim_result, _aliases = sim_results[sim_name]
            if isinstance(sim_result, MultiDutResult):
                multi_dut_data[sim_name] = sim_result
            elif isinstance(sim_result, TransientResult):
                tran_data[sim_name] = sim_result
            elif isinstance(sim_result, ACResult):
                ac_data_map[sim_name] = sim_result

        _write_requirements_json(
            results, tran_data, _sim_name_key,
            ac_data=ac_data_map, ac_group_key_fn=_sim_name_key,
            multi_dut_data=multi_dut_data,
            sim_stats=getattr(ctx, "_simulation_stats", []),
            source_file=str(config.build.entry_file_path.resolve()),
        )
    except Exception:
        logger.warning(
            "Simulation requirement verification failed — skipping", exc_info=True
        )


@muster.register(
    "prepare-nets", description="Preparing nets", dependencies=[pick_parts]
)
def prepare_nets(ctx: BuildStepContext) -> None:
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
def post_solve_checks(ctx: BuildStepContext) -> None:
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
def update_pcb(ctx: BuildStepContext) -> None:
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

    # Ensure proper board appearance (matte black soldermask, ENIG copper finish)
    # This will overwrite user settings in the KiCad PCB file!
    ensure_board_appearance(pcb.pcb_file.kicad_pcb)

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
def post_pcb_checks(ctx: BuildStepContext) -> None:
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
def build_design(ctx: BuildStepContext) -> None:
    pass


@muster.register(
    "bom",
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_bom(ctx: BuildStepContext) -> None:
    """Generate a BOM for the project in both CSV and JSON formats."""
    app = ctx.require_app()
    pickable_parts = [
        part
        for m in app.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.Pickable.has_part_picked,
        )
        for part in [m.get_trait(F.Pickable.has_part_picked)]
        if not part.is_removed()
    ]
    # Generate CSV BOM (for JLCPCB manufacturing)
    write_bom(pickable_parts, config.build.paths.output_base.with_suffix(".bom.csv"))
    # Generate JSON BOM (for VSCode extension BOM panel)
    write_json_bom(
        pickable_parts,
        config.build.paths.output_base.with_suffix(".bom.json"),
        build_id=ctx.build_id,
    )


@muster.register(
    name="glb",
    aliases=["3d-model"],
    tags={Tags.REQUIRES_KICAD},
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_glb(ctx: BuildStepContext) -> None:
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
    name="glb-only",
    aliases=["3d-model-only"],
    tags={Tags.REQUIRES_KICAD},
    dependencies=[],
    produces_artifact=True,
)
def generate_glb_only(ctx: BuildStepContext) -> None:
    """Generate GLB from existing layout without rebuilding. For fast 3D preview."""
    layout_path = config.build.paths.layout
    if not layout_path.exists():
        raise UserException(
            f"Layout file not found: {layout_path}\n\n"
            "Run a full build first to generate the layout."
        )
    with _githash_layout(layout_path) as tmp_layout:
        try:
            export_glb(
                tmp_layout,
                glb_file=config.build.paths.output_base.with_suffix(".pcba.glb"),
                project_dir=layout_path.parent,
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate 3D model: {e}") from e


@muster.register(
    name="step",
    tags={Tags.REQUIRES_KICAD},
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_step(ctx: BuildStepContext) -> None:
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
def generate_3d_models(ctx: BuildStepContext) -> None:
    """Generate PCBA 3D model as GLB and STEP."""
    pass


@muster.register(
    name="3d-image",
    tags={Tags.REQUIRES_KICAD},
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_3d_render(ctx: BuildStepContext) -> None:
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
def generate_2d_render(ctx: BuildStepContext) -> None:
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
    dependencies=[generate_glb, generate_step, post_pcb_checks],
    produces_artifact=True,
)
def generate_manufacturing_data(ctx: BuildStepContext) -> None:
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

        # Export PCB summary with board dimensions and stackup
        try:
            export_pcb_summary(
                tmp_layout,
                summary_file=config.build.paths.output_base.with_suffix(
                    ".pcb_summary.json"
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to generate PCB summary: {e}")

        # Copy kicad_pcb to build directory for manufacturing export
        import shutil

        kicad_pcb_dest = config.build.paths.output_base.with_suffix(".kicad_pcb")
        try:
            shutil.copy2(tmp_layout, kicad_pcb_dest)
            logger.info(f"Copied KiCad PCB to {kicad_pcb_dest}")
        except Exception as e:
            logger.warning(f"Failed to copy KiCad PCB: {e}")


@muster.register(
    "manifest",
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_manifest(ctx: BuildStepContext) -> None:
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
def generate_variable_report(ctx: BuildStepContext) -> None:
    """Generate a report of all the variable values in the design."""
    app = ctx.require_app()
    solver = ctx.require_solver()
    export_parameters_to_file(
        app,
        solver,
        config.build.paths.output_base.with_suffix(".variables.json"),
        build_id=ctx.build_id,
    )


@muster.register(
    "power-tree",
    dependencies=[build_design],
    produces_artifact=True,
)
def generate_power_tree(ctx: BuildStepContext) -> None:
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
def generate_datasheets(ctx: BuildStepContext) -> None:
    app = ctx.require_app()
    export_datasheets(
        app, config.build.paths.documentation / "datasheets", progress=None
    )


# @muster.register(
#     "i2c-tree",
#     dependencies=[build_design],
#     produces_artifact=True,
# )
# def generate_i2c_tree(
#     app: fabll.Node, solver: Solver, pcb: F.PCB
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
        verify_requirements_step,
    ],
    virtual=True,
)
def generate_default(ctx: BuildStepContext) -> None:
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
def generate_all(ctx: BuildStepContext) -> None:
    """Generate all targets."""
    pass


if __name__ == "__main__":
    # uv run python src/atopile/build_steps.py | dot -T png | imgcat
    print(muster.dependency_dag._to_graphviz().source)
