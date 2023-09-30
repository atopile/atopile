import logging

import semver

from atopile.targets.targets import Target, TargetCheckResult, TargetMuster
from atopile.version import get_version


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class AtoVersion(Target):
    name = "ato-version"

    def __init__(self, muster: TargetMuster) -> None:
        super().__init__(muster)

    def build(self) -> None:
        # nothing to do here
        pass

    def resolve(self, *args, clean=None, **kwargs) -> None:
        log.error(
            "Cannot resolve this target automatically. Please run `ato meta"
            " update` to update atopile."
        )

    def check(self) -> TargetCheckResult:
        version_requirement = self.project.config.atopile_version
        if version_requirement is None:
            log.warning("No atopile version requirement specified in ato.yaml")
            return TargetCheckResult.UNTIDY

        if get_version().match(version_requirement):
            return TargetCheckResult.COMPLETE

        return TargetCheckResult.UNSOLVABLE
