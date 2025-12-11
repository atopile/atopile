# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
import unittest
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest
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

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.config import config as Gcfg
from faebryk.libs.kicad.fileformats import kicad
from faebryk.libs.picker.localpick import PickerOption
from faebryk.libs.picker.picker import PickedPart, PickSupplier
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

    def __init__(self, footprint: kicad.footprint.FootprintFile):
        self.footprint = footprint

    def serialize(self) -> bytes:
        return kicad.dumps(self.footprint).encode("utf-8")

    @classmethod
    def load(cls, path: Path):
        # assume not disk modifications during run
        if path in cls.cache:
            return cls.cache[path]
        out = cls(kicad.loads(kicad.footprint.FootprintFile, path))
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
        fp = kicad.loads(kicad.footprint_v5.FootprintFile, fp_raw.decode("utf-8"))
        # workaround: remove wrl ending easyeda likes to add for no reason
        if m := fp.footprint.model:
            if Path(m.path).suffix == ".wrl":
                m.path = Path(m.path).parent.as_posix()

        new_fp = kicad.convert(fp)
        return cls(new_fp)

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
        return kicad.compare_without_uuid(
            self.footprint,
            other.footprint,
        )


class EasyEDASymbol:
    cache: dict[Path, "EasyEDASymbol"] = {}

    def __init__(self, symbol: kicad.symbol.SymbolFile):
        self.symbol = symbol

    @classmethod
    def from_api(cls, symbol: EeSymbol):
        exporter = ExporterSymbolKicad(symbol, KicadVersion.v6)
        # TODO this is weird
        fp_lib_name = symbol.info.lcsc_id
        raw = exporter.export(footprint_lib_name=fp_lib_name)
        in_file = f"""(kicad_sym
            (version 20211014)
            (generator "test")
            {raw}
        )""".replace("hide", "")
        sym = kicad.loads(kicad.symbol_v6.SymbolFile, in_file)
        new_sym = kicad.convert(sym)

        return cls(new_sym)

    def serialize(self) -> bytes:
        return kicad.dumps(self.symbol).encode("utf-8")

    def dump(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.serialize())
        type(self).cache[path] = self

    @classmethod
    def load(cls, path: Path):
        # assume not disk modifications during run
        if path in cls.cache:
            return cls.cache[path]
        out = cls(kicad.loads(kicad.symbol.SymbolFile, path))
        cls.cache[path] = out
        return out

    def compare(self, other: "EasyEDASymbol"):
        return kicad.compare_without_uuid(
            self.symbol,
            other.symbol,
        )

    @property
    def kicad_symbol(self):
        return first(self.symbol.kicad_sym.symbols)


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

        from faebryk.libs.http import http_client

        logger.debug(f"Crawling datasheet for {identifier}")

        with http_client(
            headers={"User-Agent": "curl/7.81.0"},  # emulate curl
            verify=not Gcfg.project.dangerously_skip_ssl_verification,
        ) as client:
            lcsc_site = client.get(url)

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


def check_attachable(component: fabll.Node):
    if not component.has_trait(F.Footprints.has_associated_footprint):
        if not component.has_trait(F.Footprints.can_attach_to_footprint):
            if not component.has_trait(F.has_pin_association_heuristic):
                raise LCSC_PinmapException(
                    "",
                    f"Need either F.can_attach_to_footprint or "
                    "F.has_pin_association_heuristic"
                    f" for {component}",
                )


