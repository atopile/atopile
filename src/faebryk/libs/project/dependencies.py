# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import tempfile
from pathlib import Path

import atopile.config as config
from atopile import errors
from faebryk.libs.package.dist import Dist
from faebryk.libs.util import robustly_rm_dir

logger = logging.getLogger(__name__)


class ProjectDependency:
    def __init__(self, spec: config.DependencySpec | str):
        if isinstance(spec, str):
            spec = config.DependencySpec.from_str(spec)
        self.spec = spec
        self.dist: Dist | None = None

    # @property
    # def project_config(self) -> config.ProjectConfig:
    #    pass

    @property
    def name(self) -> str:
        assert self.dist is not None
        return self.dist.manifest["package"]["identifier"]

    @property
    def target_path(self) -> Path:
        gcfg = config.config
        return gcfg.project.paths.modules / self.name

    def _install_from_dist(self, dist: Dist):
        config.ProjectConfig.set_or_add_dependency(config.config, self.spec)
        dist.install(self.target_path)

    def install(self, allow_upgrade: bool = False):
        # TODO implement upgrade check
        if not allow_upgrade:
            raise NotImplementedError("Only upgrade=True is supported at the moment")

        # TODO remove
        if not isinstance(self.spec, config.LocalDependencySpec):
            raise NotImplementedError(
                "Only local dependencies are supported at the moment"
            )
        path = self.spec.path
        if not path.exists():
            raise errors.UserFileNotFoundError(
                f"Local dependency path {path} does not exist for {self.spec.name}"
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            dist = Dist.build_dist(
                cfg=path,
                include_builds_set=None,
                output_path=Path(temp_dir) / "dist.zip",
            )
            self.dist = dist

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
