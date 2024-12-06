# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import atexit
import shutil
import unittest
from pathlib import Path
from tempfile import mkdtemp

import faebryk.libs.picker.lcsc as lcsc

"""
This mode is for when you want to check the models in kicad.
This is especially useful while reverse engineering the easyeda translations.
"""
INTERACTIVE_TESTING = False


class TestLCSC(unittest.TestCase):
    def test_model_translations(self):
        test_parts = {
            # Zero SMD
            "C1525": (0, 0, 0),
            "C2827654": (0, 0, 0),
            "C284656": (0, 0, 0),
            "C668207": (0, 0, 0),
            "C914087": (0, 0, 0),
            "C25076": (0, 0, 0),
            "C328302": (0, 0, 0),
            "C72041": (0, 0, 0),
            "C99652": (0, 0, 0),
            "C72038": (0, 0, 0),
            "C25111": (0, 0, 0),
            "C2290": (0, 0, 0),
            # Non-zero SMD
            # "C585890": (0, -3.5, 0), # TODO enable
            # "C2828092": (0, -9.4, -0.254),  # TODO enable
            # THT
            # "C5239862": (-2.159, 0, 0), #TODO enable
            # "C225521": (-6.3, 1.3, 0),  # TODO enable
        }

        if not INTERACTIVE_TESTING:
            lcsc.BUILD_FOLDER = Path(mkdtemp())
            atexit.register(lambda: shutil.rmtree(lcsc.BUILD_FOLDER))

        lcsc.LIB_FOLDER = lcsc.BUILD_FOLDER / Path("kicad/libs")
        lcsc.MODEL_PATH = None
        lcsc.EXPORT_NON_EXISTING_MODELS = True

        for part, expected in test_parts.items():
            ki_footprint, ki_model, ee_footprint, ee_model, ee_symbol = (
                lcsc.download_easyeda_info(
                    part,
                    get_model=INTERACTIVE_TESTING,
                )
            )

            translation = ki_footprint.output.model_3d.translation

            self.assertEqual(
                (translation.x, translation.y, translation.z), expected, f"{part}"
            )
