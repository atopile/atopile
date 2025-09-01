# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dataclasses_json import (
    CatchAll,
    Undefined,
    dataclass_json,
)
from dataclasses_json import (
    config as dataclasses_json_config,
)
from easyeda2kicad.easyeda.easyeda_api import EasyedaApi
from easyeda2kicad.easyeda.easyeda_importer import (
    EasyedaFootprintImporter,
    EasyedaSymbolImporter,
)
from easyeda2kicad.easyeda.parameters_easyeda import Ee3dModel, EeSymbol, ee_footprint
from easyeda2kicad.kicad.export_kicad_footprint import ExporterFootprintKicad
from easyeda2kicad.kicad.export_kicad_symbol import ExporterSymbolKicad, KicadVersion
from more_itertools import first

import faebryk.library._F as F
from atopile.config import config as Gcfg
from faebryk.core.module import Module
from faebryk.libs.kicad.fileformats_common import compare_without_uuid
from faebryk.libs.kicad.fileformats_latest import C_kicad_footprint_file
from faebryk.libs.kicad.fileformats_sch import C_kicad_sym_file
from faebryk.libs.kicad.fileformats_version import kicad_footprint_file
from faebryk.libs.picker.localpick import PickerOption
from faebryk.libs.picker.picker import (
    PickedPart,
    PickSupplier,
)
from faebryk.libs.util import ConfigFlag, call_with_file_capture, not_none, once

logger = logging.getLogger(__name__)

CRAWL_DATASHEET = ConfigFlag(
    "LCSC_DATASHEET", default=True, descr="Crawl for datasheet on LCSC"
)

WORKAROUND_SMD_3D_MODEL_FIX = True
"""
easyeda2kicad has not figured out 100% yet how to do model translations.
It's unfortunately also not really easy.
A lot of SMD components (especially passives, ICs, etc) seem to be doing just fine with
an x,y translation of 0. However that makes some other SMD components behave even worse.
Since in a typical design most components are passives etc, this workaround can save
a lot of time and manual work.
"""

WORKAROUND_THT_INCH_MM_SWAP_FIX = False
"""
Some THT models seem to be fixed when assuming their translation is mm instead of inch.
Does not really make a lot of sense.
"""


def _decode_easyeda_date(date: str | int | float) -> datetime:
    if isinstance(date, str):
        return datetime.fromisoformat(date)
    return datetime.fromtimestamp(date)


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass
class EasyEDAAPIResponse:
    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class PackageDetail:
        updateTime: int
        unknown: CatchAll = None

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class Lcsc:
        number: str
        unknown: CatchAll = None

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class _Symbol:
        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class Header:
            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class PartInfo:
                manufacturer: str = field(
                    metadata=dataclasses_json_config(field_name="Manufacturer")
                )
                partno: str = field(
                    metadata=dataclasses_json_config(field_name="Manufacturer Part")
                )
                unknown: CatchAll = None

            part_info: PartInfo = field(
                metadata=dataclasses_json_config(field_name="c_para")
            )
            unknown: CatchAll = None

        info: Header = field(metadata=dataclasses_json_config(field_name="head"))
        unknown: CatchAll = None

    packageDetail: PackageDetail
    updated_at: datetime = field(
        metadata=dataclasses_json_config(decoder=_decode_easyeda_date)
    )
    lcsc: Lcsc
    description: str
    symbol: _Symbol = field(metadata=dataclasses_json_config(field_name="dataStr"))

    _atopile_queried_at: float | None = field(
        default=None,
        metadata=dataclasses_json_config(field_name="atopile_queried_at"),
    )
    _atopile_manufacturer: str | None = field(
        default=None,
        metadata=dataclasses_json_config(field_name="atopile_manufacturer"),
    )
    unknown: CatchAll = None

    @property
    def query_time(self) -> datetime:
        return datetime.fromtimestamp(not_none(self._atopile_queried_at))

    @property
    def mfn_pn(self) -> tuple[str, str]:
        pn = self.symbol.info.part_info.partno
        mfr = self._atopile_manufacturer or self.symbol.info.part_info.manufacturer
        if not self._atopile_manufacturer:
            logger.warning(
                f"No manufacturer for ({mfr} {pn}) {self.lcsc.number} found in backend."
            )
        # remove chinese manufacturer name in parentheses
        # "TI(德州仪器)" -> "TI"
        mfr = re.sub(r"\([^)]*\)", "", mfr)
        return (mfr, pn)

    @classmethod
    def from_api_dict(cls, data: dict):
        out: EasyEDAAPIResponse = cls.from_dict(data)  # type: ignore
        out._atopile_queried_at = datetime.timestamp(datetime.now())
        return out

    def serialize(self) -> bytes:
        return self.to_json(indent=4).encode("utf-8")  # type: ignore

    def dump(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.serialize())

    @classmethod
    def deserialize(cls, data: bytes):
        out: cls = cls.from_json(data.decode("utf-8"))  # type: ignore
        if out._atopile_queried_at is None:
            out._atopile_queried_at = datetime.timestamp(out.updated_at)
        return out

    @classmethod
    def load(cls, path: Path):
        return cls.deserialize(path.read_bytes())

    def raw(self) -> dict:
        return self.to_dict()  # type: ignore


