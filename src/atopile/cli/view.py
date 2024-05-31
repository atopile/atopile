# pylint: disable=logging-fstring-interpolation

"""
`ato view`
"""
import logging
import textwrap
from enum import Enum
from pathlib import Path

import click
import yaml
from quart import Quart, jsonify, send_from_directory
from quart_cors import cors
from quart_schema import QuartSchema, validate_request, validate_response
from watchfiles import awatch

import atopile.address
import atopile.config
import atopile.front_end
import atopile.instance_methods
import atopile.schematic_utils
import atopile.viewer_utils
from atopile import errors
from atopile.cli.common import project_options
from atopile.config import BuildContext, set_project_context
from atopile.viewer_core import Pose

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


app = Quart(__name__, static_folder="../viewer/dist", static_url_path="")
app = cors(app, allow_origin="*")
QuartSchema(app)


@app.route("/block-diagram-data")
async def send_viewer_data():
    build_ctx: BuildContext = app.config["build_ctx"]
    return jsonify(atopile.viewer_utils.get_vis_dict(build_ctx))


class DiagramType(str, Enum):
    """The type of diagram."""
    block = "block"
    schematic = "schematic"


@app.route("/<diagram_type>/<path:addr>/pose", methods=["POST"])
@validate_request(Pose)
@validate_response(Pose, 201)
async def save_pose(
    diagram_type: str | DiagramType,
    addr: str,
    data: Pose
) -> tuple[Pose, int]:
    """Save the pose of an element."""
    diagram_type = DiagramType(diagram_type)
    build_ctx: BuildContext = app.config["build_ctx"]

    # FIXME: rip this logic outta here
    # We save the pose information to one file per-project
    # FIXME: figure out how we should actually
    # interact with these config files
    lock_path = build_ctx.project_context.lock_file_path
    if lock_path.exists():
        with lock_path.open("r") as lock_file:
            lock_data = yaml.safe_load(lock_file) or {}
    else:
        lock_data = {}

    lock_data.setdefault("poses", {}).setdefault(diagram_type.name, {})[addr] = data.model_dump()

    with lock_path.open("w") as lock_file:
        yaml.safe_dump(lock_data, lock_file)

    return data, 200


@app.route("/schematic-data")
async def send_schematic_data():
    build_ctx: BuildContext = app.config["build_ctx"]
    return jsonify(atopile.schematic_utils.get_schematic_dict(build_ctx))


@app.route("/")
async def home():
    """Serve the home page."""
    return await send_from_directory(app.static_folder, "index.html")


def _ato_file_filter(_, path: str):
    """Filter for files that are not ato files."""
    return path.endswith(".ato")


async def monitor_changes(src_dir: Path):
    """Background task to monitor the project for changes."""
    log.info(f"Monitoring {src_dir} for changes")

    async for changes in awatch(src_dir, watch_filter=_ato_file_filter, recursive=True):
        for change, file in changes:
            log.log(logging.NOTSET, "Change detected in %s: %s", file, change.name)
            atopile.front_end.reset_caches(file)


@app.before_serving
async def startup():
    """Set up the viewer."""
    log.info("Setting up the viewer")
    build_ctx: BuildContext = app.config["build_ctx"]

    # Monitor the project for changes to reset caches
    app.add_background_task(
        monitor_changes,
        build_ctx.project_context.project_path
    )

    # Pre-build the entry point
    atopile.instance_methods.get_instance(build_ctx.entry)


@click.command()
@project_options
def view(build_ctxs: list[BuildContext]):
    """
    View a block diagram or schematic of your project.
    """
    log.info("Spinning up the viewer")

    if len(build_ctxs) != 1:
        log.info(textwrap.dedent("""
            You need to select what you want to view.
            - If you use the `--build` option, you will view the entry point of the build.
            - If you add an argument for the address, you'll view that.
        """))
        raise errors.AtoNotImplementedError("Multiple build configs not yet supported.")

    build_ctx = build_ctxs[0]
    app.config["build_ctx"] = build_ctx
    set_project_context(build_ctx.project_context)

    app.run(host="127.0.0.1", port=8080)
