# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import asyncio
import datetime
import json
import logging
import math
import os
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import indent
from typing import Any, Callable, Generator, Self, Sequence

import patoolib
import requests
from rich.progress import track
from tortoise import Tortoise
from tortoise.expressions import Q
from tortoise.fields import CharField, DatetimeField, IntField, JSONField, TextField
from tortoise.models import Model

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import (
    Numbers,
    Parameter,
    ParameterOperatable,
)
from faebryk.core.solver.solver import Solver
from faebryk.libs.e_series import E_SERIES
from faebryk.libs.picker.common import (
    PickerESeriesIntersectionError,
    PickerUnboundedParameterError,
    check_compatible_parameters,
    generate_si_values,
    try_attach,
)
from faebryk.libs.picker.lcsc import (
    LCSC_Part,
    attach,
)
from faebryk.libs.picker.picker import (
    DescriptiveProperties,
    has_part_picked_defined,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
    Quantity_Singleton,
)
from faebryk.libs.sets.sets import P_UnitSet
from faebryk.libs.units import UndefinedUnitError, quantity
from faebryk.libs.util import at_exit, once

logger = logging.getLogger(__name__)

# TODO dont hardcode relative paths
BUILD_FOLDER = Path("./build")
CACHE_FOLDER = BUILD_FOLDER / Path("cache")

INSPECT_KNOWN_SUPERSETS_LIMIT = 100


class JLCPCB_Part(LCSC_Part):
    def __init__(self, partno: str) -> None:
        super().__init__(partno=partno)


