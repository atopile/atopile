# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.module import Module
from faebryk.core.parameter import R, p_field
from faebryk.core.node import Node
from faebryk.core.graphinterface import GraphInterface

# Top
class Top(Node):
    def __postinit__(self):
        self.add(is_project())
        self.add(is_package())
        self.add(has_dependencies())

# Types
class Version(Node):
    major = p_field(domain=R.Domains.Numbers.NATURAL)
    minor = p_field(domain=R.Domains.Numbers.NATURAL)
    patch = p_field(domain=R.Domains.Numbers.NATURAL)

    def set_version(self, version_str: str):
        if version_str is not None:
            self.major.alias_is(version_str.split(".")[0])
            self.minor.alias_is(version_str.split(".")[1])
            self.patch.alias_is(version_str.split(".")[2])

class Dependency(Node):
    identifier: p_field()
    version: Version
    depencency_interface: GraphInterface

    def set_identifier(self, identifier_str: str):
        self.identifier.alias_is(identifier_str)

class Author(Node):
    name: p_field()
    email: p_field()

    def set_name(self, name: str):
        self.name.alias_is(name)

    def set_email(self, email: str):
        self.email.alias_is(email)

# Traits
class is_project(Module.TraitT.decless()):
    required_atopile_version: Version

    def __init__(self, version_str: str = None):
        super().__init__()
        self._version_str = version_str

    def __postinit__(self):
        self.required_atopile_version.set_version(self._version_str)

class is_package(Module.TraitT.decless()):
    author: Author
    package_version: Version
    package_identifier: p_field()
    repository_url: p_field()

    def __init__(self,
        author_name: str = None,
        author_email: str = None,
        version_str: str = None,
        package_identifier: str = None,
        repository_url: str = None
        ):
        super().__init__()
        self._author_name = author_name
        self._author_email = author_email
        self._version_str = version_str
        self._package_identifier = package_identifier
        self._repository_url = repository_url

    def __postinit__(self):
        self.package_version.set_version(self._version_str)

class has_dependencies(Module.TraitT.decless()):
    dependency_interface: GraphInterface

class is_pcb(Module.TraitT.decless()):
    pass

# trait1 = is_project(version_str="1.0.0")
# trait2 = is_package(version_str="1.0.0")
# trait3 = has_dependencies()

# trait3.dependency_interface.connect(Dependency(identifier_str="faebryk/faebryk", version_str="1.0.0").depencency_interface)
# trait3.dependency_interface.connect(Dependency(identifier_str="faebryk/faebryk", version_str="1.0.0").depencency_interface)


top = Top()
graph = top.get_graph()
