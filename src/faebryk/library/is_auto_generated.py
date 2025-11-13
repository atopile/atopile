# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.checksum import Checksum


class _FileManuallyModified(Exception): ...


class is_auto_generated(fabll.Node):
    CHECKSUM_PLACEHOLDER = "{IS_AUTO_GENERATED_CHECKSUM}"

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    source_ = fabll._ChildField(F.Parameters.StringParameter)
    system_ = fabll._ChildField(F.Parameters.StringParameter)
    date_ = fabll._ChildField(F.Parameters.StringParameter)
    checksum_ = fabll._ChildField(F.Parameters.StringParameter)

    @property
    def source(self) -> str | None:
        literal = self.source_.get().try_extract_constrained_literal()
        return None if literal is None else str(literal)

    @property
    def system(self) -> str | None:
        literal = self.system_.get().try_extract_constrained_literal()
        return None if literal is None else str(literal)

    @property
    def date(self) -> str | None:
        literal = self.date_.get().try_extract_constrained_literal()
        return None if literal is None else str(literal)

    @property
    def checksum(self) -> str | None:
        literal = self.checksum_.get().try_extract_constrained_literal()
        return None if literal is None else str(literal)

    @staticmethod
    def verify(stated_checksum: str, file_contents: str):
        with_placeholder = file_contents.replace(
            stated_checksum, is_auto_generated.CHECKSUM_PLACEHOLDER
        )
        try:
            Checksum.verify(stated_checksum, with_placeholder)
        except Checksum.Mismatch as e:
            raise _FileManuallyModified("File has been manually modified") from e

    @staticmethod
    def set_checksum(file_contents: str) -> str:
        actual = Checksum.build(file_contents)
        return file_contents.replace(is_auto_generated.CHECKSUM_PLACEHOLDER, actual)

    @classmethod
    def MakeChild(
        cls,
        source: str | None = None,
        system: str | None = None,
        date: str | None = None,
        checksum: str | None = None,
    ) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        if source is not None:
            out.add_dependant(
                F.Expressions.Is.MakeChild_ConstrainToLiteral(
                    [out, cls.source_], source
                )
            )
        if system is not None:
            out.add_dependant(
                F.Expressions.Is.MakeChild_ConstrainToLiteral(
                    [out, cls.system_], system
                )
            )
        if date is not None:
            out.add_dependant(
                F.Expressions.Is.MakeChild_ConstrainToLiteral([out, cls.date_], date)
            )
        if checksum is not None:
            out.add_dependant(
                F.Expressions.Is.MakeChild_ConstrainToLiteral(
                    [out, cls.checksum_], checksum
                )
            )
        return out
