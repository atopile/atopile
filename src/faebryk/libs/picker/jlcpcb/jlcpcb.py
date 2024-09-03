# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import asyncio
import datetime
import logging
import os
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from textwrap import indent
from typing import Any, Callable, Generator, Self, Sequence

import patoolib
import requests
from rich.progress import track
from tortoise import Tortoise
from tortoise.expressions import Q
from tortoise.fields import CharField, IntField, JSONField
from tortoise.models import Model

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.core.util import pretty_param_tree, pretty_params
from faebryk.libs.e_series import (
    E_SERIES_VALUES,
    ParamNotResolvedError,
    e_series_intersect,
)
from faebryk.libs.picker.lcsc import (
    LCSC_NoDataException,
    LCSC_Part,
    LCSC_PinmapException,
    attach,
)
from faebryk.libs.picker.picker import (
    DescriptiveProperties,
    PickError,
    has_part_picked_defined,
)
from faebryk.libs.units import P, Quantity, UndefinedUnitError, to_si_str
from faebryk.libs.util import at_exit, cast_assert, try_or

logger = logging.getLogger(__name__)

# TODO dont hardcode relative paths
BUILD_FOLDER = Path("./build")
CACHE_FOLDER = BUILD_FOLDER / Path("cache")


class JLCPCB_Part(LCSC_Part):
    def __init__(self, partno: str) -> None:
        super().__init__(partno=partno)


class TBD_ParseError(F.TBD):
    """
    Wrapper for TBD that behaves exactly like TBD for the core and picker
    But gives us the possibility to attach parser errors to it for deferred
    error logging
    """

    def __init__(self, e: Exception, msg: str):
        self.e = e
        self.msg = msg
        super().__init__()

    def __repr__(self):
        return f"{super().__repr__()}({self.msg}: {self.e})"


@dataclass
class MappingParameterDB:
    param_name: str
    attr_keys: list[str]
    attr_tolerance_key: str | None = None
    transform_fn: Callable[[str], Parameter] | None = None
    ignore_at: bool = True


class Category(Model):
    id = IntField(primary_key=True)
    category = CharField(max_length=255)
    subcategory = CharField(max_length=255)

    class Meta:
        table = "categories"

    async def get_ids(
        self, category: str = "", subcategory: str = ""
    ) -> list[dict[str, Any]]:
        """
        Get the category ids for the given category and subcategory

        :param category: The category to search for, use "" for any
        :param subcategory: The subcategory to search for, use "" for any

        :return: A list of category ids for the JLCPCB database Component id field
        """
        filter_query = Q()
        if category != "":
            filter_query &= Q(category__icontains=category)
        if subcategory != "":
            filter_query &= Q(subcategory__icontains=subcategory)
        category_ids = await self.filter(filter_query).values("id")
        if len(category_ids) < 1:
            raise LookupError(
                f"Could not find a match for category {category} "
                f"and subcategory {subcategory}",
            )
        return [c["id"] for c in category_ids]


class Manufacturers(Model):
    id = IntField(primary_key=True)
    name = CharField(max_length=255)

    class Meta:
        table = "manufacturers"

    async def get_ids(self, manufacturer: str) -> list[int]:
        """
        Get the manufacturer ids for the given manufacturer

        :param manufacturer: The manufacturer to search for

        :return: A list of manufacturer ids for the JLCPCB database Component id field
        """
        manufacturer_ids = await self.filter(name__icontains=manufacturer).values("id")
        if len(manufacturer_ids) < 1:
            raise LookupError(f"Could not find a match for manufacturer {manufacturer}")
        return [m["id"] for m in manufacturer_ids]

    async def get_from_id(self, manufacturer_id: int) -> str:
        return (await self.get(id=manufacturer_id)).name


