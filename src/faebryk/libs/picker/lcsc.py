# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path

from easyeda2kicad.easyeda.easyeda_api import EasyedaApi
from easyeda2kicad.easyeda.easyeda_importer import (
    Easyeda3dModelImporter,
    EasyedaFootprintImporter,
)
from easyeda2kicad.kicad.export_kicad_3d_model import Exporter3dModelKicad
from easyeda2kicad.kicad.export_kicad_footprint import ExporterFootprintKicad
from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint import can_attach_to_footprint
from faebryk.library.has_defined_descriptive_properties import (
    has_defined_descriptive_properties,
)
from faebryk.library.KicadFootprint import KicadFootprint
from faebryk.libs.picker.picker import (
    Part,
    PickerOption,
    Supplier,
)

logger = logging.getLogger(__name__)

# TODO dont hardcode relative paths
BUILD_FOLDER = Path("./build")
LIB_FOLDER = Path("./src/kicad/libs")
MODEL_PATH: str | None = "${KIPRJMOD}/../libs/"

EXPORT_NON_EXISTING_MODELS = False

"""
easyeda2kicad has not figured out 100% yet how to do model translations.
It's unfortunately also not really easy.
A lot of SMD components (especially passives, ICs, etc) seem to be doing just fine with
an x,y translation of 0. However that makes some other SMD components behave even worse.
Since in a typical design most components are passives etc, this workaround can save
a lot of time and manual work.
"""
WORKAROUND_SMD_3D_MODEL_FIX = True

"""
Some THT models seem to be fixed when assuming their translation is mm instead of inch.
Does not really make a lot of sense.
"""
WORKAROUND_THT_INCH_MM_SWAP_FIX = False


def _fix_3d_model_offsets(ki_footprint):
    if WORKAROUND_SMD_3D_MODEL_FIX:
        if ki_footprint.input.info.fp_type == "smd":
            ki_footprint.output.model_3d.translation.x = 0
            ki_footprint.output.model_3d.translation.y = 0
    if WORKAROUND_THT_INCH_MM_SWAP_FIX:
        if ki_footprint.input.info.fp_type != "smd":
            ki_footprint.output.model_3d.translation.x *= 2.54
            ki_footprint.output.model_3d.translation.y *= 2.54


def download_easyeda_info(partno: str, get_model: bool = True):
    # easyeda api access & caching --------------------------------------------
    api = EasyedaApi()

    cache_base = BUILD_FOLDER / Path("cache/easyeda")
    cache_base.mkdir(parents=True, exist_ok=True)

    comp_path = cache_base.joinpath(partno)
    if not comp_path.exists():
        logger.debug(f"Did not find component {partno} in cache, downloading...")
        cad_data = api.get_cad_data_of_component(lcsc_id=partno)
        serialized = json.dumps(cad_data)
        comp_path.write_text(serialized)

    data = json.loads(comp_path.read_text())

    # API returned no data
    if not data:
        raise Exception(f"Failed to fetch data from EasyEDA API for part {partno}")

    easyeda_footprint = EasyedaFootprintImporter(
        easyeda_cp_cad_data=data
    ).get_footprint()

    # paths -------------------------------------------------------------------
    name = easyeda_footprint.info.name
    out_base_path = LIB_FOLDER
    fp_base_path = out_base_path.joinpath("footprints/lcsc.pretty")
    fp_base_path.mkdir(exist_ok=True, parents=True)
    footprint_filename = f"{name}.kicad_mod"
    footprint_filepath = fp_base_path.joinpath(footprint_filename)

    model_base_path = out_base_path.joinpath("3dmodels/lcsc")
    model_base_path_full = Path(model_base_path.as_posix() + ".3dshapes")
    model_base_path_full.mkdir(exist_ok=True, parents=True)

    # export to kicad ---------------------------------------------------------
    ki_footprint = ExporterFootprintKicad(easyeda_footprint)

    _fix_3d_model_offsets(ki_footprint)

    easyeda_model = Easyeda3dModelImporter(
        easyeda_cp_cad_data=data, download_raw_3d_model=False
    ).output

    ki_model = None
    if easyeda_model:
        ki_model = Exporter3dModelKicad(easyeda_model)

    if easyeda_model is not None:
        model_path = model_base_path_full.joinpath(f"{easyeda_model.name}.wrl")
        if get_model and not model_path.exists():
            logger.debug(f"Downloading & Exporting 3dmodel {model_path}")
            easyeda_model = Easyeda3dModelImporter(
                easyeda_cp_cad_data=data, download_raw_3d_model=True
            ).output
            assert easyeda_model is not None
            ki_model = Exporter3dModelKicad(easyeda_model)
            ki_model.export(str(model_base_path))

        if not model_path.exists() and not EXPORT_NON_EXISTING_MODELS:
            ki_footprint.output.model_3d = None
    else:
        logger.warn(f"No 3D model for {name}")

    if not footprint_filepath.exists():
        logger.debug(f"Exporting footprint {footprint_filepath}")
        kicad_model_path = (
            f"{MODEL_PATH}/3dmodels/lcsc.3dshapes"
            if MODEL_PATH
            else str(model_base_path_full.resolve())
        )
        ki_footprint.export(
            footprint_full_path=str(footprint_filepath),
            model_3d_path=kicad_model_path,
        )

    return ki_footprint, ki_model, easyeda_footprint, easyeda_model


def get_footprint(partno: str, get_model: bool = True):
    _, _, easyeda_footprint, _ = download_easyeda_info(
        partno=partno, get_model=get_model
    )

    # add trait to component ---------------------------------------------------
    fp = KicadFootprint(
        f"lcsc:{easyeda_footprint.info.name}",
        [p.number for p in easyeda_footprint.pads],
    )

    return fp


def attach_footprint_manually(component: Module, fp: KicadFootprint, partno: str):
    has_defined_descriptive_properties.add_properties_to(component, {"LCSC": partno})
    component.get_trait(can_attach_to_footprint).attach(fp)


def attach_footprint(component: Module, partno: str, get_model: bool = True):
    fp = get_footprint(partno, get_model)
    attach_footprint_manually(component, fp, partno)


class LCSC(Supplier):
    def attach(self, module: Module, part: PickerOption):
        assert isinstance(part.part, LCSC_Part)
        attach_footprint(component=module, partno=part.part.partno)
        if part.info is not None:
            has_defined_descriptive_properties.add_properties_to(module, part.info)


class LCSC_Part(Part):
    def __init__(self, partno: str) -> None:
        super().__init__(partno=partno, supplier=LCSC())
