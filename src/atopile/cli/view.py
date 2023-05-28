import logging
import webbrowser
from pathlib import Path

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
@click.option('--browser/--no-browser', default=True)
@click.option('--debug/--no-debug', default=False)
def view(project: Project, build_config: BuildConfig, browser: bool, debug: bool):
    # defer import because it's kinda expensive?
    import atopile.visualizer.server as s
    s.watcher.project = project
    s.watcher.build_config = build_config
    if debug:
        # FIXME: fuck... talk about pasghetti code
        import atopile.parser.parser
        atopile.parser.parser.log.setLevel(logging.DEBUG)
    s.watcher.rebuild_all()
    if browser:
        webbrowser.open("http://localhost/static/client.html")
    uvicorn.run(s.app, host="0.0.0.0", port=80)
