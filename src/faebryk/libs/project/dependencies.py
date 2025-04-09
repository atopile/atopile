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
    def __init__(
        self,
        spec: config.DependencySpec | str,
        gcfg: config.ProjectConfig | None = None,
    ):
        if isinstance(spec, str):
            spec = config.DependencySpec.from_str(spec)
        self.spec = spec
        self.dist: Dist | None = None
        self.cfg: config.ProjectConfig | None = None
        self.gcfg = gcfg or config.config.project

    @property
    def project_config(self) -> config.ProjectConfig:
        assert self.cfg is not None
        return self.cfg

    @property
    def identifier(self) -> str:
        assert self.dist is not None or self.cfg is not None
        if self.cfg:
            return not_none(self.cfg.package).identifier
        assert self.dist is not None
        return self.dist.identifier

    @property
    def target_path(self) -> Path:
        # TODO don't really like using identifier as import path
        # would be nicer to use source name and indirect imports
        return self.gcfg.paths.modules / self.identifier

    def install(self, allow_upgrade: bool = False):
        # TODO implement upgrade check
        if not allow_upgrade:
            raise NotImplementedError("Only upgrade=True is supported at the moment")

        with tempfile.TemporaryDirectory() as temp_dir:
            if isinstance(
                self.spec, (config.FileDependencySpec, config.GitDependencySpec)
            ):
                if isinstance(self.spec, config.FileDependencySpec):
                    path = self.spec.path
                    if not path.exists():
                        raise errors.UserFileNotFoundError(
                            f"Local dependency path {path} does not exist for"
                            f" {self.spec.identifier}"
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
                    output_path=Path(temp_dir),
                )
                self.spec.identifier = dist.identifier

            if isinstance(self.spec, config.RegistryDependencySpec):
                api = PackagesAPIClient()
                dist = api.release_dist(
                    self.spec.identifier,
                    Path(temp_dir),
                    version=self.spec.release,
                )
                self.spec.release = dist.version
            self.dist = dist

            # TODO cache dist

            if self.target_path.exists():
                if allow_upgrade:
                    robustly_rm_dir(self.target_path)
                else:
                    raise errors.UserFileExistsError(
                        f"Dependency {self.spec.identifier} already exists at"
                        f" {self.target_path}"
                    )

            config.ProjectConfig.set_or_add_dependency(config.config, self.spec)
            dist.install(self.target_path)

    def remove(self):
        raise NotImplementedError("Removing dependencies is not implemented")

    def try_load(self):
        if not self.target_path.exists():
            return
        self.cfg = config.ProjectConfig.from_path(self.target_path)

    @staticmethod
    def load_all_from_config(cfg: config.ProjectConfig):
        deps = [ProjectDependency(spec, gcfg=cfg) for spec in cfg.dependencies or []]
        for dep in deps:
            dep.try_load()

        return deps
