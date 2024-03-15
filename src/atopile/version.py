"""
Tools to compare semantic versions using npm style version specifiers.
"""

import importlib.metadata
import logging

from semver import Version

from atopile import errors

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class VersionMismatchError(errors.AtoError):
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
    ap_version_str = importlib.metadata.version("atopile")
    semver = parse(ap_version_str)
    return semver


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

    # Until the first major release, we're assuming
    # that minor releases are breaking changes
    if compiler_semver.major == 0:
        match_operator = "~"
    else:
        match_operator = "^"

    # Check if we match
    return match(f"{match_operator}{built_with_version}", compiler_semver)


OPERATORS = ("*", "||", "^", "~", "!", "==", ">=", "<=", ">", "<")


def match(spec: str, version: Version):
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
            raise errors.AtoError(f"Invalid version spec: {spec}") from ex

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