class EasyEDA3DModel:
    def __init__(self, step: bytes, name: str):
        self.step = step
        self.name = name

    def serialize(self) -> bytes:
        return self.step

    def dump(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.step)

    @classmethod
    def deserialize(cls, data: bytes, name: str):
        return cls(data, name)

    @classmethod
    def load(cls, path: Path):
        return cls(path.read_bytes(), path.name)


class EasyEDAFootprint:
    cache: dict[Path, "EasyEDAFootprint"] = {}

    def __init__(self, footprint: C_kicad_footprint_file):
        self.footprint = footprint

    def serialize(self) -> bytes:
        return self.footprint.dumps().encode("utf-8")

    @classmethod
    def load(cls, path: Path):
        # assume not disk modifications during run
        if path in cls.cache:
            return cls.cache[path]
        out = cls(kicad_footprint_file(path))
        cls.cache[path] = out
        return out

    @classmethod
    def from_api(cls, footprint: ee_footprint, model_path: str | None):
        exporter = ExporterFootprintKicad(footprint)
        _fix_3d_model_offsets(exporter)
        if model_path is None:
            # allows our ignored type annotation to work below
            assert footprint.model_3d is None

        fp_raw = call_with_file_capture(
            lambda path: exporter.export(str(path), model_path)  # type: ignore
        )[1]
        fp = kicad_footprint_file(fp_raw.decode("utf-8"))
        # workaround: remove wrl ending easyeda likes to add for no reason
        for m in fp.footprint.models:
            if m.path.suffix == ".wrl":
                m.path = m.path.parent
        return cls(fp)

    def dump(self, path: Path):
        type(self).cache[path] = self
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.serialize())

    @property
    def library_name(self):
        return self.footprint.footprint.name

    @property
    def base_name(self):
        return self.library_name.split(":")[-1]

    def compare(self, other: "EasyEDAFootprint"):
        return compare_without_uuid(
            self.footprint,
            other.footprint,
        )


class EasyEDASymbol:
    cache: dict[Path, "EasyEDASymbol"] = {}

    def __init__(self, symbol: C_kicad_sym_file):
        self.symbol = symbol

    @classmethod
    def from_api(cls, symbol: EeSymbol):
        from faebryk.libs.kicad.fileformats_v6 import C_symbol_in_file_v6
        from faebryk.libs.sexp.dataclass_sexp import loads as sexp_loads

        exporter = ExporterSymbolKicad(symbol, KicadVersion.v6)
        # TODO this is weird
        fp_lib_name = symbol.info.lcsc_id
        raw = exporter.export(footprint_lib_name=fp_lib_name)
        sym = sexp_loads(raw, C_symbol_in_file_v6).symbol.convert_to_new()
        sym_file = C_kicad_sym_file(
            C_kicad_sym_file.C_kicad_symbol_lib(
                version=1,
                generator="faebryk",
                symbols={sym.name: sym},
            )
        )
        return cls(sym_file)

    def serialize(self) -> bytes:
        return self.symbol.dumps().encode("utf-8")

    def dump(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.serialize())
        type(self).cache[path] = self

    @classmethod
    def load(cls, path: Path):
        # assume not disk modifications during run
        if path in cls.cache:
            return cls.cache[path]
        out = cls(C_kicad_sym_file.loads(path))
        cls.cache[path] = out
        return out

    def compare(self, other: "EasyEDASymbol"):
        return compare_without_uuid(
            self.symbol,
            other.symbol,
        )

    @property
    def kicad_symbol(self):
        return first(self.symbol.kicad_symbol_lib.symbols.values())


