import os
from typing import TYPE_CHECKING, Annotated, Iterator

import typer
from semver import Version

from atopile.errors import UserBadParameterError, UserException, UserFileNotFoundError
from atopile.exceptions import accumulate
from atopile.logging import get_logger
from atopile.telemetry import capture

if TYPE_CHECKING:
    from atopile.config import Config

logger = get_logger(__name__)

package_app = typer.Typer(rich_markup_mode="rich")


FROM_GIT = "from-git"


def _yield_semver_tags(config: "Config") -> Iterator[Version]:
    from git import Repo

    repo = Repo(config.project.paths.root)
    for tag in repo.tags:
        if not tag.commit == repo.head.commit:
            continue

        try:
            yield Version.parse(tag.name.removeprefix("v"))
        except ValueError:
            continue


def _apply_version(specd_version: str, config: "Config") -> None:
    if specd_version == FROM_GIT:
        try:
            semver_tags = list(_yield_semver_tags(config))
        except Exception as e:
            raise UserException(
                "Could not determine version from git tags: %s" % e
            ) from e

        if len(semver_tags) == 0:
            raise UserBadParameterError("No semver tags found for the current commit")

        elif len(semver_tags) > 1:
            raise UserBadParameterError(
                "Multiple semver tags found for the current commit: %s."
                " No guessing which to use."
            )

        version = semver_tags[0]

    else:
        try:
            version = Version.parse(specd_version.removeprefix("v"))
        except ValueError as ex:
            raise UserBadParameterError(
                f"{specd_version} is not a valid semantic version"
            ) from ex

    if version.prerelease or version.build:
        raise UserBadParameterError(
            "Version must be a semantic version, without prerelease or build."
            f" Got {str(version)}"
        )

    assert config.project.package is not None
    config.project.package.version = str(version)


