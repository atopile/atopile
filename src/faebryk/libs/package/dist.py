# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import itertools
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path

import pathspec
import pathvalidate
from ruamel.yaml import YAML

import atopile.config
from atopile import version
from atopile.errors import UserBadParameterError
from faebryk.libs.util import not_none, once

logger = logging.getLogger(__name__)


def _get_non_excluded_project_files(cfg: atopile.config.ProjectConfig) -> list[Path]:
    """
    Get all files in the project that aren't excluded by .gitignore.

    Args:
        cfg: The project configuration

    Returns:
        A list of Path objects for all non-excluded files
    """
    from git import Repo

    prjroot = cfg.paths.root
    repo = Repo(search_parent_directories=True)

    # For gitignore patterns, we need to get all files and filter out the matched ones,
    # since gitignore patterns specify which files to exclude
    ignore_pattern_lines = [".git/"]
    for ignore_file in itertools.chain(
        # TODO: only search directories between cwd and root
        # TODO include other gitignore sources
        Path(repo.working_tree_dir or prjroot).glob("*.gitignore"),
        Path(repo.working_tree_dir or prjroot).glob("*.atoignore"),
    ):
        if not ignore_file.is_file():
            continue
        with open(ignore_file, "r") as f:
            ignore_pattern_lines.extend(line.strip() for line in f.readlines())

    ignore_spec = pathspec.GitIgnoreSpec.from_lines(ignore_pattern_lines)

    return [prjroot / f for f in ignore_spec.match_tree_files(prjroot, negate=True)]


class DistValidationError(Exception): ...


class Dist:
    def __init__(self, path: Path):
        self.path = path
        self.validate()

    def validate(self) -> None:
        # validate
        try:
            self.manifest
        except Exception as e:
            raise DistValidationError(f"Invalid dist, can't load manifest: {e}") from e
        if self.manifest.package is None:
            raise DistValidationError("Invalid dist, manifest has no package")
        if self.manifest.package.version is None:
            raise DistValidationError("Invalid dist, manifest has no package version")
        if self.manifest.package.identifier is None:
            raise DistValidationError(
                "Invalid dist, manifest has no package identifier"
            )

    @property
    @once
    def manifest(self) -> atopile.config.ProjectConfig:
        with zipfile.ZipFile(self.path, "r") as zip_file:
            manifest_file = zip_file.read(str(atopile.config.PROJECT_CONFIG_FILENAME))
            return atopile.config.ProjectConfig.from_bytes(manifest_file)

    @property
    def version(self) -> str:
        return not_none(self.manifest.package).version

    @property
    def identifier(self) -> str:
        return not_none(self.manifest.package).identifier

    @property
    def compiler_version_spec(self) -> str:
        return not_none(self.manifest.requires_atopile)

    @property
    def bytes(self) -> int:
        return self.path.stat().st_size

    @staticmethod
    def get_package_filename(cfg: atopile.config.ProjectConfig) -> str:
        if cfg.package is None:
            raise DistValidationError("Project has no package configuration")
        return (
            pathvalidate.sanitize_filename(
                f"{cfg.package.identifier}-{cfg.package.version}".replace("/", "-")
            )
            + ".zip"
        )

    @staticmethod
    def build_dist(
        cfg: atopile.config.ProjectConfig | Path,
        output_path: Path,
    ) -> "Dist":
        """
        Build a distribution package for the given project.
        """
        if isinstance(cfg, Path):
            # TODO better error handling

            try:
                _cfg = atopile.config.ProjectConfig.from_path(cfg)
            except Exception as e:
                raise DistValidationError(
                    f"Could not load project config at: {cfg}: {e}"
                ) from e
            if _cfg is None:
                raise DistValidationError(f"Could not load project config at: {cfg}")
            cfg = _cfg

        if cfg.package is None:
            raise DistValidationError("Project has no package configuration")

        package_filename = Dist.get_package_filename(cfg)
        matched_files = _get_non_excluded_project_files(cfg)
        # TODO: make this ./dist or the likes?
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / package_filename

            # Create the package config
            package_config_path = temp_path / atopile.config.PROJECT_CONFIG_FILENAME

            yaml = YAML(typ="rt")  # round-trip
            with (cfg.paths.root / atopile.config.PROJECT_CONFIG_FILENAME).open(
                "r", encoding="utf-8"
            ) as file:
                config_data: dict = yaml.load(file) or {}

            config_data["package"]["identifier"] = str(cfg.package.identifier)
            config_data["package"]["repository"] = str(cfg.package.repository)
            config_data["package"]["version"] = str(cfg.package.version)

            with package_config_path.open("w", encoding="utf-8") as file:
                yaml.dump(config_data, file)

            ## Validate the package config is a valid config at all
            try:
                atopile.config.ProjectConfig.from_path(package_config_path)
            except Exception as e:
                raise UserBadParameterError(
                    "Something went wrong while validating the package config. "
                    "Please check the config file."
                ) from e

            # Bundle up the package
            with zipfile.ZipFile(
                zip_path, "x", compression=zipfile.ZIP_BZIP2, compresslevel=9
            ) as zip_file:
                ## Copy in the freshly minted package config
                zip_file.write(
                    package_config_path, atopile.config.PROJECT_CONFIG_FILENAME
                )

                ## Copy in the files to package
                for file in matched_files:
                    # rich.progress.track(
                    #    matched_files, description=f"Building {package_filename}..."
                    # ):
                    src_path = cfg.paths.root / file
                    if not src_path.is_file():
                        continue

                    if file.name == "ato.yaml":
                        continue

                    zip_file.write(src_path, file.relative_to(cfg.paths.root))

            out_file = output_path / package_filename
            if out_file.exists():
                out_file.unlink()
            out_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(zip_path, out_file)

            return Dist(out_file)

    def install(self, path: Path):
        if path.exists():
            raise FileExistsError(f"Path {path} already exists")

        if not version.match(
            self.compiler_version_spec,
            version.get_installed_atopile_version(),
        ):
            raise version.VersionMismatchError(
                f"Compiler version {version.get_installed_atopile_version()} "
                f"does not match required version {self.compiler_version_spec}"
                f"of package {self.identifier}@{self.version}"
            )

        with zipfile.ZipFile(self.path, "r") as zip_file:
            zip_file.extractall(path)
