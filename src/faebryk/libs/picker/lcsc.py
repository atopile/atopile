# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path

from easyeda2kicad.easyeda.easyeda_api import EasyedaApi
from easyeda2kicad.easyeda.easyeda_importer import (
    Easyeda3dModelImporter,
    EasyedaFootprintImporter,
    EasyedaSymbolImporter,
)
from easyeda2kicad.easyeda.parameters_easyeda import EeSymbol
from easyeda2kicad.kicad.export_kicad_3d_model import Exporter3dModelKicad
from easyeda2kicad.kicad.export_kicad_footprint import ExporterFootprintKicad
from easyeda2kicad.kicad.export_kicad_symbol import ExporterSymbolKicad, KicadVersion

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.picker.picker import (
    Part,
    PickerOption,
    Supplier,
)
from faebryk.libs.util import ConfigFlag

logger = logging.getLogger(__name__)

CRAWL_DATASHEET = ConfigFlag(
    "LCSC_DATASHEET", default=False, descr="Crawl for datasheet on LCSC"
)

# TODO dont hardcode relative paths
BUILD_FOLDER = Path("./build")
LIB_FOLDER = Path("./src/kicad/libs")
KICAD_PROJECT_PATH: Path | None = None
MODEL_PATH: str | None = None

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
    if ki_footprint.output.model_3d is None:
        return

    if WORKAROUND_SMD_3D_MODEL_FIX:
        if ki_footprint.input.info.fp_type == "smd":
            ki_footprint.output.model_3d.translation.x = 0
            ki_footprint.output.model_3d.translation.y = 0
    if WORKAROUND_THT_INCH_MM_SWAP_FIX:
        if ki_footprint.input.info.fp_type != "smd":
            ki_footprint.output.model_3d.translation.x *= 2.54
            ki_footprint.output.model_3d.translation.y *= 2.54


def cache_base_path():
    return BUILD_FOLDER / Path("cache/easyeda")


class LCSCException(Exception):
    def __init__(self, partno: str, *args: object) -> None:
        self.partno = partno
        super().__init__(*args)

    def __str__(self) -> str:
        return f"{type(self).__name__}: {self.partno} - {self.args}"


class LCSC_NoDataException(LCSCException): ...


class LCSC_PinmapException(LCSCException): ...


def get_raw(lcsc_id: str):
    api = EasyedaApi()

    cache_base = cache_base_path()
    cache_base.mkdir(parents=True, exist_ok=True)

    comp_path = cache_base.joinpath(lcsc_id)
    if not comp_path.exists():
        logger.debug(f"Did not find component {lcsc_id} in cache, downloading...")
        cad_data = api.get_cad_data_of_component(lcsc_id=lcsc_id)
        serialized = json.dumps(cad_data)
        comp_path.write_text(serialized)

    data = json.loads(comp_path.read_text())

    # API returned no data
    if not data:
        raise LCSC_NoDataException(
            lcsc_id, f"Failed to fetch data from EasyEDA API for part {lcsc_id}"
        )

    return data


def download_easyeda_info(lcsc_id: str, get_model: bool = True):
    # easyeda api access & caching --------------------------------------------
    data = get_raw(lcsc_id)

    easyeda_footprint = EasyedaFootprintImporter(
        easyeda_cp_cad_data=data
    ).get_footprint()

    easyeda_symbol = EasyedaSymbolImporter(easyeda_cp_cad_data=data).get_symbol()

    # paths -------------------------------------------------------------------
    name = easyeda_footprint.info.name
    out_base_path = LIB_FOLDER
    fp_base_path = out_base_path / "footprints" / "lcsc.pretty"
    sym_base_path = out_base_path / "lcsc.kicad_sym"
    fp_base_path.mkdir(exist_ok=True, parents=True)
    footprint_filename = f"{name}.kicad_mod"
    footprint_filepath = fp_base_path.joinpath(footprint_filename)

    # The base_path has to be split from the full path, because the exporter
    # will append .3dshapes to it
    model_base_path = out_base_path / "3dmodels" / "lcsc"
    model_base_path_full = model_base_path.with_suffix(".3dshapes")
    model_base_path_full.mkdir(exist_ok=True, parents=True)

    # export to kicad ---------------------------------------------------------
    ki_footprint = ExporterFootprintKicad(easyeda_footprint)
    ki_symbol = ExporterSymbolKicad(easyeda_symbol, KicadVersion.v6)

    _fix_3d_model_offsets(ki_footprint)

    easyeda_model = Easyeda3dModelImporter(
        easyeda_cp_cad_data=data, download_raw_3d_model=False
    ).output

    ki_model = None
    if easyeda_model:
        ki_model = Exporter3dModelKicad(easyeda_model)

    if easyeda_model is not None:
        model_path = model_base_path_full / f"{easyeda_model.name}.wrl"
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
    elif get_model:
        logger.warning(f"No 3D model for '{name}'")

    if not footprint_filepath.exists():
        logger.debug(f"Exporting footprint {footprint_filepath}")
        kicad_model_path = (
            f"{MODEL_PATH}/3dmodels/lcsc.3dshapes"
            if MODEL_PATH
            else str(
                "${KIPRJMOD}"
                / model_base_path_full.relative_to(KICAD_PROJECT_PATH, walk_up=True)
            )
            if KICAD_PROJECT_PATH
            else str(model_base_path_full.resolve())
        )
        ki_footprint.export(
            footprint_full_path=str(footprint_filepath),
            model_3d_path=kicad_model_path,
        )

    if not sym_base_path.exists():
        logger.debug(f"Exporting symbol {sym_base_path}")
        ki_symbol.export(str(sym_base_path))

    return ki_footprint, ki_model, easyeda_footprint, easyeda_model, easyeda_symbol