class _PackageValidators:
    @staticmethod
    def verify_manifest(config: "Config"):
        if config.project.package is None:
            raise UserException(
                "Project has no package configuration. "
                "Please add a `package` section to your `ato.yaml` file."
            )
        if not config.project.package.identifier:
            raise UserBadParameterError(
                "Project `identifier` is not set. Set via ATO_PACKAGE_IDENTIFIER "
                "envvar or in `ato.yaml`"
            )
        if not config.project.package.repository:
            raise UserBadParameterError(
                "Project `repository` is not set. Set via ATO_PACKAGE_REPOSITORY "
                "envvar or in `ato.yaml`"
            )

    @staticmethod
    def verify_pinned_dependencies(config: "Config", latest: bool = False):
        from atopile.config import RegistryDependencySpec
        from faebryk.libs.backend.packages.api import PackagesAPIClient

        if not config.project.dependencies:
            return

        api = PackagesAPIClient()

        registry_deps = [
            dep
            for dep in config.project.dependencies
            if isinstance(dep, RegistryDependencySpec)
        ]
        unpublishable_deps = [
            dep
            for dep in config.project.dependencies
            if not isinstance(dep, RegistryDependencySpec)
        ]

        for dep in registry_deps:
            if dep.release is None:
                raise UserBadParameterError(
                    f"Dependency {dep.identifier} is not pinned to a release."
                )
            latest_registry_version = api.get_package(dep.identifier).info.version
            if latest and dep.release != latest_registry_version:
                raise UserBadParameterError(
                    f"Dependency {dep.identifier} is not at latest version "
                    f"{latest_registry_version}"
                )

        if len(unpublishable_deps) > 0:
            raise UserBadParameterError(
                "Packages can not be published with github or file dependencies: "
                + ", ".join([f"{dep.identifier}" for dep in unpublishable_deps])
            )

    @staticmethod
    def verify_file_structure(config: "Config"):
        """
        Validate folder & naming conventions for first-party packages.
        Raises UserBadParameterError if any rule is violated.
        """
        from pathlib import Path

        project_root: Path = config.project.paths.root

        if config.project.package is None:
            raise UserException(
                "Project has no package configuration. "
                "Please add a `package` section to your `ato.yaml` file."
            )
        expected_dirname = config.project.package.identifier.split("/")[-1]
        if project_root.name != expected_dirname:
            raise UserBadParameterError(
                f"Project directory '{project_root.name}' must be named "
                f"'{expected_dirname}'"
            )

        # 2. Required top-level files / dirs
        required = [
            project_root / "ato.yaml",
            project_root / f"{expected_dirname}.ato",
            project_root / "layouts",
            project_root / "parts",
            project_root / "README.md",
            project_root / "usage.ato",
        ]
        missing = [str(p.relative_to(project_root)) for p in required if not p.exists()]
        if missing:
            raise UserBadParameterError(
                "Missing required files/directories: " + ", ".join(missing)
            )

        # 3. ato.yaml must contain 'usage' build
        build_names = set(config.project.builds.keys())
        for required_build in {"usage"}:
            if required_build not in build_names:
                raise UserBadParameterError(
                    f"ato.yaml must define a '{required_build}' build target"
                )

        # 4. Build settings requirements
        for build_cfg in config.project.builds.values():
            if build_cfg.hide_designators is not True:
                raise UserBadParameterError(
                    "Every build must set 'hide_designators: true' in ato.yaml"
                )
            if "PCB.requires_drc_check" not in set(build_cfg.exclude_checks):
                raise UserBadParameterError(
                    "Every build must include "
                    "'exclude_checks: ['PCB.requires_drc_check']'"
                )

    @staticmethod
    def verify_build_exists(config: "Config"):
        missing_builds = [
            b
            for b in config.project.builds.keys()
            if not config.project.paths.root.joinpath("build", "builds").exists()
        ]
        if missing_builds:
            raise UserFileNotFoundError(
                "Missing build directories: "
                + ", ".join(missing_builds)
                + " Please run `ato build` to create the build directories."
            )

    @staticmethod
    def verify_usage_import(config: "Config"):
        """
        Verify that the `usage` build target's imports reference atopile packages.
        """
        import re
        from pathlib import Path

        import atopile.compiler.ast_types as AST
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.graph as graph
        import faebryk.core.node as fabll
        from atopile.compiler.antlr_visitor import ANTLRVisitor
        from atopile.compiler.parse import parse_file

        if (usage_build := config.project.builds.get("usage", None)) is None:
            raise UserBadParameterError("Missing 'usage' build target in ato.yaml")

        entry_path: Path = usage_build.entry_file_path
        if not entry_path.exists():
            raise UserFileNotFoundError(f"Usage build entry not found: {entry_path}")

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        root_ctx = parse_file(entry_path)
        ast_root = ANTLRVisitor(g, tg, entry_path).visit(root_ctx)
        assert isinstance(ast_root, AST.File)

        permitted_import_prefixes = {
            d.identifier for d in config.project.dependencies or []
        }

        # Package-local imports must also be fully-qualified
        if config.project.package is not None:
            permitted_import_prefixes.add(config.project.package.identifier)

        def iter_imports(scope: AST.Scope) -> list[AST.ImportStmt]:
            imports: list[AST.ImportStmt] = []
            for stmt_trait in scope.get_child_stmts():
                stmt_node = fabll.Traits(stmt_trait).get_obj_raw()
                if isinstance(stmt_node, AST.ImportStmt):
                    imports.append(stmt_node)
                    continue
                if isinstance(stmt_node, (AST.BlockDefinition, AST.ForStmt)):
                    imports.extend(iter_imports(stmt_node.scope.get()))
            return imports

        def format_import(node: AST.ImportStmt) -> str:
            path = node.get_path()
            if path is not None:
                return path
            return f"import {node.get_type_ref_name()}"

        from_paths: set[str] = set()
        for node in iter_imports(ast_root.scope.get()):
            path = node.get_path()
            if path is not None:
                from_paths.add(path)

        usage_text = entry_path.read_text(encoding="utf-8")
        for match in re.finditer(r'from\s+"([^"]+)"\s+import', usage_text):
            from_paths.add(match.group(1))

        offending: list[str] = []
        for path in sorted(from_paths):
            parts = [p for p in path.split("/") if p]
            if not parts:
                offending.append(path)
                continue

            # Allow local parts imports
            if parts[0] == "parts":
                continue

            # Allow fully-qualified imports from dependencies
            if (
                len(parts) >= 2
                and f"{parts[0]}/{parts[1]}" in permitted_import_prefixes
            ):
                continue

            offending.append(path)

        if offending:
            raise UserBadParameterError(
                "Import not found in installed packages, "
                "imports must use absolute path, e.g. 'atopile/...'. \n"
                "Offending imports: " + ", ".join(offending)
            )

    @staticmethod
    def verify_usage_in_readme(config: "Config"):
        """
        Verify that the `usage` build target's imports reference atopile packages.
        """
        usage_build = config.project.builds.get("usage", None)
        if usage_build is None:
            raise UserBadParameterError("Missing 'usage' build target in ato.yaml")

        usage_content = usage_build.entry_file_path.read_text(encoding="utf-8")
        readme_content = (config.project.paths.root / "README.md").read_text(
            encoding="utf-8"
        )

        if usage_content not in readme_content:
            raise UserBadParameterError(
                "Entire content of usage.ato must be included in the README.md file."
            )

    @staticmethod
    def verify_build_artifacts(config: "Config"):
        """
        Verify every build target has all required artifacts.
        """
        from faebryk.libs.package.artifacts import Artifacts

        builds_root = Artifacts.builds_dir(config.project)
        required_patterns = {
            "glb": "*.glb",
            "bom.csv": "*.bom.csv",
            "gerber.zip": "*gerber.zip",
            "step": "*step",
        }
        missing_by_build: dict[str, list[str]] = {}
        for build_name in config.project.builds.keys():
            build_dir = builds_root / build_name
            if not build_dir.exists():
                missing_by_build[build_name] = list(required_patterns.keys())
                continue
            missing: list[str] = []
            for label, pattern in required_patterns.items():
                if not any(build_dir.glob(pattern)):
                    missing.append(label)
            if missing:
                missing_by_build[build_name] = missing

        if missing_by_build:
            missing_lines = [
                f"{build_name}: {', '.join(missing)}"
                for build_name, missing in sorted(missing_by_build.items())
            ]
            raise UserBadParameterError(
                "Missing build artifacts per target:\n" + "\n".join(missing_lines)
            )

    @staticmethod
    def verify_3d_models(config: "Config"):
        from pathlib import Path

        from faebryk.libs.kicad.fileformats import kicad

        layout_path: Path = config.project.paths.layout
        kicad_pcb_paths = list(layout_path.rglob("*.kicad_pcb"))

        missing_models: list[str] = []

        def _resolve_model_path(raw: Path, pcb_dir: Path) -> Path:
            s = str(raw)
            s = s.replace("${KIPRJMOD}", str(pcb_dir))
            s = os.path.expandvars(s)
            p = Path(s)
            if p.is_absolute():
                return p
            return pcb_dir / p

        for pcb_path in kicad_pcb_paths:
            pcb_file = kicad.loads(kicad.pcb.PcbFile, pcb_path)
            pcb_dir = pcb_path.parent
            for fp in pcb_file.kicad_pcb.footprints:
                for m in getattr(fp, "models", []):
                    resolved = _resolve_model_path(m.path, pcb_dir)
                    if not resolved.exists():
                        missing_models.append(
                            f"{pcb_path.relative_to(config.project.paths.root)} -> "
                            f"{m.path} -> {resolved}"
                        )

        if missing_models:
            raise UserBadParameterError(
                "Missing 3D model files referenced in KiCad boards:\n\n"
                + "\n".join(missing_models)
            )

    @staticmethod
    def verify_no_warnings(config: "Config"):
        from atopile.model import build_history

        project_root = str(config.project.paths.root)

        # Query recent builds for this project from the database
        builds = build_history.get_builds_by_project_target(
            project_root=project_root,
            limit=50,  # Get recent builds
        )

        if not builds:
            raise UserFileNotFoundError(
                f"No build history found for {project_root}. "
                "Please run `ato build` to generate build records."
            )

        # Get the latest build for each target
        latest_by_target: dict[str, dict] = {}
        for build in builds:
            target = build.get("target", "default")
            if target not in latest_by_target:
                latest_by_target[target] = build

        # Check total warnings from latest builds per target
        total_warnings = sum(b.get("warnings", 0) for b in latest_by_target.values())
        if total_warnings > 0:
            # Collect warning details from individual builds
            warning_details: list[str] = []
            for target, build in latest_by_target.items():
                build_warnings = build.get("warnings", 0)
                if build_warnings > 0:
                    # Get full build info for stage details
                    build_info = build_history.get_build_info_by_id(build["build_id"])
                    if build_info:
                        stages_with_warnings = [
                            f"  - {stage['name']}: {stage['warnings']} warning(s)"
                            for stage in build_info.get("stages", [])
                            if stage.get("warnings", 0) > 0
                        ]
                        if stages_with_warnings:
                            warning_details.append(
                                f"{target} ({build_warnings} warning(s)):\n"
                                + "\n".join(stages_with_warnings)
                            )
                        else:
                            warning_details.append(
                                f"{target}: {build_warnings} warning(s)"
                            )
                    else:
                        warning_details.append(
                            f"{target}: {build_warnings} warning(s)"
                        )

            raise UserBadParameterError(
                f"Build completed with {total_warnings} warning(s). "
                "Warnings must be resolved before publishing.\n\n"
                + "\n".join(warning_details)
            )

    @staticmethod
    def verify_version_increment(config: "Config"):
        from atopile.config import config
        from atopile.errors import UserBadParameterError
        from faebryk.libs.backend.packages.api import Errors, PackagesAPIClient

        if config.project.package is None:
            raise UserBadParameterError("Package version is not set")
        if config.project.package.version is None:
            raise UserBadParameterError("Package version is not set")

        api = PackagesAPIClient()

        local_ver = Version.parse(config.project.package.version)
        try:
            registry_ver = api.get_package(
                config.project.package.identifier
            ).info.version
        except Errors.PackageNotFoundError:
            logger.warning(
                "Package not found in registry, skipping version check. "
                "This is expected for first-time publishes."
            )
            return

        if registry_ver is None:
            return

        semver_registry_ver = Version.parse(registry_ver)

        if local_ver <= semver_registry_ver:
            logger.warning(
                (
                    f"Package version {local_ver} is <= registry version "
                    f"{registry_ver} - package will not publish"
                )
            )

    @staticmethod
    def verify_unused_and_duplicate_imports(config: "Config"):
        import re

        _import_name_regex = r"(import ([^,\n]+))"

        ato_files = config.project.paths.root.rglob("*.ato")
        for ato_file in ato_files:
            import_statements: list[re.Match[str]] = []
            content = ato_file.read_text(encoding="utf-8")
            for import_name in re.finditer(_import_name_regex, content):
                import_statements.append(import_name)

            # check if the name is at lease twice in the file
            unused_imports: list[str] = []
            duplicates: list[str] = []
            for import_match in import_statements:
                if content.count(import_match.group(2)) < 2:
                    unused_imports.append(import_match.group(2))
                if content.count(import_match.group(1)) > 1:
                    duplicates.append(import_match.group(1))

            file_path = ato_file.relative_to(config.project.paths.root)
            message = ""
            if unused_imports:
                message = (
                    f"Unused imports: [{', '.join(unused_imports)}] in {file_path}"
                )
            if duplicates:
                message += (
                    f"\nDuplicate imports: [{', '.join(duplicates)}] in {file_path}"
                )
            if message:
                raise UserBadParameterError(message)


