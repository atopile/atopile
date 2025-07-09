import logging
from pathlib import Path

from pydantic import BaseModel

from atopile import buildutil
from atopile.cli.logging_ import capture_logs, log_exceptions
from atopile.mcp.util import MCPTools

cli_tools = MCPTools()

logger = logging.getLogger(__name__)


class Result(BaseModel):
    success: bool
    project_dir: str


class ErrorResult(Result):
    error: str
    error_message: str


class BuildResult(Result):
    target: str
    logs: str


@cli_tools.register()
def build_project(
    absolute_project_dir: Path, target_name_from_yaml: str
) -> BuildResult:
    from atopile.build import init_app
    from atopile.config import config

    config.apply_options(
        entry=None,
        working_dir=absolute_project_dir,
        selected_builds=[target_name_from_yaml],
    )

    config.project.open_layout_on_build = False
    config.interactive = False

    success = True

    with config.select_build(target_name_from_yaml), capture_logs() as logs:
        logger.info("Building target '%s'", config.build.name)

        try:
            with log_exceptions(logs):
                app = init_app()
                buildutil.build(app)
        except Exception:
            success = False

    return BuildResult(
        success=success,
        project_dir=str(absolute_project_dir),
        target=target_name_from_yaml,
        logs=logs.getvalue(),
    )


class CreatePartResult(Result):
    manufacturer: str
    part_number: str
    description: str
    supplier_id: str
    stock: int
    path: str
    import_statement: str


class CreatePartError(ErrorResult):
    error: str
    error_message: str


@cli_tools.register()
def search_and_install_jlcpcb_part(
    absolute_project_dir: Path, lcsc_part_number: str
) -> CreatePartResult | CreatePartError:
    """
    Search for a part on JLCPCB and install it.
    """

    from atopile.cli.create import part
    from atopile.config import config

    try:
        apart, component = part(
            search_term=lcsc_part_number,
            accept_single=True,
            project_dir=absolute_project_dir,
        )
    except Exception as e:
        return CreatePartError(
            success=False,
            project_dir=str(absolute_project_dir),
            error=e.__class__.__name__,
            error_message=str(e),
        )

    return CreatePartResult(
        success=True,
        project_dir=str(absolute_project_dir),
        manufacturer=component.manufacturer_name,
        part_number=component.part_number,
        description=component.description,
        supplier_id=component.lcsc_display,
        stock=component.stock,
        path=str(apart.path),
        import_statement=apart.generate_import_statement(config.project.paths.src),
    )


class InstallPackageResult(Result):
    installed_packages: list[str]


class InstallPackageError(ErrorResult):
    pass


@cli_tools.register()
def install_package(
    absolute_project_dir: str,
    package_identifiers: list[str],
    allow_upgrade: bool = False,
) -> InstallPackageResult | InstallPackageError:
    """
    Install a package using the ato CLI.
    """

    from atopile.cli.install import add

    try:
        add(
            package=package_identifiers,
            path=Path(absolute_project_dir),
            upgrade=allow_upgrade,
        )
    except Exception as e:
        return InstallPackageError(
            success=False,
            project_dir=str(absolute_project_dir),
            error=e.__class__.__name__,
            error_message=str(e),
        )

    return InstallPackageResult(
        success=True,
        project_dir=str(absolute_project_dir),
        installed_packages=package_identifiers,
    )
