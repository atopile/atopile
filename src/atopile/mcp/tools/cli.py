import logging
from pathlib import Path

from atopile import buildutil
from atopile.dataclasses import (
    BuildResult,
    CreatePartError,
    CreatePartResult,
    ErrorResult,
    InstallPackageError,
    InstallPackageResult,
    PackageVerifyResult,
    Result,
)
from atopile.logging import BaseLogger
from atopile.mcp.util import MCPTools

cli_tools = MCPTools()

logger = logging.getLogger(__name__)


@cli_tools.register()
def build_project(
    absolute_project_dir: Path, target_name_from_yaml: str
) -> BuildResult:
    from atopile.config import config

    config.apply_options(
        entry=None,
        working_dir=absolute_project_dir,
        selected_builds=[target_name_from_yaml],
    )

    config.project.open_layout_on_build = False
    config.interactive = False

    success = True

    with config.select_build(target_name_from_yaml), BaseLogger.capture_logs() as logs:
        logger.info("Building target '%s'", config.build.name)

        try:
            with BaseLogger.log_exceptions(logs):
                buildutil.build()
        except Exception:
            success = False

    return BuildResult(
        success=success,
        project_dir=str(absolute_project_dir),
        target=target_name_from_yaml,
        logs=logs.getvalue(),
    )


# CreatePartResult and CreatePartError are imported from atopile.dataclasses


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


# InstallPackageResult and InstallPackageError are imported from atopile.dataclasses


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


@cli_tools.register()
def verify_package(absolute_project_dir: Path) -> PackageVerifyResult:
    """
    Check if a project satisfies requirements to be published as package.
    """
    from atopile.cli.package import verify_package as _verify_package
    from atopile.config import config

    config.apply_options(entry=str(absolute_project_dir))

    success = True
    with BaseLogger.capture_logs() as logs:
        logger.info("Verifying package at '%s'", absolute_project_dir)
        try:
            with BaseLogger.log_exceptions(logs):
                _verify_package(config)
        except Exception:
            success = False

    return PackageVerifyResult(
        success=success,
        project_dir=str(absolute_project_dir),
        logs=logs.getvalue(),
    )