class Component(Model):
    lcsc = IntField(primary_key=True)
    category_id = IntField()
    mfr = CharField(max_length=255)
    package = CharField(max_length=255)
    joints = IntField()
    manufacturer_id = IntField()
    basic = IntField()
    description = CharField(max_length=255)
    datasheet = CharField(max_length=255)
    stock = IntField()
    price = JSONField()
    last_update = IntField()
    extra = JSONField()
    flag = IntField()
    last_on_stock = IntField()
    preferred = IntField()

    class Meta:
        table = "components"

    class ParseError(Exception):
        pass

    @property
    def partno(self):
        return f"C{self.lcsc}"

    def get_price(self, qty: int = 1) -> float:
        """
        Get the price for qty of the component including handling fees

        For handling fees and component price classifications, see:
        https://jlcpcb.com/help/article/pcb-assembly-faqs
        """
        BASIC_HANDLING_FEE = 0
        PREFERRED_HANDLING_FEE = 0
        EXTENDED_HANDLING_FEE = 3

        if qty < 1:
            raise ValueError("Quantity must be greater than 0")

        if self.basic:
            handling_fee = BASIC_HANDLING_FEE
        elif self.preferred:
            handling_fee = PREFERRED_HANDLING_FEE
        else:
            handling_fee = EXTENDED_HANDLING_FEE

        unit_price = float("inf")
        try:
            for p in self.price:
                if p["qTo"] is None or qty < p["qTo"]:
                    unit_price = float(p["price"])
            unit_price = float(self.price[-1]["price"])
        except LookupError:
            pass

        return unit_price * qty + handling_fee

    def attribute_to_parameter(
        self, attribute_name: str, use_tolerance: bool = False, ignore_at: bool = True
    ) -> Parameter:
        """
        Convert a component value in the extra['attributes'] dict to a parameter

        :param attribute_name: The key in the extra['attributes'] dict to convert
        :param use_tolerance: Whether to use the tolerance field in the component

        :return: The parameter representing the attribute value
        """
        assert isinstance(self.extra, dict) and "attributes" in self.extra

        value_field = self.extra["attributes"][attribute_name]
        # parse fields like "850mV@1A"
        # TODO better to actually parse this
        if ignore_at:
            value_field = value_field.split("@")[0]

        value_field = value_field.replace("cd", "candela")

        # parse fields like "1.5V~2.5V"
        if "~" in value_field:
            values = value_field.split("~")
            if len(values) != 2:
                raise ValueError(f"Invalid range from value '{value_field}'")
            return F.Range(*(P.Quantity(v) for v in values))

        # unit hacks

        try:
            value = P.Quantity(value_field)
        except UndefinedUnitError as e:
            raise ValueError(f"Could not parse value field '{value_field}'") from e

        if not use_tolerance:
            return F.Constant(value)

        if "Tolerance" not in self.extra["attributes"]:
            raise ValueError(f"No Tolerance field in component (lcsc: {self.lcsc})")
        if "ppm" in self.extra["attributes"]["Tolerance"]:
            tolerance = float(self.extra["attributes"]["Tolerance"].strip("±pm")) / 1e6
        elif "%~+" in self.extra["attributes"]["Tolerance"]:
            tolerances = self.extra["attributes"]["Tolerance"].split("~")
            tolerances = [float(t.strip("%+-")) for t in tolerances]
            tolerance = max(tolerances) / 100
        elif "%" in self.extra["attributes"]["Tolerance"]:
            tolerance = float(self.extra["attributes"]["Tolerance"].strip("%±")) / 100
        else:
            raise ValueError(
                "Could not parse tolerance field "
                f"'{self.extra['attributes']['Tolerance']}'"
            )

        return F.Range.from_center_rel(value, tolerance)

    def get_parameter(self, m: MappingParameterDB) -> Parameter:
        """
        Transform a component attribute to a parameter

        :param attribute_search_keys: The key in the component's extra['attributes']
        dict that holds the value to check
        :param tolerance_search_key: The key in the component's extra['attributes'] dict
        that holds the tolerance value
        :param parser: A function to convert the attribute value to the correct type

        :return: The parameter representing the attribute value
        """

        attribute_search_keys = m.attr_keys
        tolerance_search_key = m.attr_tolerance_key
        parser = m.transform_fn

        if tolerance_search_key is not None and parser is not None:
            raise NotImplementedError(
                "Cannot provide both tolerance_search_key and parser arguments"
            )

        assert isinstance(self.extra, dict)

        attr_key = next(
            (k for k in attribute_search_keys if k in self.extra.get("attributes", "")),
            None,
        )

        if "attributes" not in self.extra:
            raise LookupError("does not have any attributes")
        if attr_key is None:
            raise LookupError(
                f"does not have any of required attribute fields: "
                f"{attribute_search_keys} in {self.extra['attributes']}"
            )
        if (
            tolerance_search_key is not None
            and tolerance_search_key not in self.extra["attributes"]
        ):
            raise LookupError(
                f"does not have any of required tolerance fields: "
                f"{tolerance_search_key}"
            )

        if parser is not None:
            return parser(self.extra["attributes"][attr_key])

        return self.attribute_to_parameter(
            attr_key, tolerance_search_key is not None, m.ignore_at
        )

    def get_params(self, mapping: list[MappingParameterDB]) -> list[Parameter]:
        return [
            try_or(
                lambda: self.get_parameter(m),
                default_f=lambda e: TBD_ParseError(
                    e, f"Failed to parse {m.param_name}"
                ),
                catch=(LookupError, ValueError, AssertionError),
            )
            for m in mapping
        ]

    def attach(
        self,
        module: Module,
        mapping: list[MappingParameterDB],
        qty: int = 1,
        allow_TBD: bool = False,
    ):
        params = self.get_params(mapping)

        if not allow_TBD and any(isinstance(p, TBD_ParseError) for p in params):
            params_str = indent(
                "\n"
                + "\n".join(repr(p) for p in params if isinstance(p, TBD_ParseError)),
                " " * 4,
            )
            raise Component.ParseError(
                f"Failed to parse parameters for component {self.partno}: {params_str}"
            )

        for name, value in zip([m.param_name for m in mapping], params):
            getattr(module, name).override(value)

        module.add(
            F.has_descriptive_properties_defined(
                {
                    DescriptiveProperties.partno: self.mfr,
                    DescriptiveProperties.manufacturer: asyncio.run(
                        Manufacturers().get_from_id(self.manufacturer_id)
                    ),
                    DescriptiveProperties.datasheet: self.datasheet,
                    "JLCPCB stock": str(self.stock),
                    "JLCPCB price": f"{self.get_price(qty):.4f}",
                    "JLCPCB description": self.description,
                    "JLCPCB Basic": str(bool(self.basic)),
                    "JLCPCB Preferred": str(bool(self.preferred)),
                },
            )
        )

        attach(module, self.partno)
        module.add(has_part_picked_defined(JLCPCB_Part(self.partno)))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Attached component {self.partno} to module {module}: \n"
                f"{indent(str(params), ' '*4)}\n--->\n"
                f"{indent(pretty_params(module), ' '*4)}"
            )


