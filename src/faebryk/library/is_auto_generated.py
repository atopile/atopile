# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from hashlib import sha256

from faebryk.core.module import Module


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
    def _checksum_algo(to_hash: str) -> str:
        return sha256(to_hash.encode("utf-8")).hexdigest()

    @staticmethod
    def verify(stated_checksum: str, file_contents: str):
        actual_checksum = is_auto_generated._checksum_algo(
            file_contents.replace(
                stated_checksum, is_auto_generated.CHECKSUM_PLACEHOLDER
            )
        )

        if actual_checksum != stated_checksum:
            raise _FileManuallyModified(
                f"Checksum mismatch {actual_checksum} != {stated_checksum}"
            )

    @staticmethod
    def set_checksum(file_contents: str) -> str:
        actual = is_auto_generated._checksum_algo(file_contents)
        return file_contents.replace(is_auto_generated.CHECKSUM_PLACEHOLDER, actual)
