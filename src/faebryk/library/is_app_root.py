# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class is_app_root(fabll.Module.TraitT.decless()):
    """
    Indicates that the module is the root of an application.
    """

    def on_obj_set(self):
        obj = self.get_obj(fabll.Node)
        obj.no_include_parents_in_full_name = True