class EasyEDAPart:
    def __init__(
        self,
        lcsc_id: str,
        description: str,
        mfn_pn: tuple[str, str],
        footprint: EasyEDAFootprint,
        symbol: EasyEDASymbol,
        model: EasyEDA3DModel | None = None,
        datasheet_url: str | None = None,
    ):
        self.lcsc_id = lcsc_id
        self.description = description
        self.mfn_pn = mfn_pn
        self.footprint = footprint
        self.symbol = symbol
        self.model = model
        self._pre_model: Ee3dModel | None = None
        self.datasheet_url = datasheet_url
        self._pre_datasheet: str | None = None

    @property
    def identifier(self):
        return self.lcsc_id

    @property
    def model_name(self):
        if self.model:
            return self.model.name
        assert self._pre_model is not None
        return self._pre_model.name

    def load_model(self):
        from faebryk.libs.part_lifecycle import PartLifecycle

        lifecycle = PartLifecycle.singleton()
        assert self.model is None
        assert self._pre_model is not None
        if lifecycle.easyeda2kicad.shall_refresh_model(self):
            logger.debug(f"Downloading model for {self.identifier}")
            model = EasyedaApi().get_step_3d_model(uuid=self._pre_model.uuid)
            # might happen sometimes, that even tho it's in the api, it's not available
            if model is None:
                self.model = None
            else:
                self.model = EasyEDA3DModel(model, self._pre_model.name)
        else:
            self.model = lifecycle.easyeda2kicad.load_model(self)

        self._pre_model = None

    @classmethod
    def from_api_response(cls, data: EasyEDAAPIResponse, download_model: bool):
        """
        args:
            download_model: Purely for performance and api overloading
        """
        from faebryk.libs.part_lifecycle import PartLifecycle

        lifecycle = PartLifecycle.singleton()

        easyeda_footprint = EasyedaFootprintImporter(
            easyeda_cp_cad_data=data.raw()
        ).get_footprint()

        easyeda_symbol = EasyedaSymbolImporter(
            easyeda_cp_cad_data=data.raw()
        ).get_symbol()

        easyeda_model = easyeda_footprint.model_3d

        if easyeda_model is not None:
            model_name = easyeda_model.name
            model_path = lifecycle.easyeda2kicad.get_model_path(
                data.lcsc.number, model_name
            )
            kicad_model_path = str(
                Gcfg.project.get_relative_to_kicad_project(model_path)
            )
        else:
            kicad_model_path = None

        part = cls(
            lcsc_id=data.lcsc.number,
            description=data.description,
            mfn_pn=data.mfn_pn,
            footprint=EasyEDAFootprint.from_api(easyeda_footprint, kicad_model_path),
            symbol=EasyEDASymbol.from_api(easyeda_symbol),
        )
        part._pre_model = easyeda_model
        part._pre_datasheet = easyeda_symbol.info.datasheet

        if download_model and part._pre_model is not None:
            part.load_model()

        if part._pre_datasheet is not None:
            part.load_datasheet()

        return part

    @once
    @staticmethod
    def load_datasheet_for_identifier(
        url: str, identifier: str, lcsc_id: str
    ) -> str | None:
        import re

        import requests

        logger.debug(f"Crawling datasheet for {identifier}")

        # make requests act like curl
        lcsc_site = requests.get(
            url,
            headers={"User-Agent": "curl/7.81.0"},
            verify=not Gcfg.project.dangerously_skip_ssl_verification,
        )
        # find _{partno}.pdf in html
        match = re.search(f'href="(https://[^"]+_{lcsc_id}.pdf)"', lcsc_site.text)
        if match:
            pdfurl = match.group(1)
            logger.debug(f"Found datasheet for {lcsc_id} at {pdfurl}")
            return pdfurl

        return None

    def load_datasheet(self):
        if self.datasheet_url:
            return self.datasheet_url

        # TODO use easyeda2kicad api as soon as works again
        # return symbol.info.datasheet

        if not CRAWL_DATASHEET:
            return None

        if not (url := self._pre_datasheet):
            return None

        if pdfurl := EasyEDAPart.load_datasheet_for_identifier(
            url, self.identifier, self.lcsc_id
        ):
            self.datasheet_url = pdfurl
            return pdfurl

        return None


def _fix_3d_model_offsets(ki_footprint: ExporterFootprintKicad):
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