_DEFAULT_VALIDATORS = [
    _PackageValidators.verify_manifest,
    _PackageValidators.verify_build_exists,
    _PackageValidators.verify_pinned_dependencies,
    _PackageValidators.verify_version_increment,
    _PackageValidators.verify_usage_import,
]

_STRICT_VALIDATORS = [
    _PackageValidators.verify_3d_models,
    _PackageValidators.verify_file_structure,
    _PackageValidators.verify_no_warnings,
    _PackageValidators.verify_usage_import,
    _PackageValidators.verify_usage_in_readme,
    _PackageValidators.verify_build_artifacts,
    _PackageValidators.verify_unused_and_duplicate_imports,
]


@package_app.command()
@capture("cli:package_publish_start", "cli:package_publish_end")
def publish(
    version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            envvar="ATO_CLI_PACKAGE_VERSION",
            help="The version of the package to publish.",
        ),
    ] = "",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Dry run the package publication."),
    ] = False,
    package_address: Annotated[
        str | None,
        typer.Argument(help="The address of the package to publish."),
    ] = None,
    include_artifacts: Annotated[
        bool,
        typer.Option(
            "--include-artifacts",
            "-a",
            envvar="ATO_CLI_PACKAGE_INCLUDE_ARTIFACTS",
            help="Include build artifacts in the package.",
        ),
    ] = True,
    skip_auth: Annotated[
        bool,
        typer.Option("--skip-auth", "-s", help="Skip authentication."),
    ] = False,
    skip_duplicate_versions: Annotated[
        bool,
        typer.Option(
            "--skip-duplicate-versions",
            envvar="ATO_CLI_PACKAGE_SKIP_DUPLICATE_VERSIONS",
            help="Ignore duplicate version errors.",
        ),
    ] = False,
):
    """
    Publish a package to the package registry.

    Currently, the only supported authentication method is Github Actions OIDC.

    For the options which allow multiple inputs, use comma separated values.
    """
    import faebryk.libs.backend.packages.api as packages_api
    from atopile.config import config
    from atopile.errors import UserBadParameterError, UserException
    from faebryk.libs.backend.packages.api import PackagesAPIClient
    from faebryk.libs.package.artifacts import Artifacts
    from faebryk.libs.package.dist import Dist, DistValidationError

    # Apply the entry-point early
    # This will configure the project root properly, meaning you can practically spec
    # the working directory of the publish and expands for future use publishing
    # packagelets from specific module entrypoints
    config.apply_options(entry=package_address)
    logger.info("Using project config: %s", config.project.paths.root / "ato.yaml")

    if version:  # NOT `is not None` to allow for empty strings
        _apply_version(version, config)

    if config.project.package is None:
        raise UserException(
            "Project has no package configuration. "
            "Please add a `package` section to your `ato.yaml` file."
        )
    logger.info("Package version: %s", config.project.package.version)

    if not config.project.package.identifier:
        raise UserBadParameterError(
            "Project `identifier` is not set. Set via ATO_PACKAGE_IDENTIFIER envvar"
            " or in `ato.yaml`"
        )

    if not config.project.package.repository:
        raise UserBadParameterError(
            "Project `repository` is not set. Set via ATO_PACKAGE_REPOSITORY envvar"
            " or in `ato.yaml`"
        )

    # Build the package
    try:
        dist = Dist.build_dist(
            cfg=config.project,
            output_path=config.project.paths.build,
        )
    except DistValidationError as e:
        raise UserException(
            "Could not build package distribution: %s" % e
            + "\n Have a look at https://docs.atopile.io/atopile/essentials/4-packages"
        ) from e

    logger.info("Package distribution built: %s", dist.path)

    if include_artifacts:
        artifacts = Artifacts.build_artifacts(
            cfg=config.project, output_path=config.project.paths.build
        )
    else:
        artifacts = None

    try:
        from git import Repo

        repo = Repo(config.project.paths.root)
        git_ref = str(repo.head.ref)
    except Exception:
        git_ref = None

    # Upload sequence
    if dry_run:
        logger.info("Dry run, skipping upload")
    else:
        api = PackagesAPIClient()
        try:
            package_url = api.publish(
                identifier=config.project.package.identifier,
                version=str(config.project.package.version),
                dist=dist,
                artifacts=artifacts,
                git_ref=git_ref,
                skip_auth=skip_auth,
            ).url
        except packages_api.Errors.ReleaseAlreadyExistsError:
            if skip_duplicate_versions:
                logger.info("Release already exists, skipping")
                return
            else:
                raise

        logger.info("Package URL: %s", package_url)

    logger.info("Done! 📦🛳️")


@package_app.command()
@capture("cli:package_verify_start", "cli:package_verify_end")
def verify(
    package_address: Annotated[
        str | None,
        typer.Argument(
            help="Path/to/project or address (file.ato:Module) of the package "
            "you want to verify.",
        ),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict",
            "-s",
            help="Fail on any warning.",
            envvar="ATO_PACKAGE_VERIFY_STRICT_MODE",
        ),
    ] = False,
):
    """
    Validate that a package can be built and meets the registry rules.
    """

    from atopile.config import config

    config.apply_options(entry=package_address)

    with accumulate() as accumulator:
        for validator in _DEFAULT_VALIDATORS:
            with accumulator.collect():
                validator(config)

        if strict:
            logger.info("Running strict verification")
            for validator in _STRICT_VALIDATORS:
                with accumulator.collect():
                    validator(config)

    logger.info("Package verification successful! 🎉")