class ComponentQuery:
    class Error(Exception): ...

    class ParamError(Error):
        def __init__(self, param: Parameter, msg: str):
            self.param = param
            self.msg = msg
            super().__init__(f"{msg} for parameter {param!r}")

    def __init__(self):
        # init db connection
        JLCPCB_DB()

        self.Q: Q | None = Q()
        self.results: list[Component] | None = None

    async def exec(self) -> list[Component]:
        queryset = Component.filter(self.Q)
        logger.debug(f"Query results: {await queryset.count()}")
        self.results = await queryset
        self.Q = None
        return self.results

    def get(self) -> list[Component]:
        if self.results is not None:
            return self.results
        return asyncio.run(self.exec())

    def filter_by_stock(self, qty: int) -> Self:
        assert self.Q
        self.Q &= Q(stock__gte=qty)
        return self

    def filter_by_value(
        self,
        value: Parameter[Quantity],
        si_unit: str,
        e_series: set[float] | None = None,
    ) -> Self:
        assert self.Q
        value = value.get_most_narrow()

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Filtering by value:\n{indent(pretty_param_tree(value), ' '*4)}"
            )

        if isinstance(value, F.ANY):
            return self
        assert not self.results
        value_query = Q()
        try:
            intersection = F.Set(
                [e_series_intersect(value, e_series or E_SERIES_VALUES.E_ALL)]
            ).params
        except ParamNotResolvedError as e:
            raise ComponentQuery.ParamError(
                value, f"Could not run e_series_intersect: {e}"
            ) from e
        si_vals = [
            to_si_str(cast_assert(F.Constant, r).value, si_unit)
            .replace("µ", "u")
            .replace("inf", "∞")
            for r in intersection
        ]
        logger.debug(f"Possible values: {si_vals}")
        for si_val in si_vals:
            value_query |= Q(description__contains=f" {si_val}")
        self.Q &= value_query
        return self

    def filter_by_category(self, category: str, subcategory: str) -> Self:
        assert self.Q
        category_ids = asyncio.run(Category().get_ids(category, subcategory))
        self.Q &= Q(category_id__in=category_ids)
        return self

    def filter_by_footprint(
        self, footprint_candidates: Sequence[tuple[str, int]] | None
    ) -> Self:
        assert self.Q
        if not footprint_candidates:
            return self
        footprint_query = Q()
        if footprint_candidates is not None:
            for footprint, pin_count in footprint_candidates:
                footprint_query |= Q(description__icontains=footprint) & Q(
                    joints=pin_count
                )
        self.Q &= footprint_query
        return self

    def filter_by_traits(self, obj: Module) -> Self:
        out = self
        if obj.has_trait(F.has_footprint_requirement):
            out = self.filter_by_footprint(
                obj.get_trait(F.has_footprint_requirement).get_footprint_requirement()
            )

        return out

    def sort_by_price(self, qty: int = 1) -> Self:
        self.get().sort(key=lambda x: x.get_price(qty))
        return self

    def filter_by_lcsc_pn(self, partnumber: str) -> Self:
        assert self.Q
        self.Q &= Q(lcsc=partnumber.strip("C"))
        return self

    def filter_by_manufacturer_pn(self, partnumber: str) -> Self:
        assert self.Q
        self.Q &= Q(mfr__icontains=partnumber)
        return self

    def filter_by_manufacturer(self, manufacturer: str) -> Self:
        assert self.Q
        manufacturer_ids = asyncio.run(Manufacturers().get_ids(manufacturer))
        self.Q &= Q(manufacturer_id__in=manufacturer_ids)
        return self

    def filter_by_module_params(
        self,
        module: Module,
        mapping: list[MappingParameterDB],
    ) -> Generator[Component, None, None]:
        """
        Filter the results by the parameters of the module

        This should be used as the last step before attaching the component to the
        module

        :param module: The module to filter by
        :param mapping: The mapping of module parameters to component attributes
        :param qty: The quantity of components needed
        :param attach_first: Whether to attach the first component that matches the
        parameters and return immediately

        :return: The first component that matches the parameters
        """

        for c in self.get():
            params = c.get_params(mapping)

            if not all(
                pm := [
                    p.is_subset_of(getattr(module, m.param_name))
                    for p, m in zip(params, mapping)
                ]
            ):
                logger.debug(
                    f"Component {c.lcsc} doesn't match: "
                    f"{[p for p, v in zip(params, pm) if not v]}"
                )
                continue

            logger.debug(
                f"Found part {c.lcsc:8} "
                f"Basic: {bool(c.basic)}, Preferred: {bool(c.preferred)}, "
                f"Price: ${c.get_price(1):2.4f}, "
                f"{c.description:15},"
            )

            yield c

    def filter_by_module_params_and_attach(
        self, module: Module, mapping: list[MappingParameterDB], qty: int = 1
    ):
        # TODO if no modules without TBD, rerun with TBD allowed

        failures = []
        for c in self.filter_by_module_params(module, mapping):
            try:
                c.attach(module, mapping, qty, allow_TBD=False)
                return self
            except (ValueError, Component.ParseError) as e:
                failures.append((c, e))
            except LCSC_NoDataException as e:
                failures.append((c, e))
            except LCSC_PinmapException as e:
                failures.append((c, e))

        if failures:
            fail_str = indent(
                "\n" + f"{'\n'.join(f'{c}: {e}' for c, e in failures)}", " " * 4
            )

            raise PickError(
                f"Failed to attach any components to module {module}: {len(failures)}"
                f" {fail_str}",
                module,
            )

        raise PickError(
            "No components found that match the parameters and that can be attached",
            module,
        )


