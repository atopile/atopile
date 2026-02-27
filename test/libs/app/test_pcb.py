# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

from faebryk.libs.app.pcb import ensure_board_appearance
from faebryk.libs.kicad.fileformats import kicad
from faebryk.libs.test.fileformats import PCBFILE


def test_ensure_board_appearance_initializes_stackup_thicknesses():
    pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE)
    pcb.kicad_pcb.setup.stackup = None

    ensure_board_appearance(pcb.kicad_pcb)

    stackup = pcb.kicad_pcb.setup.stackup
    assert stackup is not None

    expected_thicknesses = {
        "F.Mask": 0.01,
        "F.Cu": 0.035,
        "dielectric 1": 1.51,
        "B.Cu": 0.035,
        "B.Mask": 0.01,
    }

    layers_by_name = {layer.name: layer for layer in stackup.layers}
    for name, expected in expected_thicknesses.items():
        layer = layers_by_name[name]
        thickness = layer.thickness
        assert thickness is not None
        assert isinstance(thickness, kicad.pcb.Thickness)
        assert thickness.thickness == pytest.approx(expected)


def test_stackup_layer_rejects_float_thickness() -> None:
    with pytest.raises(TypeError, match="Expected kicad.pcb.Thickness"):
        kicad.pcb.StackupLayer(
            name="F.Mask",
            type="Top Solder Mask",
            color="Black",
            thickness=0.01,
            material="Solder mask",
            epsilon_r=3.3,
            loss_tangent=None,
        )
