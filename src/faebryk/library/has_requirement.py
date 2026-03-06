# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Any

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_requirement(fabll.Node):
    """
    Trait for capturing natural language design requirements.

    Requirements represent design intent that can't be expressed as formal
    ``assert`` constraints. Each requirement has an ID, descriptive text,
    and acceptance criteria.

    Example ato usage:
        module PowerFrontEnd:
            trait has_requirement<
                id="R1",
                text="40V input",
                criteria="Power path rated for 60V",
            >
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()

    id_ = F.Parameters.StringParameter.MakeChild()
    text_ = F.Parameters.StringParameter.MakeChild()
    criteria_ = F.Parameters.StringParameter.MakeChild()

    @property
    def id(self) -> str:
        """Get the requirement ID (e.g. 'R1')."""
        return str(self.id_.get().extract_singleton())

    @property
    def text(self) -> str:
        """Get the requirement description."""
        return str(self.text_.get().extract_singleton())

    @property
    def criteria(self) -> str:
        """Get the acceptance criteria."""
        return str(self.criteria_.get().extract_singleton())

    @classmethod
    def MakeChild(  # type: ignore[override]
        cls, id: str, text: str, criteria: str
    ) -> fabll._ChildField[Any]:
        """Create a has_requirement trait with the given parameters."""
        out = fabll._ChildField(cls)
        # Store discriminator so trait_from_field can generate a unique
        # identifier when multiple has_requirement traits are on one module.
        out._trait_discriminator = id  # type: ignore[attr-defined]
        out.add_dependant(F.Literals.Strings.MakeChild_SetSuperset([out, cls.id_], id))
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.text_], text)
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.criteria_], criteria)
        )
        return out
