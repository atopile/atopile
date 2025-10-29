# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.core.node as fabll
# from faebryk.core.link import Link


class has_single_connection(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    # @abstractmethod
    # def get_connection(self) -> Link: ...
