# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import tempfile
from pathlib import Path

import atopile.config as config
from atopile import errors
from faebryk.libs.backend.packages.api import PackagesAPIClient
from faebryk.libs.package.dist import Dist
from faebryk.libs.util import clone_repo, not_none, robustly_rm_dir

logger = logging.getLogger(__name__)


class ProjectDependency:
    def __init__(self, spec: config.DependencySpec | str):
        if isinstance(spec, str):
            spec = config.DependencySpec.from_str(spec)
        self.spec = spec
        self.dist: Dist | None = None
        self.cfg: config.ProjectConfig | None = None

    # @property
    # def project_config(self) -> config.ProjectConfig:
    #    pass

    @property
    def name(self) -> str:
        assert self.dist is not None or self.cfg is not None
        if self.cfg:
            return not_none(self.cfg.package).identifier
        assert self.dist is not None
        # TODO: I hate strings so goddamn much
        return self.dist.manifest["package"]["identifier"]

    @property
    def target_path(self) -> Path:
        # TODO don't really like using identifier as import path
        # would be nicer to use source name and indirect imports
        gcfg = config.config
        return gcfg.project.paths.modules / self.name

    def _install_from_dist(self, dist: Dist):
        config.ProjectConfig.set_or_add_dependency(config.config, self.spec)
        dist.install(self.target_path)

    def install(self, allow_upgrade: bool = False):
        # TODO implement upgrade check
        if not allow_upgrade:
            raise NotImplementedError("Only upgrade=True is supported at the moment")

        with tempfile.TemporaryDirectory() as temp_dir:
            if isinstance(
                self.spec, (config.LocalDependencySpec, config.GitDependencySpec)
            ):
                if isinstance(self.spec, config.LocalDependencySpec):
                    path = self.spec.path
                    if not path.exists():
                        raise errors.UserFileNotFoundError(
                            f"Local dependency path {path} does not exist for"
                            f" {self.spec.name}"
                        )
                else:
                    path = clone_repo(
                        self.spec.repo_url,
                        clone_target=Path(temp_dir) / "repo",
                        ref=self.spec.ref,
                    )
                    if self.spec.path_within_repo:
                        path = path / self.spec.path_within_repo

                dist = Dist.build_dist(
                    cfg=path,
                    include_builds_set=None,
                    output_path=Path(temp_dir),
                )

            if isinstance(self.spec, config.RegistryDependencySpec):
                api = PackagesAPIClient()
                dist = api.release_dist(
                    self.spec.identifier,
                    Path(temp_dir),
                    version=self.spec.release,
                )
            self.dist = dist

            # TODO cache dist

            if self.target_path.exists():
                if allow_upgrade:
                    robustly_rm_dir(self.target_path)
                else:
                    raise errors.UserFileExistsError(
                        f"Dependency {self.spec.name} already exists at"
                        f" {self.target_path}"
                    )
            self._install_from_dist(dist)

    def remove(self):
        raise NotImplementedError("Removing dependencies is not implemented")
