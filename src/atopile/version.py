import importlib.metadata
import logging

import semver

from atopile.project.project import Project
from atopile.utils import is_editable_install

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def parse(version_str: str) -> semver.Version:
    """
    Robustly parse versions, even if a little wonky

    semver package is very strict about matching the semver spec
    spec for reference: https://semver.org/
    if we can't parse the version string, it's most likely because
    hatch uses "." as a separator between the version number and
    prerelease/build information, but semver requires "-"
    we are going to support hatch's shenanigans by splitting and
    reconstituting the string
    hatch example: "0.0.17.dev0+g0151069.d20230928"
    """

    try:
        version = semver.Version.parse(version_str)
    except ValueError:
        dot_split = version_str.split(".")
        version_str = "-".join(
            ".".join(fragments) for fragments in (dot_split[:3], dot_split[3:])
        )
        version = semver.Version.parse(version_str)

    return version


def clean_version(verion: semver.Version) -> semver.Version:
    """
    Clean a version by dropping any prerelease or build information
    """
    return semver.Version(
        verion.major,
        verion.minor,
        verion.patch,
    )


def get_version() -> semver.Version:
    """
    Get the installed atopile version
    """

    ap_version_str = importlib.metadata.version("atopile")
    return parse(ap_version_str)


def match(spec: str, version: semver.Version):
    """
    Check if a version matches a given specifier

    :param spec: the specifier to match against
    :param version: the version to check
    :return: True if the version matches the specifier, False otherwise
    """
    # first clean up the spec string
    spec = spec.strip()

    # for match checking, we accept dirty builds
    # so we clean the version before checking
    version = clean_version(version)

    if spec == "*":
        return True

    if "||" in spec:
        for s in spec.split("||"):
            if match(s, version):
                return True
        return False

    if " " in spec:
        for s in spec.split(" "):
            if not match(s, version):
                return False
        return True

    if spec[:2] in ("==", ">=", "<="):
        operator = spec[:2]
        specd_version = parse(spec[2:])
    elif spec[0] in ("^", "~", "!", ">", "<"):
        operator = spec[0]
        specd_version = parse(spec[1:])
    else:
        # if there's not operator, default to ^ (up to next major)
        try:
            specd_version = parse(spec)
            operator = "^"
        except ValueError as ex:
            # finally, if we could do any of that, we assume there's something wrong with the spec
            raise SyntaxError(f"Invalid version spec: {spec}") from ex

    if operator == "^":
        # semver doesn't support ^, so we have to do it ourselves
        # ^1.2.3 is equivalent to >=1.2.3 <2.0.0
        return version >= specd_version and version < specd_version.bump_major()

    if operator == "~":
        # semver doesn't support ~, so we have to do it ourselves
        # ~1.2.3 is equivalent to >=1.2.3 <1.3.0
        return version >= specd_version and version < specd_version.bump_minor()

    if operator == "!":
        return version != specd_version

    if operator == "==":
        return version == specd_version

    if operator == ">=":
        return version >= specd_version

    if operator == "<=":
        return version <= specd_version

    if operator == ">":
        return version > specd_version

    if operator == "<":
        return version < specd_version


def check_project_version(project: Project) -> bool:
    """
    Check if the current version of Atopile matches the version specified in the project's configuration file.

    :param project: The project to check the version for.
    :type project: Project
    :return: True if the current version matches the project's version specification, False otherwise.
    :rtype: bool
    """
    version_spec = project.config.atopile_version
    if version_spec is None:
        log.warning("No atopile version requirement specified in ato.yaml")
        return True

    installed_version = get_version()
    is_match = match(version_spec, installed_version)

    if not is_match and is_editable_install():
        log.warning(
            "atopile is installed in editable mode, so version checks can be erroneous. "
            "Consider running `ato meta update` and trying again."
        )

    if not is_match:
        log.error(
            "Project demands atopile version %s, but you have %s installed.",
            project.config.atopile_version,
            get_version(),
        )

    return is_match
