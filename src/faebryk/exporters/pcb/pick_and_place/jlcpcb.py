# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# convert kicad p&p file to jlcpcb p&p file
def convert_kicad_pick_and_place_to_jlcpcb(
    kicad_pick_and_place_file: Path, jlcpcb_pick_and_place_file: Path
) -> None:
    """
    Convert KiCad pick and place file to JLCPCB pick and place file
    """

    logger.info("Converting KiCad p&p file to JLCPCB format")

    # Rename the following in the csv header and copy contents:
    # Ref to Designator PosX to Mid X PosY to Mid Y Rot to Rotation Side to Layer
    with open(kicad_pick_and_place_file, "r", encoding="utf-8") as kicad_pick_and_place:
        with open(
            jlcpcb_pick_and_place_file, "w", encoding="utf-8"
        ) as jlcpcb_pick_and_place:
            for line in kicad_pick_and_place:
                if "Ref,Val,Package,PosX,PosY,Rot,Side" in line:
                    jlcpcb_pick_and_place.write(
                        "Designator,Val,Package,Mid X,Mid Y,Rotation,Layer\n"
                    )
                else:
                    jlcpcb_pick_and_place.write(line)
