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


def _write_requirements_json(
    results, tran_data, group_key_fn, ac_data=None, ac_group_key_fn=None,
    multi_dut_data=None,
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

        entry: dict = {
            "id": req.get_name().replace(" ", "_").replace(":", ""),
            "name": req.get_name(),
            "net": net,
            "capture": capture,
            "measurement": measurement,
            "minVal": req.get_min_val(),
            "typical": req.get_typical(),
            "maxVal": req.get_max_val(),
            "actual": actual,
            "passed": r.passed,
            "unit": unit,
            "contextNets": context_nets,
        }

        if r.display_net:
            entry["displayNet"] = r.display_net

        justification = req.get_justification()
        if justification:
            entry["justification"] = justification

        settling_tol = req.get_settling_tolerance()
        if settling_tol is not None:
            entry["settlingTolerance"] = settling_tol

        # Attach transient config and time-series
        if capture == "transient":
            tran_start = req.get_tran_start() or 0
            tran_stop = req.get_tran_stop()
            entry["tranStart"] = tran_start
            if tran_stop is not None:
                entry["tranStop"] = tran_stop

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

    artifact = {
        "requirements": reqs_json,
        "buildTime": datetime.now(timezone.utc).isoformat(),
    }

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


def _plot_multi_dut_requirement(
    result,
    multi_result,
    path,
    req,
) -> None:
    """Generate a per-requirement plot for multi-DUT simulation results.

    Overlays one trace per DUT on the same chart.
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
        return

    try:
        import plotly.graph_objects as go
    except ImportError:
        return

    measurement = req.get_measurement()
    raw_net = req.get_net()
    settling_tol = req.get_settling_tolerance()

    DUT_COLORS = [
        "#89b4fa",  # blue
        "#a6e3a1",  # green
        "#cba6f7",  # purple
        "#f38ba8",  # red
        "#fab387",  # orange
        "#f9e2af",  # yellow
    ]

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
        color = DUT_COLORS[idx % len(DUT_COLORS)]

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

    # Status annotation
    n_duts = len(multi_result.results)
    status = "PASS" if result.passed else "FAIL"
    status_color = "#2ecc71" if result.passed else "#e74c3c"
    fig.add_annotation(
        x=0.02, y=0.98, xref="paper", yref="paper",
        text=f"<b>{status}</b> ({n_duts} DUTs)",
        showarrow=False,
        font=dict(color=status_color, size=12),
        xanchor="left", yanchor="top",
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor=status_color, borderwidth=1, borderpad=4,
    )

    fig.update_layout(
        title=dict(text=req.get_name(), font=dict(size=16)),
        xaxis_title=f"Time ({t_unit})",
        yaxis_title=measurement.replace("_", " "),
        template="plotly_white",
        margin=dict(t=60, b=60, l=60, r=30),
        showlegend=True,
    )

    path = Path(path)
    fig.write_html(str(path), include_plotlyjs="cdn")


def _plot_sweep_requirement(
    result,
    sweep_dict: dict,
    net_aliases: dict,
    path,
) -> None:
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
        line=dict(color="royalblue", width=2.5),
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
    else:
        y_unit = "V"

    n_pass = sum(1 for y in y_vals if min_val <= y <= max_val)
    status = "ALL PASS" if n_pass == len(y_vals) else f"{len(y_vals) - n_pass} FAIL"
    status_color = "#2ecc71" if n_pass == len(y_vals) else "#e74c3c"

    fig.add_annotation(
        x=0.02, y=0.98, xref="paper", yref="paper",
        text=f"<b>{status}</b> ({n_pass}/{len(y_vals)} points)",
        showarrow=False,
        font=dict(color=status_color, size=12),
        xanchor="left", yanchor="top",
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor=status_color, borderwidth=1, borderpad=4,
    )

    fig.update_layout(
        title=dict(text=req.get_name(), font=dict(size=16)),
        xaxis_title="Sweep Parameter",
        yaxis_title=f"{measurement.replace('_', ' ')} ({y_unit})",
        template="plotly_white",
        margin=dict(t=60, b=60, l=60, r=30),
    )

    path = Path(path)
    fig.write_html(str(path), include_plotlyjs="cdn")


def _render_overlay_charts(
    app,
    sim_results: dict,
    output_dir,
) -> None:
    """Discover and render SweepOverlayChart nodes defined in the design.

    For each chart node, resolves its simulation references, computes the
    measurement at each sweep point for each series, and calls the chart's
    render() method.
    """
    from pathlib import Path
    from faebryk.exporters.simulation.ngspice import TransientResult
    from faebryk.exporters.simulation.requirement import _measure_tran
    from faebryk.library.Plots import SweepOverlayChart, SweepPoint

    charts = app.get_children(direct_only=False, types=SweepOverlayChart)
    if not charts:
        return

    for chart in charts:
        sim_names = chart.get_simulations()
        labels = chart.get_series_labels()
        raw_net = chart.get_net()
        measurement = chart.get_measurement() or "average"
        raw_ctx_nets = chart.get_context_nets()
        min_v = chart.get_min_val()
        max_v = chart.get_max_val()

        if not sim_names or not raw_net:
            continue

        # Pad labels if fewer than simulations
        while len(labels) < len(sim_names):
            labels.append(sim_names[len(labels)])

        series_data: dict[str, list[SweepPoint]] = {}

        for sim_name, label in zip(sim_names, labels):
            # Find simulation in results registry
            matched_key = None
            for key in sim_results:
                if key == sim_name or key.endswith("." + sim_name):
                    matched_key = key
                    break
            if matched_key is None:
                logger.warning(
                    f"SweepOverlayChart: simulation '{sim_name}' not found"
                )
                continue

            sweep_dict, net_aliases = sim_results[matched_key]
            if not isinstance(sweep_dict, dict):
                continue

            # Resolve net (normalize dots→underscores for lookup)
            normalized_net = raw_net.replace(".", "_")
            resolved_net = net_aliases.get(
                raw_net,
                net_aliases.get(normalized_net, normalized_net),
            )

            # Resolve context nets
            resolved_ctx = []
            for ctx_net in raw_ctx_nets:
                normalized = ctx_net.replace(".", "_")
                resolved = net_aliases.get(
                    ctx_net, net_aliases.get(normalized, ctx_net)
                )
                resolved_ctx.append(resolved)

            points: list[SweepPoint] = []
            for pval in sorted(sweep_dict.keys()):
                point_result = sweep_dict[pval]
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

                val = _measure_tran(
                    measurement,
                    signal_data,
                    time_data,
                    sim_result=point_result,
                    context_nets=resolved_ctx,
                )

                passed = min_v <= val <= max_v
                points.append(SweepPoint(
                    param_value=pval, actual=val, passed=passed,
                ))

            if points:
                series_data[label] = points

        if not series_data:
            continue

        # Build output filename from chart title
        chart_title = chart.get_title() or "sweep_overlay"
        name_slug = (
            chart_title.replace(" ", "_").replace("/", "_").replace(":", "")
        )
        plot_path = Path(output_dir) / f"{name_slug}.html"
        chart.render(series_data, plot_path)
        logger.info(f"Overlay chart: {plot_path}")


def _render_startup_validation_charts(
    app,
    sim_results: dict,
    output_dir,
) -> None:
    """Discover and render StartupValidationChart nodes defined in the design.

    Each chart references multiple SimulationTransient sims (one per frequency).
    The chart's render() receives a dict mapping sim name -> TransientResult.
    """
    from pathlib import Path
    from faebryk.library.Plots import StartupValidationChart

    charts = app.get_children(direct_only=False, types=StartupValidationChart)
    if not charts:
        return

    for chart in charts:
        sim_names = chart.get_simulations()
        raw_net = chart.get_net()

        if not sim_names or not raw_net:
            continue

        # Resolve sim names -> TransientResult, resolve net key
        series_data: dict = {}
        resolved_net_key = None

        for sim_name in sim_names:
            matched_key = None
            for key in sim_results:
                if key == sim_name or key.endswith("." + sim_name):
                    matched_key = key
                    break
            if matched_key is None:
                logger.warning(
                    f"StartupValidationChart: simulation '{sim_name}' not found"
                )
                continue

            sim_result, net_aliases = sim_results[matched_key]

            if resolved_net_key is None:
                normalized_net = raw_net.replace(".", "_")
                resolved_net = net_aliases.get(
                    raw_net,
                    net_aliases.get(normalized_net, normalized_net),
                )
                resolved_net_key = (
                    f"v({resolved_net})"
                    if not resolved_net.startswith(("v(", "i("))
                    else resolved_net
                )

            series_data[sim_name] = sim_result

        if not series_data or resolved_net_key is None:
            continue

        chart_title = chart.get_title() or "startup_validation"
        name_slug = (
            chart_title.replace(" ", "_").replace("/", "_").replace(":", "")
        )
        plot_path = Path(output_dir) / f"{name_slug}.html"
        chart.render(series_data, resolved_net_key, plot_path)
        logger.info(f"Startup validation chart: {plot_path}")


def _render_efficiency_validation_charts(
    app,
    sim_results: dict,
    output_dir,
) -> None:
    """Discover and render EfficiencyValidationChart nodes defined in the design.

    For each chart node, resolves its simulation references (sweep sims),
    collects the dict[float, TransientResult] for each series, and calls
    the chart's render() method to produce a 3-panel efficiency dashboard.
    """
    from pathlib import Path
    from faebryk.library.Plots import EfficiencyValidationChart

    charts = app.get_children(direct_only=False, types=EfficiencyValidationChart)
    if not charts:
        return

    for chart in charts:
        sim_names = chart.get_simulations()
        labels = chart.get_series_labels()
        raw_net = chart.get_net()
        raw_ctx_nets = chart.get_context_nets()

        if not sim_names or not raw_net:
            continue

        while len(labels) < len(sim_names):
            labels.append(sim_names[len(labels)])

        series_data: dict[str, dict] = {}
        resolved_net_key = None
        resolved_ctx_keys: list[str] = []

        for sim_name, label in zip(sim_names, labels):
            matched_key = None
            for key in sim_results:
                if key == sim_name or key.endswith("." + sim_name):
                    matched_key = key
                    break
            if matched_key is None:
                logger.warning(
                    f"EfficiencyValidationChart: simulation '{sim_name}' not found"
                )
                continue

            sim_result, net_aliases = sim_results[matched_key]
            if not isinstance(sim_result, dict):
                logger.warning(
                    f"EfficiencyValidationChart: '{sim_name}' is not a sweep sim"
                )
                continue

            if resolved_net_key is None:
                normalized_net = raw_net.replace(".", "_")
                resolved_net = net_aliases.get(
                    raw_net,
                    net_aliases.get(normalized_net, normalized_net),
                )
                resolved_net_key = (
                    f"v({resolved_net})"
                    if not resolved_net.startswith(("v(", "i("))
                    else resolved_net
                )

                for ctx_net in raw_ctx_nets:
                    normalized = ctx_net.replace(".", "_")
                    resolved = net_aliases.get(
                        ctx_net, net_aliases.get(normalized, ctx_net)
                    )
                    ctx_key = (
                        f"v({resolved})"
                        if not resolved.startswith(("v(", "i("))
                        else resolved
                    )
                    resolved_ctx_keys.append(ctx_key)

            series_data[label] = sim_result

        if not series_data or resolved_net_key is None:
            continue

        chart_title = chart.get_title() or "efficiency_validation"
        name_slug = (
            chart_title.replace(" ", "_").replace("/", "_").replace(":", "")
        )
        plot_path = Path(output_dir) / f"{name_slug}.html"
        chart.render(
            series_data, resolved_net_key, plot_path,
            context_keys=resolved_ctx_keys or None,
        )
        logger.info(f"Efficiency validation chart: {plot_path}")


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
                with open("/tmp/plot_debug.log", "a") as _dbg:
                    _dbg.write(
                        f"Req '{req.get_name()}': sim='{sim_name}', "
                        f"result_type={type(sim_result).__name__}\n"
                    )
                if isinstance(sim_result, MultiDutResult):
                    with open("/tmp/plot_debug.log", "a") as _dbg:
                        _dbg.write("Entered MultiDutResult branch\n")
                        try:
                            lp = req.limit.get()
                            _dbg.write(f"  limit param: {lp!r}\n")
                            # Try raw operatable extraction
                            op = lp.is_parameter_operatable.get()
                            _dbg.write(f"  operatable: {op!r}\n")
                            # Try getting raw literal sets
                            from faebryk.library.Literals import Numbers
                            try:
                                ss = op.try_extract_superset(lit_type=Numbers)
                                _dbg.write(f"  superset Numbers: {ss!r}\n")
                                if ss:
                                    _dbg.write(f"    min={ss.get_min_value()}, max={ss.get_max_value()}\n")
                            except Exception as e3:
                                _dbg.write(f"  superset error: {e3}\n")
                            try:
                                from faebryk.library.Literals import Quantity
                                sq = op.try_extract_superset(lit_type=Quantity)
                                _dbg.write(f"  superset Quantity: {sq!r}\n")
                                if sq:
                                    _dbg.write(f"    min={sq.get_min_value()}, max={sq.get_max_value()}\n")
                            except Exception as e4:
                                _dbg.write(f"  superset Quantity error: {e4}\n")
                            # Check what children/edges the param has
                            children = lp.get_children(direct_only=True)
                            _dbg.write(f"  children: {[type(c).__name__ for c in children]}\n")
                        except Exception as e2:
                            import traceback
                            _dbg.write(f"  limit extraction error: {e2}\n{traceback.format_exc()}\n")
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

                    # Generate multi-DUT plot(s)
                    name_slug = (
                        req.get_name()
                        .replace(" ", "_")
                        .replace(":", "")
                    )

                    # Use attached plot nodes if available
                    plot_nodes = req.get_plots()
                    with open("/tmp/plot_debug.log", "a") as _dbg:
                        _dbg.write(
                            f"Plot nodes: {len(plot_nodes)} found, "
                            f"slug='{name_slug}', output_dir={output_dir}\n"
                        )
                        # Also check all LineChart children
                        all_lc = req.get_children(
                            direct_only=True, types=F.Plots.LineChart
                        )
                        _dbg.write(
                            f"All LineChart children: {len(all_lc)}\n"
                        )
                        for lc in all_lc:
                            _dbg.write(
                                f"  LC: title={lc.get_title()!r}, "
                                f"nets={lc.get_nets()!r}\n"
                            )
                    if plot_nodes:
                        for pi, plot_node in enumerate(plot_nodes):
                            suffix = f"_{pi}" if len(plot_nodes) > 1 else ""
                            p = output_dir / f"req_{name_slug}{suffix}.html"
                            plot_node.render_multi_dut(
                                sim_result, req, p
                            )
                    else:
                        plot_path = output_dir / f"req_{name_slug}.html"
                        _plot_multi_dut_requirement(
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

                # Generate plot
                name_slug = (
                    req.get_name()
                    .replace(" ", "_")
                    .replace(":", "")
                )
                plot_path = output_dir / f"req_{name_slug}.html"
                if isinstance(sim_result, TransientResult):
                    plot_requirement(r, sim_result, plot_path)
                elif isinstance(sim_result, ACResult):
                    plot_requirement(r, None, plot_path, ac_data=sim_result)
                elif isinstance(sim_result, dict):
                    _plot_sweep_requirement(
                        r, sim_result, net_aliases, plot_path
                    )
            except Exception as e:
                import traceback
                with open("/tmp/plot_debug.log", "a") as _dbg:
                    _dbg.write(
                        f"EXCEPTION processing req: {e}\n"
                        f"{traceback.format_exc()}\n"
                    )
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
        )

        # Render SweepOverlayChart nodes defined in the design
        _render_overlay_charts(app, sim_results, output_dir)

        # Render StartupValidationChart nodes defined in the design
        _render_startup_validation_charts(app, sim_results, output_dir)

        # Render EfficiencyValidationChart nodes defined in the design
        _render_efficiency_validation_charts(app, sim_results, output_dir)
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
