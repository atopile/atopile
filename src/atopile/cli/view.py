# pylint: disable=logging-fstring-interpolation

"""
`ato view`
"""
import logging
import textwrap
from pathlib import Path

import click
from quart import Quart, jsonify, send_from_directory
from quart_cors import cors
from watchfiles import awatch

import atopile.front_end
import atopile.instance_methods
import atopile.schematic_utils
import atopile.viewer_utils
from atopile import errors
from atopile.cli.common import project_options
from atopile.config import BuildContext, set_project_context

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


app = Quart(__name__, static_folder="../viewer/dist", static_url_path="")
app = cors(app, allow_origin="*")


@app.route("/data")
async def send_viewer_data():
    build_ctx: BuildContext = app.config["build_ctx"]
    return jsonify(atopile.viewer_utils.get_vis_dict(build_ctx.entry))


@app.route("/schematic-data")
async def send_schematic_data():
    build_ctx: BuildContext = app.config["build_ctx"]
    return jsonify(atopile.schematic_utils.get_schematic_dict(build_ctx.entry))


@app.route("/")
async def home():
    """Serve the home page."""
    return await send_from_directory(app.static_folder, "index.html")


async def monitor_changes(src_dir: Path):
    """Background task to monitor the project for changes."""
    log.info(f"Monitoring {src_dir} for changes")

    async for changes in awatch(src_dir, recursive=True):
        for change, file in changes:
            log.log(logging.NOTSET, "Change detected in %s: %s", file, change.name)
            atopile.front_end.reset_caches(file)


@app.before_serving
async def startup():
    """Set up the viewer."""
    log.info("Setting up the viewer")
    build_ctx: BuildContext = app.config["build_ctx"]

    # Monitor the project for changes to reset caches
    app.add_background_task(monitor_changes, build_ctx.project_context.src_path)

    # Pre-build the entry point
    atopile.instance_methods.get_instance(build_ctx.entry)


@click.command()
@project_options
def view(build_ctxs: list[BuildContext]):
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
