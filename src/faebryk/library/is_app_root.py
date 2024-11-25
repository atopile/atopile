# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.libs.library import L


class is_app_root(L.Module.TraitT.decless()):
    """
    Indicates that the module is the root of an application.
    """
