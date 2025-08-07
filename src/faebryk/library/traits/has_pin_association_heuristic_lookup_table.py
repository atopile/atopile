# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.libs.util import KeyErrorNotFound

logger = logging.getLogger(__name__)


class has_pin_association_heuristic_lookup_table(
    F.has_pin_association_heuristic.impl()
):
    def __init__(
        self,
        mapping: dict[F.Electrical, list[str]],
        accept_prefix: bool,
        case_sensitive: bool,
        nc: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.mapping = mapping
        self.accept_prefix = accept_prefix
        self.case_sensitive = case_sensitive
        self.nc = nc or ["NC", "nc"]

    def get_pins(
        self,
        pins: list[tuple[str, str]],
    ) -> dict[str, F.Electrical]:
        """
        Get the pinmapping for a list of pins based on a lookup table.

        :param pins: A list of tuples with the pin number and name.
        :return: A dictionary with the pin name as key and the module interface as value
        """

        pinmap = {}
        for mif, alt_names in self.mapping.items():
            matches = []
            for number, name in pins:
                if name in self.nc:
                    continue
                for alt_name in alt_names:
                    if not self.case_sensitive:
                        alt_name = alt_name.lower()
                        name = name.lower()
                    if self.accept_prefix and name.endswith(alt_name):
                        matches.append((number, name))
                        break
                    elif name == alt_name:
                        matches.append((number, name))
                        break
            if not matches:
                try:
                    _, is_optional = mif.get_parent_with_trait(F.is_optional)
                    if not is_optional.is_needed():
                        is_optional._handle_result(False)
                        continue
                except KeyErrorNotFound:
                    pass
                raise F.has_pin_association_heuristic.PinMatchException(
                    f"Could not find a match for pin {mif} with names '{alt_names}'"
                    f" in the pins: {pins}"
                )
            for number, name in matches:
                pinmap[number] = mif
                logger.debug(
                    f"Matched pin {number} with name {name} to {mif} with "
                    f"alias {alt_names}"
                )

        unmatched = [p for p in pins if p[0] not in pinmap and p[1] not in self.nc]
        if unmatched:
            logger.warning(
                f"Unmatched pins: {unmatched}, all pins: {pins},"
                f" mapping: {self.mapping}"
            )
        return pinmap
