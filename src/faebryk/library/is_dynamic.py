# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.parameter import Parameter


class is_dynamic(Parameter.TraitT):
    """
    Marks a parameter as dynamic, meaning that it needs to be re-evaluatated before use.
    Current use only for parameters related through bus connections.
    """

    def exec(self):
        pass
