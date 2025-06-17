# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest

import pytest

import faebryk.libs.picker.lcsc as lcsc

"""
This mode is for when you want to check the models in kicad.
This is especially useful while reverse engineering the easyeda translations.
"""
INTERACTIVE_TESTING = False


@pytest.mark.usefixtures("setup_project_config")
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

        # if not INTERACTIVE_TESTING:
        #    lcsc.BUILD_FOLDER = Path(mkdtemp())

        for partid, expected in test_parts.items():
            part = lcsc.download_easyeda_info(
                partid,
                get_model=INTERACTIVE_TESTING,
            )

            translation = part.footprint.footprint.footprint.models[0].offset.xyz

            self.assertEqual(
                (translation.x, translation.y, translation.z), expected, f"{partid}"
            )
