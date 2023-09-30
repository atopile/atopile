import semver
import importlib.metadata
import logging

from atopile.project.project import Project

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

    if spec.startswith("^"):
        # semver doesn't support ^, so we have to do it ourselves
        # ^1.2.3 is equivalent to >=1.2.3 <2.0.0
        specd_version = parse(spec[1:])
        return version >= specd_version and version < specd_version.bump_major()

    if spec.startswith("~"):
        # semver doesn't support ~, so we have to do it ourselves
        # ~1.2.3 is equivalent to >=1.2.3 <1.3.0
        specd_version = parse(spec[1:])
        return version >= specd_version and version < specd_version.bump_minor()

    if spec.startswith("!"):
        return version != parse(spec[1:])

    if spec.startswith("=="):
        return version == parse(spec[2:])

    if spec.startswith(">="):
        return version >= parse(spec[2:])

    if spec.startswith("<="):
        return version <= parse(spec[2:])

    if spec.startswith(">"):
        return version > parse(spec[1:])

    if spec.startswith("<"):
        return version < parse(spec[1:])

    # if there's not operator, default to ^ (up to next major)
    try:
        specd_version = parse(spec)
        return version >= specd_version and version < specd_version.bump_major()
    except ValueError:
        pass

    # finally, if we could do any of that, we assume there's something wrong with the spec
    raise SyntaxError(f"Invalid version spec: {spec}")


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

    return match(version_spec, get_version())