@dataclass(frozen=True)
class MappingParameterDB:
    param_name: str
    attr_keys: list[str] = field(hash=False)
    attr_tolerance_key: str | None = None
    transform_fn: Callable[[str], ParameterOperatable.Literal] | None = None
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
    category = CharField(max_length=255)
    subcategory = CharField(max_length=255, optional=True)
    mfr = CharField(max_length=255)
    package = CharField(max_length=255)
    joints = IntField()
    manufacturer_id = IntField()
    manufacturer_name = CharField(max_length=255, optional=True)
    basic = IntField()
    description = CharField(max_length=255)
    datasheet = CharField(max_length=255)
    stock = IntField()
    price = JSONField()
    last_update = DatetimeField()
    extra = TextField()
    flag = IntField()
    last_on_stock = DatetimeField()
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

    @property
    @once
    def extra_(self) -> dict:
        if isinstance(self.extra, str):
            return json.loads(self.extra)
        assert isinstance(self.extra, dict)
        return self.extra

    def attribute_to_range(
        self, attribute_name: str, use_tolerance: bool = False, ignore_at: bool = True
    ) -> Quantity_Interval:
        """
        Convert a component value in the extra['attributes'] dict to a parameter

        :param attribute_name: The key in the extra['attributes'] dict to convert
        :param use_tolerance: Whether to use the tolerance field in the component

        :return: The parameter representing the attribute value
        """
        assert isinstance(self.extra_, dict) and "attributes" in self.extra_

        value_field = self.extra_["attributes"][attribute_name]
        # parse fields like "850mV@1A"
        # TODO better to actually parse this
        if ignore_at:
            value_field = value_field.split("@")[0]

        # parse fields like "110mA;130mA"
        # TODO: better data model so we can choose the appropriate value
        if ";" in value_field:
            value_field = value_field.split(";")[0]

        value_field = value_field.replace("cd", "candela")

        # parse fields like "1.5V~2.5V"
        if "~" in value_field:
            values = value_field.split("~")
            if len(values) != 2:
                raise ValueError(f"Invalid range from value '{value_field}'")
            low, high = map(quantity, values)
            return Quantity_Interval(low, high)

        # unit hacks

        try:
            value = quantity(value_field)
        except UndefinedUnitError as e:
            raise ValueError(f"Could not parse value field '{value_field}'") from e

        if not use_tolerance:
            return Quantity_Singleton(value)

        if "Tolerance" not in self.extra_["attributes"]:
            raise ValueError(f"No Tolerance field in component (lcsc: {self.lcsc})")
        if "ppm" in self.extra_["attributes"]["Tolerance"]:
            tolerance = float(self.extra_["attributes"]["Tolerance"].strip("±pm")) / 1e6
        elif "%~+" in self.extra_["attributes"]["Tolerance"]:
            tolerances = self.extra_["attributes"]["Tolerance"].split("~")
            tolerances = [float(t.strip("%+-")) for t in tolerances]
            tolerance = max(tolerances) / 100
        elif "%" in self.extra_["attributes"]["Tolerance"]:
            tolerance = float(self.extra_["attributes"]["Tolerance"].strip("%±")) / 100
        else:
            raise ValueError(
                "Could not parse tolerance field "
                f"'{self.extra_['attributes']['Tolerance']}'"
            )

        return Quantity_Interval.from_center_rel(value, tolerance)

    def get_literal(self, m: MappingParameterDB) -> ParameterOperatable.Literal:
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

        assert isinstance(self.extra_, dict)

        attr_key = next(
            (
                k
                for k in attribute_search_keys
                if k in self.extra_.get("attributes", "")
            ),
            None,
        )

        if "attributes" not in self.extra_:
            raise LookupError("does not have any attributes")
        if attr_key is None:
            raise LookupError(
                f"does not have any of required attribute fields: "
                f"{attribute_search_keys} in {self.extra_['attributes']}"
            )
        if (
            tolerance_search_key is not None
            and tolerance_search_key not in self.extra_["attributes"]
        ):
            raise LookupError(
                f"does not have any of required tolerance fields: "
                f"{tolerance_search_key}"
            )

        if parser is not None:
            return parser(self.extra_["attributes"][attr_key])

        return self.attribute_to_range(
            attr_key, tolerance_search_key is not None, m.ignore_at
        )

    def get_literal_for_mappings(
        self, mapping: list[MappingParameterDB]
    ) -> tuple[
        dict[MappingParameterDB, ParameterOperatable.Literal],
        dict[MappingParameterDB, Exception],
    ]:
        params = {}
        exceptions = {}
        for m in mapping:
            try:
                params[m] = self.get_literal(m)
            except (LookupError, ValueError, AssertionError) as e:
                exceptions[m] = e
        return params, exceptions

    def attach(
        self,
        module: Module,
        mapping: list[MappingParameterDB],
        qty: int = 1,
        ignore_exceptions: bool = False,
    ):
        params, exceptions = self.get_literal_for_mappings(mapping)

        if not ignore_exceptions and exceptions:
            params_str = indent(
                "\n" + "\n".join(repr(e) for e in exceptions.values()),
                " " * 4,
            )
            raise Component.ParseError(
                f"Failed to parse parameters for component {self.partno}: {params_str}"
            )

        attach(module, self.partno)

        module.add(
            F.has_descriptive_properties_defined(
                {
                    DescriptiveProperties.partno: self.mfr,
                    DescriptiveProperties.manufacturer: self.mfr_name,
                    DescriptiveProperties.datasheet: self.datasheet,
                    "JLCPCB stock": str(self.stock),
                    "JLCPCB price": f"{self.get_price(qty):.4f}",
                    "JLCPCB description": self.description,
                    "JLCPCB Basic": str(bool(self.basic)),
                    "JLCPCB Preferred": str(bool(self.preferred)),
                },
            )
        )

        module.add(has_part_picked_defined(JLCPCB_Part(self.partno)))

        for name, value in params.items():
            getattr(module, name.param_name).alias_is(value)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Attached component {self.partno} to module {module}: \n"
                f"{indent(str(params), ' '*4)}\n--->\n"
                f"{indent(module.pretty_params(), ' '*4)}"
            )

    @property
    def mfr_name(self):
        try:
            return self.manufacturer_name
        except AttributeError:
            return asyncio.run(Manufacturers().get_from_id(self.manufacturer_id))


