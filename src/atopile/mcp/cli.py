import logging
from pathlib import Path

from atopile.mcp.util import mcp_decorate

logger = logging.getLogger(__name__)


@mcp_decorate()
def build_project(absolute_project_dir: str, target_name_from_yaml: str) -> str:
    """
    Build an atopile project using the ato CLI.
    """

    from atopile.cli.build import build

    try:
        build(
            selected_builds=[target_name_from_yaml],
            entry=absolute_project_dir,
            open_layout=False,
        )
    except Exception as e:
        raise ValueError(f"Failed to build project: {e}")

    return f"Built project {absolute_project_dir} with target {target_name_from_yaml}"


@mcp_decorate()
def search_and_install_jlcpcb_part(lcsc_part_number: str) -> str:
    """
    Search for a part on JLCPCB and install it.
    """

    from atopile.cli.create import part

    # TODO capture log / stdout
    part(search_term=lcsc_part_number, accept_single=True)

    return "Done"


@mcp_decorate()
def install_package(
    package_identifiers: list[str],
    project_path: Path | None = None,
    allow_upgrade: bool = False,
) -> str:
    """
    Install a package using the ato CLI.
    """

    from atopile.cli.install import add

    logger.info(f"CWD: {Path.cwd()}, path: {project_path}")
    # TODO capture log / stdout
    add(package=package_identifiers, path=project_path, upgrade=allow_upgrade)

    return "Done"
