import logging
from pathlib import Path

from pydantic import BaseModel

from atopile import buildutil
from atopile.cli.logging_ import capture_logs
from atopile.mcp.util import MCPTools
from faebryk.libs.exceptions import log_user_errors

cli_tools = MCPTools()

logger = logging.getLogger(__name__)


class BuildResult(BaseModel):
    success: bool
    project: str
    target: str
    logs: str


@cli_tools.register()
def build_project(absolute_project_dir: str, target_name_from_yaml: str) -> BuildResult:
    from atopile.build import init_app
    from atopile.config import config

    config.apply_options(
        entry=absolute_project_dir,
        selected_builds=[target_name_from_yaml],
    )

    config.project.open_layout_on_build = False
    config.interactive = False

    with (
        config.select_build(target_name_from_yaml),
        capture_logs() as logs,
        log_user_errors(),
    ):
        logger.info("Building target '%s'", config.build.name)

        try:
            app = init_app()
            buildutil.build(app)
            success = True
        except Exception:
            success = False

        return BuildResult(
            success=success,
            project=absolute_project_dir,
            target=target_name_from_yaml,
            logs=logs.getvalue(),
        )


@cli_tools.register()
def search_and_install_jlcpcb_part(lcsc_part_number: str) -> str:
    """
    Search for a part on JLCPCB and install it.
    """

    from atopile.cli.create import part

    # TODO capture log / stdout
    part(search_term=lcsc_part_number, accept_single=True)

    return "Done"


@cli_tools.register()
def install_package(
    package_identifiers: list[str],
    project_path: Path | None = None,
    allow_upgrade: bool = False,
) -> str:
    """
    Install a package using the ato CLI.
    """

    from atopile.cli.install import add

    # TODO capture log / stdout
    add(package=package_identifiers, path=project_path, upgrade=allow_upgrade)

    return "Done"