class JLCPCB_DB:
    @dataclass
    class Config:
        db_path: Path = CACHE_FOLDER / Path("jlcpcb_part_database")
        no_download_prompt: bool = False
        force_db_update: bool = False

    config = Config()
    _instance: "JLCPCB_DB | None" = None
    failed: Exception | None = None

    @staticmethod
    def get() -> "JLCPCB_DB":
        return JLCPCB_DB.__new__(JLCPCB_DB)

    def __new__(cls) -> "JLCPCB_DB":
        if cls.failed:
            raise cls.failed
        if not JLCPCB_DB._instance:
            instance = super(JLCPCB_DB, cls).__new__(cls)
            try:
                instance.init()
            except FileNotFoundError as e:
                cls.failed = e
                raise e

            JLCPCB_DB._instance = instance
            at_exit(JLCPCB_DB.close)
        return JLCPCB_DB._instance

    @staticmethod
    def close():
        if not JLCPCB_DB._instance:
            return
        instance = JLCPCB_DB._instance
        JLCPCB_DB._instance = None
        del instance

    def init(self) -> None:
        config = self.config
        self.db_path = config.db_path
        self.db_file = config.db_path / Path("cache.sqlite3")
        self.connected = False

        no_download_prompt = config.no_download_prompt

        if not sys.stdin.isatty():
            no_download_prompt = True

        if config.force_db_update:
            self.download()
        elif not self.has_db():
            if no_download_prompt or self.prompt_db_update(
                f"No JLCPCB database found at {self.db_file}, download now?"
            ):
                self.download()
            else:
                raise FileNotFoundError(f"No JLCPCB database found at {self.db_file}")
        elif not self.is_db_up_to_date():
            if not no_download_prompt and self.prompt_db_update(
                f"JLCPCB database at {self.db_file} is older than 7 days, update?"
            ):
                self.download()
            else:
                logger.warning("Continuing with outdated JLCPCB database")

        asyncio.run(self._init_db())

    def __del__(self):
        if self.connected:
            asyncio.run(self._close_db())

    async def _init_db(self):
        await Tortoise.init(
            db_url=f"sqlite://{self.db_path}/cache.sqlite3",
            modules={
                "models": [__name__]
            },  # Use __name__ to refer to the current module
        )
        self.connected = True

    async def _close_db(self):
        from tortoise.log import logger as tortoise_logger

        # suppress close ORM info
        tortoise_logger.setLevel(logging.WARNING)
        await Tortoise.close_connections()
        self.connected = False

    def has_db(self) -> bool:
        return self.db_path.is_dir() and self.db_file.is_file()

    def is_db_up_to_date(
        self, max_timediff: datetime.timedelta = datetime.timedelta(days=7)
    ) -> bool:
        if not self.has_db():
            return False

        return (
            datetime.datetime.fromtimestamp(
                self.db_file.stat().st_mtime, tz=datetime.timezone.utc
            )
            >= datetime.datetime.now(tz=datetime.timezone.utc) - max_timediff
        )

    def prompt_db_update(self, prompt: str = "Update JLCPCB database?") -> bool:
        ans = input(prompt + " [Y/n]:").lower()
        return ans == "y" or ans == ""

    def download(
        self,
    ):
        def download_file(url, output_path: Path):
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

        def get_number_of_volumes(zip_path):
            with open(zip_path, "rb") as f:
                f.seek(-22, os.SEEK_END)  # Go to the end of the file minus 22 bytes
                end_of_central_dir = f.read(22)

                if len(end_of_central_dir) != 22 or not end_of_central_dir.startswith(
                    b"PK\x05\x06"
                ):
                    # Not a valid ZIP file or the end of central directory signature is
                    # missing
                    raise ValueError(
                        "Invalid ZIP file or End of Central Directory signature not "
                        "found"
                    )

                # Unpack the number of this volume (should be 0 if single part zip)
                current_volume, volume_with_central_dir = struct.unpack(
                    "<HH", end_of_central_dir[4:8]
                )

                # Number of volume files = volume_with_central_dir + 1
                return volume_with_central_dir + 1

        self.db_path.mkdir(parents=True, exist_ok=True)

        zip_file = self.db_path / Path("cache.zip")
        base_url = "https://yaqwsx.github.io/jlcparts/data/"

        logger.info(f"Downloading {base_url}cache.zip to {zip_file}")
        download_file(base_url + "cache.zip", zip_file)

        num_volumes = get_number_of_volumes(zip_file)
        assert num_volumes <= 99
        logger.info(f"Number of volumes: {num_volumes}")

        # Download the additional volume files
        for volume_num in track(
            range(num_volumes), description="Downloading and appending zip volumes"
        ):
            # Skip .zip file since it is already downloaded
            if volume_num == 0:
                continue

            volume_file = self.db_path / Path(f"cache.z{volume_num:02d}")
            volume_url = base_url + f"cache.z{volume_num:02d}"

            download_file(volume_url, volume_file)

        self.db_file.unlink(missing_ok=True)
        logger.info(f"Unzipping {zip_file}")
        patoolib.extract_archive(str(zip_file), outdir=str(self.db_path))

        # remove downloaded files
        for volume_num in range(num_volumes):
            if volume_num == 0:
                volume_file = zip_file
            else:
                volume_file = self.db_path / Path(f"cache.z{volume_num:02d}")
            os.remove(volume_file)