def attach(
    component_with_fp: F.Footprints.can_attach_to_footprint,
    partno: str,
    get_3d_model: bool = True,
    check_only: bool = False,
):
    """
    Download the EasyEDA part and try to attach it to the component.
    """
    from faebryk.libs.part_lifecycle import PartIsNotAutoGenerated, PartLifecycle

    # TODO fix this later on
    # for now, we always get the 3d model
    # related to #1265
    get_3d_model = True

    lifecycle = PartLifecycle.singleton()
    try:
        epart = download_easyeda_info(partno, get_model=get_3d_model)
    except LCSC_NoDataException:
        if component_with_fp.has_trait(F.Footprints.has_associated_footprint):
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

    assert apart is not None

    pads_number_name_pairs = [
        (pin.number.number, pin.name.name)
        for sym in apart.symbol.kicad_sym.symbols
        for unit in sym.symbols
        for pin in unit.pins
        if pin.number is not None
    ]
    # create temp pads from the atopart pad names and numbers to check if their
    # names match the lead names
    tmp_pads = [
        fabll.Traits.create_and_add_instance_to(
            node=fabll.Node.bind_typegraph(tg=component_with_fp.tg).create_instance(
                g=component_with_fp.instance.g()
            ),
            trait=F.Footprints.is_pad,
        ).setup(pad_number=number, pad_name=name)
        for number, name in pads_number_name_pairs
    ]

    leads_t = F.Lead.is_lead.bind_typegraph(component_with_fp.tg).get_instances()

    # try matching the ato part pad names to the component's leads
    try:
        for lead_t in leads_t:
            matched_pad = lead_t.find_matching_pad(tmp_pads)
    except F.Lead.PadMatchException as e:
        raise LCSC_PinmapException(partno, f"Failed to get pinmap: {e}") from e

    if check_only:
        # don't attach or create any footprint related things if we're only checking
        # if the pad-lead combo's are valid
        component_node = fabll.Traits(component_with_fp).get_obj_raw()
        logger.debug(f"Checking pinmap for {partno} -> {component_node.get_name()}")
        return

    if not component_with_fp.has_trait(F.Footprints.has_associated_footprint):
        # we need to create and add a footprint node to the component if it
        # doesn't exist yet
        fp = F.Footprints.GenericFootprint.bind_typegraph_from_instance(
            instance=component_with_fp.instance
        ).create_instance(g=component_with_fp.instance.g())
        fp.setup(tmp_pads)

        component_node = fabll.Traits(component_with_fp).get_obj_raw()
        fabll.Traits.create_and_add_instance_to(
            node=component_node, trait=F.Footprints.has_associated_footprint
        ).setup(fp.is_footprint.get())

        pads_t = fp.get_pads()
        try:
            # only attach to leads that don't have associated pads yet
            for lead_t in [
                lt for lt in leads_t if not lt.has_trait(F.Lead.has_associated_pads)
            ]:
                matched_pad = lead_t.find_matching_pad(pads_t)
                fabll.Traits.create_and_add_instance_to(
                    node=lead_t, trait=F.Lead.has_associated_pads
                ).setup(pad=matched_pad, parent=lead_t)
        except F.Lead.PadMatchException as e:
            raise LCSC_PinmapException(partno, f"Failed to get pinmap: {e}") from e

    # link footprint to the component
    footprint = component_node.get_trait(
        F.Footprints.has_associated_footprint
    ).get_footprint()

    if not footprint.has_trait(
        F.KiCadFootprints.has_associated_kicad_library_footprint
    ):
        # link the kicad library footprint to the fabll footprint
        fabll.Traits.create_and_add_instance_to(
            node=footprint,
            trait=F.KiCadFootprints.has_associated_kicad_library_footprint,
        ).setup(
            library_name=apart.path.name,
            kicad_footprint_file_path=str(apart.fp_path),
        )
    logger.debug(f"Attached {partno} to -> {component_node.get_name()}")

    # 3D model done by kicad (in fp)


class PickSupplierLCSC(PickSupplier):
    supplier_id: str = "lcsc"

    def attach(self, module: fabll.Node, part: PickerOption):
        assert isinstance(part.part, PickedPartLCSC)
        module_with_fp = module.get_trait(F.Footprints.can_attach_to_footprint)
        attach(component_with_fp=module_with_fp, partno=part.part.lcsc_id)

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


# TODO: move to global fixtures, or put into the specific test
@pytest.fixture()
def setup_project_config(tmp_path):
    from atopile.config import ProjectConfig, ProjectPaths, config

    config.project = ProjectConfig.skeleton(
        entry="", paths=ProjectPaths(build=tmp_path / "build", root=tmp_path)
    )
    yield


