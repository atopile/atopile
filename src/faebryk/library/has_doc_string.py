# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Any

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_doc_string(fabll.Node):
    """
    Trait for modules/components/interfaces that have a docstring.

    This trait is automatically attached when a block has a docstring
    (triple-quoted string statement as the first statement in the block).

    Example ato usage:
        module MyModule:
            '''
            This is the docstring for MyModule.
            It can span multiple lines.
            '''
            r = new Resistor
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()

    doc_string_ = F.Parameters.StringParameter.MakeChild()

    @property
    def doc_string(self) -> str:
        """Get the docstring text."""
        return str(self.doc_string_.get().extract_singleton())

    @classmethod
    def MakeChild(cls, doc_string: str) -> fabll._ChildField[Any]:  # type: ignore[override]
        """Create a has_doc_string trait with the given docstring text."""
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.doc_string_], doc_string)
        )
        return out
