"""
Tools to compare semantic versions using npm style version specifiers.
"""

import importlib.metadata
import logging

import requests
from semver import Version

from atopile import errors

log = logging.getLogger(__name__)

DISTRIBUTION_NAME = "atopile"
UPGRADE_DOCS_URL = "https://docs.atopile.io/atopile/guides/install"


class VersionMismatchError(errors.UserException):
    """
    Raise when the compiler version isn't
    compatible with the project version.
    """


def parse(version_str: str) -> Version:
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
    if version_str.startswith("v"):
        version_str = version_str[1:]

    try:
        version = Version.parse(version_str)
    except ValueError:
        dot_split = version_str.split(".")
        version_str = "-".join(
            ".".join(fragments) for fragments in (dot_split[:3], dot_split[3:])
        )
        version = Version.parse(version_str)

    return version


def clean_version(verion: Version) -> Version:
    """
    Clean a version by dropping any prerelease or build information
    """
    return Version(
        verion.major,
        verion.minor,
        verion.patch,
    )


def get_installed_atopile_version() -> Version:
    """
    Get the installed atopile version
    """
    ap_version_str = importlib.metadata.version(DISTRIBUTION_NAME)
    semver = parse(ap_version_str)
    return semver


def get_latest_atopile_version() -> Version | None:
    """
    Get the latest atopile version
    """
    try:
        response = requests.get(
            f"https://pypi.org/pypi/{DISTRIBUTION_NAME}/json", timeout=0.1
        )
        response.raise_for_status()
        version_str = response.json()["info"]["version"]
    except (KeyError, requests.exceptions.RequestException):
        log.debug("Failed to get latest version")
        return None

    return parse(version_str)


def match_compiler_compatability(built_with_version: Version) -> bool:
    """
    Check whether the currently installed compiler is compatible with
    presumably a project.
    We assume that if we're pre-release, we're compatible with
    the next major (or minor if major is 0) release to come.
    """
    # Figure out what we are
    compiler_semver = get_installed_atopile_version()
    if compiler_semver.prerelease:
        compiler_semver = clean_version(compiler_semver)
        if compiler_semver.major == 0:
            compiler_semver = compiler_semver.bump_patch()
        else:
            compiler_semver = compiler_semver.bump_minor()

    # Check if we match
    return match(f">={built_with_version},<0.4.0", compiler_semver)


OPERATORS = ("*", "^", "~", "!", "==", ">=", "<=", ">", "<")


def match(spec: str, version: Version) -> bool:
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

    if "," in spec:
        for s in spec.split(","):
            if not match(s, version):
                return False
        return True

    for operator in OPERATORS:
        if spec.startswith(operator):
            specd_version = parse(spec[len(operator) :])
            break
    else:
        # if there's not operator, default to ^ (up to next major)
        try:
            specd_version = parse(spec)
            operator = "^"
        except ValueError as ex:
            # finally, if we could do any of that, we assume there's something wrong with the spec # noqa: E501  # pre-existing
            raise errors.UserException(f"Invalid version spec: {spec}") from ex

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

    else:
        raise ValueError(f"Invalid operator: {operator}")


def check_for_update() -> None:
    installed_version = get_installed_atopile_version()
    latest_version = get_latest_atopile_version()
    installed_version_clean = clean_version(installed_version)

    if latest_version is None:
        return

    if installed_version < latest_version:
        log.warning(
            "Your version of atopile (%s) is out-of-date. Latest version: %s.\n"
            "You can find upgrade instructions here: %s",
            installed_version_clean,
            latest_version,
            UPGRADE_DOCS_URL,
        )
    elif installed_version > latest_version:
        log.info(
            "Current version (%s) is newer than latest (%s)",
            installed_version_clean,
            latest_version,
        )
