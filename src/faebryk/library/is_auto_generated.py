# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.checksum import Checksum


class _FileManuallyModified(Exception): ...


class is_auto_generated(fabll.Node):
    CHECKSUM_PLACEHOLDER = "{IS_AUTO_GENERATED_CHECKSUM}"

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    source_ = fabll._ChildField(F.Parameters.StringParameter)
    system_ = fabll._ChildField(F.Parameters.StringParameter)
    date_ = fabll._ChildField(F.Parameters.StringParameter)
    checksum_ = fabll._ChildField(F.Parameters.StringParameter)

    @property
    def source(self) -> str | None:
        return self.source_.get().try_extract_singleton()

    @property
    def system(self) -> str | None:
        return self.system_.get().try_extract_singleton()

    @property
    def date(self) -> str | None:
        return self.date_.get().try_extract_singleton()

    @property
    def checksum(self) -> str | None:
        return self.checksum_.get().try_extract_singleton()

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
                F.Literals.Strings.MakeChild_SetSuperset([out, cls.source_], source)
            )
        if system is not None:
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset([out, cls.system_], system)
            )
        if date is not None:
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset([out, cls.date_], date)
            )
        if checksum is not None:
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset([out, cls.checksum_], checksum)
            )
        return out

    def setup(
        self,
        source: str | None = None,
        system: str | None = None,
        date: str | None = None,
        checksum: str | None = None,
    ) -> Self:
        if source is not None:
            self.source_.get().set_singleton(source)
        if system is not None:
            self.system_.get().set_singleton(system)
        if date is not None:
            self.date_.get().set_singleton(date)
        if checksum is not None:
            self.checksum_.get().set_singleton(checksum)
        return self
