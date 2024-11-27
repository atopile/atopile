# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.libs.library import L


class is_app_root(L.Module.TraitT.decless()):
    """
    Indicates that the module is the root of an application.
    """

    def on_obj_set(self):
        obj = self.get_obj(L.Node)
        obj.no_include_parents_in_full_name = True
