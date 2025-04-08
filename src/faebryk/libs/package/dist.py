# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pathspec
import pathvalidate
import rich.progress
from ruamel.yaml import YAML

import atopile.config
from atopile.errors import UserBadParameterError
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)


def _get_non_excluded_project_files(cfg: atopile.config.ProjectConfig) -> list[Path]:
    """
    Get all files in the project that aren't excluded by .gitignore.

    Args:
        cfg: The project configuration

    Returns:
        A list of Path objects for all non-excluded files
    """
    prjroot = cfg.paths.root
    gitignore_path = prjroot / ".gitignore"

    # For gitignore patterns, we need to get all files and filter out the matched ones,
    # since gitignore patterns specify which files to exclude
    all_files = []
    for p in prjroot.glob("**/*"):
        if p.is_file():
            all_files.append(str(p.relative_to(prjroot)))

    # Check if .gitignore exists
    if gitignore_path.exists():
        # Read gitignore patterns
        with open(gitignore_path, "r") as f:
            gitignore_patterns = f.read().splitlines()
        # Create a PathSpec from gitignore patterns
        spec = pathspec.PathSpec.from_lines("gitwildmatch", gitignore_patterns)

        # Filter out files that match the gitignore patterns
        matched_files = [f for f in all_files if not spec.match_file(f)]
    else:
        # If no .gitignore, include all files
        matched_files = all_files

    return [prjroot / f for f in matched_files]


class Dist:
    def __init__(self, path: Path):
        self.path = path

    @property
    def manifest(self) -> dict[str, Any]:
        with zipfile.ZipFile(self.path, "r") as zip_file:
            manifest_file = zip_file.read(str(atopile.config.PROJECT_CONFIG_FILENAME))
            return YAML().load(manifest_file)

    @staticmethod
    def build_dist(
        cfg: atopile.config.ProjectConfig | Path,
        include_builds_set: set[str] | None,
        output_path: Path,
    ) -> "Dist":
        """
        Build a distribution package for the given project.
        """
        if isinstance(cfg, Path):
            # TODO better error handling
            cfg = not_none(atopile.config.ProjectConfig.from_path(cfg))

        if cfg.package is None:
            # TODO say which project
            raise ValueError(
                "Project has no package configuration. "
                "Please add a `package` section to your `ato.yaml` file."
            )

        if include_builds_set is None:
            include_builds_set = set(cfg.builds)

        package_filename = (
            pathvalidate.sanitize_filename(
                f"{cfg.package.name}-{cfg.package.version}".replace("/", "-")
            )
            + ".zip"
        )

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

            config_data["package"]["name"] = cfg.package.name
            config_data["package"]["repository"] = cfg.package.repository
            config_data["package"]["version"] = str(cfg.package.version)

            config_data["builds"] = {
                k: v
                for k, v in config_data["builds"].items()
                if k in include_builds_set
            }

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
            with zipfile.ZipFile(zip_path, "x") as zip_file:
                ## Copy in the freshly minted package config
                zip_file.write(
                    package_config_path, atopile.config.PROJECT_CONFIG_FILENAME
                )

                ## Copy in the files to package
                for file in rich.progress.track(
                    matched_files, description="Building package..."
                ):
                    src_path = cfg.paths.root / file
                    if not src_path.is_file():
                        continue

                    if file.name == "ato.yaml":
                        continue

                    zip_file.write(src_path, file.relative_to(cfg.paths.root))

            shutil.move(zip_path, output_path)

            return Dist(output_path)

    def install(self, path: Path):
        if path.exists():
            raise FileExistsError(f"Path {path} already exists")
        with zipfile.ZipFile(self.path, "r") as zip_file:
            zip_file.extractall(path)
