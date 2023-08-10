import logging
import webbrowser
import urllib.parse

import click
import uvicorn
from atopile.project.project import Project
from atopile.project.config import BuildConfig
from atopile.cli.common import ingest_config_hat

# configure logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


# configure UI
@click.command()
@ingest_config_hat
@click.option("--port", default=2860)  # ato0 -> 2860 on an old phone
@click.option("--browser/--no-browser", default=True)
@click.option("--debug/--no-debug", default=False)
def view(
    project: Project, build_config: BuildConfig, port: int, browser: bool, debug: bool
):
    """
    View the specified the root source file with the argument SOURCE.
    eg. `ato view path/to/source.ato:module.path`
    """
    # defer import because it's kinda expensive?
    import atopile.viewer.server as s

    s.project_handler.project = project
    s.project_handler.build_config = build_config
    if debug:
        # FIXME: fuck... talk about pasghetti code
        import atopile.parser.parser

        atopile.parser.parser.log.setLevel(logging.DEBUG)

    url = f"http://localhost:{port}/client.html?" + urllib.parse.urlencode(
        {"circuit": build_config.root_node}
    )

    # print out the URL to the console super obviously
    log.info("")
    log.info("=" * len(url))
    log.info("Browse to:")
    log.info(url)
    log.info("=" * len(url))
    log.info("")

    if browser:
        webbrowser.open(url)
    uvicorn.run(s.app, host="0.0.0.0", port=port)