class LCSCException(Exception):
    def __init__(self, partno: str, *args: object) -> None:
        self.partno = partno
        super().__init__(*args)

    def __str__(self) -> str:
        return f"{type(self).__name__}: {self.partno} - {self.args}"


class LCSC_NoDataException(LCSCException): ...


class LCSC_PinmapException(LCSCException): ...


@once
def get_raw(lcsc_id: str) -> EasyEDAAPIResponse:
    from faebryk.libs.part_lifecycle import PartLifecycle

    lifecycle = PartLifecycle.singleton()
    if not lifecycle.easyeda_api.shall_refresh(lcsc_id):
        return lifecycle.easyeda_api.load(lcsc_id)

    logger.debug(f"Downloading API data {lcsc_id}")
    api = EasyedaApi()
    cad_data = api.get_cad_data_of_component(lcsc_id=lcsc_id)
    # API returned no data
    if not cad_data:
        raise LCSC_NoDataException(
            lcsc_id, f"Failed to fetch data from EasyEDA API for part {lcsc_id}"
        )
    response = EasyEDAAPIResponse.from_api_dict(cad_data)
    # TODO: this is a hack
    # get manufacturer from backend
    from faebryk.libs.picker.api.api import get_api_client

    if api_part := first(
        get_api_client().fetch_part_by_lcsc(int(lcsc_id.removeprefix("C"))), None
    ):
        response._atopile_manufacturer = api_part.manufacturer_name

    return lifecycle.easyeda_api.ingest(lcsc_id, response)


@once
def download_easyeda_info(lcsc_id: str, get_model: bool = True):
    from faebryk.libs.part_lifecycle import PartLifecycle

    lifecycle = PartLifecycle.singleton()

    data = get_raw(lcsc_id)
    part = EasyEDAPart.from_api_response(data, download_model=False)

    if get_model and not part._pre_model:
        logger.warning(f"No 3D model for '{lcsc_id} ({part.footprint.base_name})'")

    if get_model and lifecycle.easyeda2kicad.shall_refresh_model(part):
        part.load_model()

    return lifecycle.easyeda2kicad.ingest_part(part)


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
    from faebryk.libs.part_lifecycle import PartIsNotAutoGenerated, PartLifecycle

    # TODO fix this later on
    # for now, we always get the model
    # related to #1265
    get_model = True

    lifecycle = PartLifecycle.singleton()
    try:
        epart = download_easyeda_info(partno, get_model=get_model)
    except LCSC_NoDataException:
        if component.has_trait(F.has_footprint):
            apart = None
            epart = None
        else:
            raise
    else:
        try:
            apart = lifecycle.library.ingest_part_from_easyeda(epart)
        except PartIsNotAutoGenerated as ex:
            apart = ex.part
            logger.debug(
                f"Part `{ex.part.path}` is not purely auto-generated. Not overwriting."
            )

    # TODO maybe check the symbol matches, even if a footprint is already attached?
    if not component.has_trait(F.has_footprint):
        assert apart is not None
        if not component.has_trait(F.can_attach_to_footprint):
            # TODO make this a trait
            pins = [
                (pin.number.number, pin.name.name)
                for sym in apart.symbol.kicad_symbol_lib.symbols.values()
                for unit in sym.symbols.values()
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
            # FIXME
            sym.add(
                F.Symbol.has_kicad_symbol(f"{apart.identifier}:{apart.sym_path.name}")
            )

        if check_only:
            return

        # footprint
        fp = F.KicadFootprint.from_path(apart.fp_path, lib_name=apart.path.name)
        component.get_trait(F.can_attach_to_footprint).attach(fp)

    if check_only:
        return

    # model done by kicad (in fp)


class PickSupplierLCSC(PickSupplier):
    supplier_id: str = "lcsc"

    def attach(self, module: Module, part: PickerOption):
        assert isinstance(part.part, PickedPartLCSC)
        attach(component=module, partno=part.part.lcsc_id)

    def __str__(self) -> str:
        return f"{type(self).__name__}()"

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other)


@dataclass(frozen=True, kw_only=True)
class PickedPartLCSC(PickedPart):
    @dataclass(frozen=True)
    class Info:
        stock: int
        price: float
        description: str
        basic: bool
        preferred: bool

    info: Info | None = None
    supplier: PickSupplierLCSC = field(default_factory=PickSupplierLCSC)

    @property
    def lcsc_id(self) -> str:
        return self.supplier_partno
