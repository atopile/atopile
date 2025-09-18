# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.module import Module
from faebryk.core.parameter import R, p_field
from faebryk.core.node import Node

# A "version" type
class Version(Node):
    major = p_field(domain=R.Domains.Numbers.NATURAL)
    minor = p_field(domain=R.Domains.Numbers.NATURAL)
    patch = p_field(domain=R.Domains.Numbers.NATURAL)

    def set_version(self, version_str: str):
        self.major.alias_is(version_str.split(".")[0])
        self.minor.alias_is(version_str.split(".")[1])
        self.patch.alias_is(version_str.split(".")[2])

# A "dependency" type
class Dependency(Node):
    identifier: p_field()
    version: Version

    def __init__(self, identifier_str: str, version_str: str):
        super().__init__()
        self._identifier_str = identifier_str
        self._version_str = version_str

    def __postinit__(self):
        self.identifier.alias_is(self._identifier_str)
        self.version.set_version(self._version_str)


class is_project(Module.TraitT.decless()):
    required_atopile_version: Version

    def __init__(self, version_str: str):
        super().__init__()
        self._version_str = version_str

    def __postinit__(self):
        self.required_atopile_version.set_version(self._version_str)

class is_package(Module.TraitT.decless()):
    package_version: Version

    def __init__(self, version_str: str):
        super().__init__()
        self._version_str = version_str

    def __postinit__(self):
        self.package_version.set_version(self._version_str)


trait = is_project(version_str="1.0.0")
trait = is_package(version_str="1.0.0")

# trait = has_project_config(version_major=1, version_minor=0, version_patch=0)
# trait = is_package(
#     repository_url="https://github.com/faebryk/faebryk",
#     package_identifier="faebryk/faebryk",
#     package_version=Version(major=1, minor=0, patch=0))
