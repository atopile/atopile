# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class is_app_root(fabll.Node):
    """
    Indicates that the module is the root of an application.
    """

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def on_obj_set(self):
        parent = self.get_parent_force()[0]
        parent.no_include_parents_in_full_name = True
 