@pytest.mark.usefixtures("setup_project_config")
def test_attach_resistor(capsys):
    import faebryk.core.faebrykpy as fbrk
    import faebryk.core.node as fabll

    LCSC_ID = "C21190"

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    component = F.Resistor.bind_typegraph(tg=tg).create_instance(g=g)

    # Before attach: no kicad footprint should be linked yet
    associated_footprint = component.try_get_trait(
        F.Footprints.has_associated_footprint
    )

    assert associated_footprint is None

    with capsys.disabled():
        print(
            fabll.graph.InstanceGraphFunctions.render(
                component.instance, show_traits=True, show_pointers=True
            )
        )
    component_with_fp = component.get_trait(F.Footprints.can_attach_to_footprint)
    attach(component_with_fp=component_with_fp, partno=LCSC_ID)

    associated_footprint = component.try_get_trait(
        F.Footprints.has_associated_footprint
    )

    assert associated_footprint is not None

    # After attach: footprint should now be linked
    footprint = associated_footprint.get_footprint()

    # there should also be a kicad library footprint linked
    kicad_library_footprint = footprint.try_get_trait(
        F.KiCadFootprints.has_associated_kicad_library_footprint
    )
    assert kicad_library_footprint is not None

    assert kicad_library_footprint.kicad_identifier == "UNI_ROYAL_0603WAF1001T5E:R0603"
    assert kicad_library_footprint.library_name == "UNI_ROYAL_0603WAF1001T5E"
    assert kicad_library_footprint.pad_names == ["2", "1"]
    assert (
        "src/parts/UNI_ROYAL_0603WAF1001T5E/R0603.kicad_mod"
        in kicad_library_footprint.kicad_footprint_file_path
    )


@pytest.mark.usefixtures("setup_project_config")
def test_attach_mosfet():
    import faebryk.core.faebrykpy as fbrk
    import faebryk.core.node as fabll

    LCSC_ID = "C8545"

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    component = F.MOSFET.bind_typegraph(tg=tg).create_instance(g=g)

    component_with_fp = component.get_trait(F.Footprints.can_attach_to_footprint)
    attach(component_with_fp=component_with_fp, partno=LCSC_ID)

    associated_footprint = component.try_get_trait(
        F.Footprints.has_associated_footprint
    )

    assert associated_footprint is not None

    # After attach: footprint should now be linked
    footprint = associated_footprint.get_footprint()
    # TODO: check footrpint pad names assert footrpint.pad_names == ["G", "S", "D"]

    # there should also be a kicad footprint linked
    kicad_library_footprint = footprint.get_trait(
        F.KiCadFootprints.has_associated_kicad_library_footprint
    )

    assert (
        kicad_library_footprint.kicad_identifier
        == "Changjiang_Electronics_Tech_2N7002:SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR"
    )
    assert kicad_library_footprint.library_name == "Changjiang_Electronics_Tech_2N7002"
    assert kicad_library_footprint.pad_names == ["1", "2", "3"]
    assert (
        "src/parts/Changjiang_Electronics_Tech_2N7002/SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR.kicad_mod"
        in kicad_library_footprint.kicad_footprint_file_path
    )


@pytest.mark.usefixtures("setup_project_config")
def test_attach_failure():
    import faebryk.core.faebrykpy as fbrk
    import faebryk.core.node as fabll

    RESISTOR_LCSC_ID = "C21190"
    MOSFET_LCSC_ID = "C8545"

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    component = F.MOSFET.bind_typegraph(tg=tg).create_instance(g=g)

    component_with_fp = component.get_trait(F.Footprints.can_attach_to_footprint)
    with pytest.raises(LCSC_PinmapException):
        attach(
            component_with_fp=component_with_fp,
            partno=RESISTOR_LCSC_ID,
            check_only=True,
        )

    attach(component_with_fp=component_with_fp, partno=MOSFET_LCSC_ID, check_only=False)

    associated_footprint = component.try_get_trait(
        F.Footprints.has_associated_footprint
    )

    assert associated_footprint is not None

    footprint = associated_footprint.get_footprint()

    kicad_library_footprint = footprint.get_trait(
        F.KiCadFootprints.has_associated_kicad_library_footprint
    )
    assert kicad_library_footprint.pad_names == ["1", "2", "3"]


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
            part = download_easyeda_info(
                partid,
                get_model=INTERACTIVE_TESTING,
            )

            translation = part.footprint.footprint.footprint.models[0].offset.xyz

            self.assertEqual(
                (translation.x, translation.y, translation.z), expected, f"{partid}"
            )
