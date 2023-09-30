import semver
import importlib.metadata
import logging

from atopile.utils import is_editable_install

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def warn_editable_install() -> None:
    """
    Log a warning if the installed atopile version is a dev version.
    """
    if is_editable_install():
        log.warning(
            "You are using an editable install of atopile, which means "
            "version numbers are unreliable."
        )
        log.info("If atopile fails due to an "
            "outdated version, try reinstalling with `ato meta update`"
        )


def get_version() -> semver.Version:
    """
    Get the installed atopile version
    """

    ap_version_str = importlib.metadata.version("atopile")
    try:
        version = semver.Version.parse(ap_version_str)
    except ValueError:
        # semver package is very strict about matching the semver spec
        # spec for reference: https://semver.org/
        # if we can't parse the version string, it's most likely because
        # hatch uses "." as a separator between the version number and
        # prerelease/build information, but semver requires "-"
        # we are going to support hatch's shenanigans by splitting and
        # reconstituting the string
        # hatch example: "0.0.17.dev0+g0151069.d20230928"
        dot_split = ap_version_str.split(".")
        version_str = "-".join(".".join(fragments) for fragments in (dot_split[:3], dot_split[3:]))
        version = semver.Version.parse(version_str)

    return version


def check_project_version(project: Project) -> bool:
    """"""
