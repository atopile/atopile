# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.module import Module
from faebryk.libs.checksum import Checksum


class _FileManuallyModified(Exception): ...


class is_auto_generated(Module.TraitT.decless()):
    CHECKSUM_PLACEHOLDER = "{IS_AUTO_GENERATED_CHECKSUM}"

    def __init__(
        self,
        source: str | None = None,
        system: str | None = None,
        date: str | None = None,
        checksum: str | None = None,
    ) -> None:
        super().__init__()
        self._source = source
        self._system = system
        self._date = date
        self._checksum = checksum
        """
        checksum is the sha256 hash of the file where the checksum string is:
          '{CHECKSUM}'
        """

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