class ComponentQuery:
    class Error(Exception): ...

    class ParamError(Error):
        def __init__(self, param: P_UnitSet, msg: str):
            self.param = param
            self.msg = msg
            super().__init__(f"{msg} for parameter {param!r}")

    def __init__(self):
        # init db connection
        JLCPCB_DB()

        self.Q: Q | None = Q()
        self.results: list[Component] | None = None

    async def exec(self) -> list[Component]:
        assert self.Q
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

    def filter_by_description(self, *keywords: str) -> Self:
        assert self.Q

        logger.debug(f"Possible keywords: {keywords}")
        description_query = Q()
        for keyword in keywords:
            description_query |= Q(description__contains=keyword)
        self.Q &= description_query

        return self

    def filter_by_si_values(
        self,
        value: Quantity_Interval_Disjoint,
        e_series: E_SERIES | None = None,
        tolerance_requirement: float | None = None,
    ) -> Self:
        assert self.Q
        assert not self.results

        try:
            si_vals = generate_si_values(value, e_series)
        except PickerUnboundedParameterError:
            return self
        except PickerESeriesIntersectionError as e:
            raise ComponentQuery.ParamError(value, str(e)) from e

        if tolerance_requirement:
            self.filter_by_tolerance(tolerance_requirement)

        return self.filter_by_description(*si_vals)

    def hint_filter_parameter(
        self,
        param: Parameter,
        solver: Solver,
        e_series: E_SERIES | None = None,
    ) -> Self:
        # param will in the general case consist of multiple ranges
        # we have to pick some range or make a new one to pre_filter our candidates
        # we can try making a new range with inspect_min and max to filter out
        # everything we already know won't fit
        # then we can check the cardinality of the remaining candidates to see if we
        # need to pick a range contained in the param to filter

        # TODO
        if not isinstance(param.domain, Numbers):
            raise NotImplementedError()

        candidate_ranges = solver.inspect_get_known_supersets(param)
        if not candidate_ranges.is_finite():
            return self
        if not isinstance(candidate_ranges, Quantity_Interval_Disjoint):
            # TODO nothing we can really do in the sqlite version here
            # might just save it for later filtering
            return self

        return self.filter_by_si_values(candidate_ranges, e_series)

    def filter_by_tolerance(self, tolerance: float) -> Self:
        assert self.Q

        tol_int = int(math.floor(tolerance * 100))
        return self.filter_by_description(f"±{tol_int}%")

    def filter_by_category(self, category: str, subcategory: str) -> Self:
        assert self.Q
        category_ids = asyncio.run(Category().get_ids(category, subcategory))
        self.Q &= Q(category_id__in=category_ids)
        return self

    def filter_by_package(self, package_candidates: Sequence[str] | None) -> Self:
        assert self.Q
        if not package_candidates:
            return self
        package_query = Q()
        if package_candidates is not None:
            for package in package_candidates:
                package_query |= Q(description__icontains=package)
        self.Q &= package_query
        return self

    def filter_by_traits(self, obj: Module) -> Self:
        out = self
        if obj.has_trait(F.has_package_requirement):
            out = self.filter_by_package(
                obj.get_trait(F.has_package_requirement).get_package_candidates()
            )

        return out

    def sort_by_price(self, qty: int = 1) -> Self:
        self.get().sort(key=lambda x: x.get_price(qty))
        return self

    def filter_by_lcsc_pn(self, partnumber: str) -> Self:
        assert self.Q
        self.Q &= Q(lcsc=partnumber.strip("C"))
        return self

    def filter_by_specified_parameters(self, mapping: list[MappingParameterDB]) -> Self:
        assert self.Q
        keys = [m.attr_keys for m in mapping]

        extra_query = Q()
        for kl in keys:
            sub_q = Q()
            for k in kl:
                sub_q |= Q(extra__contains=k)
            extra_query &= sub_q
        self.Q &= extra_query
        return self

    def filter_by_attribute_mention(self, candidates: list[str]) -> Self:
        if not candidates:
            return self
        assert self.Q
        q = Q()
        for candidate in candidates:
            q |= Q(extra__contains=candidate)
        self.Q &= q
        return self

    def filter_by_manufacturer_pn(self, partnumber: str) -> Self:
        assert self.Q
        self.Q &= Q(mfr__icontains=partnumber)
        return self

    def filter_by_manufacturer(self, manufacturer: str) -> Self:
        assert self.Q
        if not manufacturer:
            return self
        manufacturer_ids = asyncio.run(Manufacturers().get_ids(manufacturer))
        self.Q &= Q(manufacturer_id__in=manufacturer_ids)
        return self

    def filter_by_module_params(
        self,
        module: Module,
        mapping: list[MappingParameterDB],
        solver: Solver,
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

        # iterate through all candidate components
        for c in self.get():
            if check_compatible_parameters(module, c, mapping, solver):
                yield c

    def filter_by_module_params_and_attach(
        self,
        module: Module,
        mapping: list[MappingParameterDB],
        solver: Solver,
        qty: int = 1,
    ):
        try_attach(
            module,
            self.filter_by_module_params(module, mapping, solver),
            mapping,
            qty,
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
        self.fresh_db = False

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
        if self.fresh_db:
            await self.post_process_db()

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
        ans = input(prompt + " [y/N]:").lower()
        return ans == "y"

    async def post_process_db(self):
        return
        # Ignoring all OOS components isn't a good idea, since there are many
        # parts you may want to explicitly include in your BoM, even when OOS
        # eg. most ICs, micros
        # TODO: consider another approach to optimize the DB, eg. partitioning
        logger.info("Deleting out-of-stock components from DB")
        await Component.filter(stock__lt=1).delete()

        logger.info("Vacuuming DB")
        await Tortoise.get_connection("default").execute_query("VACUUM;")

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

        self.fresh_db = True