def get_datasheet_url(part: EeSymbol):
    # TODO use easyeda2kicad api as soon as works again
    # return part.info.datasheet

    if not CRAWL_DATASHEET:
        return None

    import re

    import requests

    url = part.info.datasheet
    if not url:
        return None
    # make requests act like curl
    lcsc_site = requests.get(url, headers={"User-Agent": "curl/7.81.0"})
    lcsc_id = part.info.lcsc_id
    # find _{partno}.pdf in html
    match = re.search(f'href="(https://[^"]+_{lcsc_id}.pdf)"', lcsc_site.text)
    if match:
        pdfurl = match.group(1)
        logger.debug(f"Found datasheet for {lcsc_id} at {pdfurl}")
        return pdfurl
    else:
        return None


def check_attachable(component: Module):
    if not component.has_trait(F.has_footprint):
        if not component.has_trait(F.can_attach_to_footprint):
            if not component.has_trait(F.has_pin_association_heuristic):
                raise LCSC_PinmapException(
                    "",
                    f"Need either F.can_attach_to_footprint or "
                    "F.has_pin_association_heuristic"
                    f" for {component}",
                )


def attach(
    component: Module, partno: str, get_model: bool = True, check_only: bool = False
):
    try:
        _, _, easyeda_footprint, _, easyeda_symbol = download_easyeda_info(
            partno, get_model=get_model
        )
    except LCSC_NoDataException:
        if component.has_trait(F.has_footprint):
            easyeda_symbol = None
            easyeda_footprint = None
        else:
            raise

    # TODO maybe check the symbol matches, even if a footprint is already attached?
    if not component.has_trait(F.has_footprint):
        assert easyeda_symbol is not None
        assert easyeda_footprint is not None
        if not component.has_trait(F.can_attach_to_footprint):
            # TODO make this a trait
            pins = [
                (pin.settings.spice_pin_number, pin.name.text)
                for unit in easyeda_symbol.units
                for pin in unit.pins
            ]
            try:
                pinmap = component.get_trait(F.has_pin_association_heuristic).get_pins(
                    pins
                )
            except F.has_pin_association_heuristic.PinMatchException as e:
                raise LCSC_PinmapException(partno, f"Failed to get pinmap: {e}") from e

            if check_only:
                return

            component.add(F.can_attach_to_footprint_via_pinmap(pinmap))

            sym = F.Symbol.with_component(component, pinmap)
            sym.add(F.Symbol.has_kicad_symbol(f"lcsc:{easyeda_footprint.info.name}"))

        if check_only:
            return

        # footprint
        fp = F.KicadFootprint(
            f"lcsc:{easyeda_footprint.info.name}",
            [p.number for p in easyeda_footprint.pads],
        )
        component.get_trait(F.can_attach_to_footprint).attach(fp)

    if check_only:
        return

    component.add(F.has_descriptive_properties_defined({"LCSC": partno}))

    if easyeda_symbol is not None:
        datasheet = get_datasheet_url(easyeda_symbol)
        if datasheet:
            component.add(F.has_datasheet_defined(datasheet))

    # model done by kicad (in fp)


class LCSC(Supplier):
    def attach(self, module: Module, part: PickerOption):
        assert isinstance(part.part, LCSC_Part)
        attach(component=module, partno=part.part.partno)
        if part.info is not None:
            module.add(F.has_descriptive_properties_defined(part.info))


class LCSC_Part(Part):
    def __init__(self, partno: str) -> None:
        super().__init__(partno=partno, supplier=LCSC())
