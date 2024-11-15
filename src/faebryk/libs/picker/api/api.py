# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import functools
import json
import logging
import textwrap
from dataclasses import dataclass
from typing import Iterable

import requests
from dataclasses_json import dataclass_json
from pint import DimensionalityError

from faebryk.core.module import Module

# TODO: replace with API-specific data model
from faebryk.libs.picker.common import SIvalue
from faebryk.libs.picker.jlcpcb.jlcpcb import Component, MappingParameterDB
from faebryk.libs.picker.lcsc import LCSC_NoDataException, LCSC_PinmapException
from faebryk.libs.picker.picker import PickError
from faebryk.libs.util import ConfigFlagString, try_or

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://components.atopileapi.com"
DEFAULT_API_TIMEOUT_SECONDS = 30
API_URL = ConfigFlagString("PICKER_API_URL", DEFAULT_API_URL, "API URL")
API_KEY = ConfigFlagString("PICKER_API_KEY", "", "API key")


class ApiError(Exception): ...


class ApiNotConfiguredError(ApiError): ...


class ApiHTTPError(ApiError):
    def __init__(self, error: requests.exceptions.HTTPError):
        super().__init__()
        self.response = error.response

    def __str__(self) -> str:
        status_code = self.response.status_code
        detail = self.response.json()["detail"]
        return f"{super().__str__()}: {status_code} {detail}"


def check_compatible_parameters(
    module: Module, component: Component, mapping: list[MappingParameterDB]
) -> bool:
    """
    Check if the parameters of a component are compatible with the module
    """
    # TODO: serialize the module and check compatibility in the backend

    params = component.get_params(mapping)
    param_matches = [
        try_or(
            lambda: p.is_subset_of(getattr(module, m.param_name)),
            default=False,
            catch=DimensionalityError,
        )
        for p, m in zip(params, mapping)
    ]

    if not (is_compatible := all(param_matches)):
        logger.debug(
            f"Component {component.lcsc} doesn't match: "
            f"{[p for p, v in zip(params, param_matches) if not v]}"
        )

    return is_compatible


def try_attach(
    cmp: Module, parts: Iterable[Component], mapping: list[MappingParameterDB], qty: int
) -> bool:
    failures = []
    for part in parts:
        if not check_compatible_parameters(cmp, part, mapping):
            continue

        try:
            part.attach(cmp, mapping, qty, allow_TBD=False)
            return True
        except (ValueError, Component.ParseError) as e:
            failures.append((part, e))
        except LCSC_NoDataException as e:
            failures.append((part, e))
        except LCSC_PinmapException as e:
            failures.append((part, e))

    if failures:
        fail_str = textwrap.indent(
            "\n" + f"{'\n'.join(f'{c}: {e}' for c, e in failures)}", " " * 4
        )

        raise PickError(
            f"Failed to attach any components to module {cmp}: {len(failures)}"
            f" {fail_str}",
            cmp,
        )

    return False


@dataclass_json
@dataclass(frozen=True)
class FootprintCandidate:
    footprint: str
    pin_count: int


@dataclass_json
@dataclass(frozen=True)
class BaseParams:
    footprint_candidates: list[FootprintCandidate]
    qty: int

    def convert_to_dict(self) -> dict:
        return self.to_dict()  # type: ignore


@dataclass(frozen=True)
class ResistorParams(BaseParams):
    resistances: list[SIvalue]


@dataclass(frozen=True)
class CapacitorParams(BaseParams):
    capacitances: list[SIvalue]


@dataclass(frozen=True)
class InductorParams(BaseParams):
    inductances: list[SIvalue]


@dataclass(frozen=True)
class TVSParams(BaseParams): ...


@dataclass(frozen=True)
class DiodeParams(BaseParams):
    max_currents: list[SIvalue]
    reverse_working_voltages: list[SIvalue]


@dataclass(frozen=True)
class LEDParams(BaseParams): ...


@dataclass(frozen=True)
class MOSFETParams(BaseParams): ...


@dataclass(frozen=True)
class LDOParams(BaseParams): ...


@dataclass(frozen=True)
class LCSCParams:
    lcsc: int


@dataclass(frozen=True)
class ManufacturerPartParams:
    manufacturer_name: str
    mfr: str
    qty: int


class ApiClient:
    @dataclass
    class Config:
        api_url: str = API_URL.get()
        api_key: str = API_KEY.get()

    config = Config()

    def __init__(self):
        self._client = requests.Session()
        self._client.headers["Authorization"] = f"Bearer {self.config.api_key}"

    def _get(self, url: str, timeout: float = 10) -> requests.Response:
        try:
            response = self._client.get(f"{self.config.api_url}{url}", timeout=timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ApiHTTPError(e) from e

        return response

    def _post(
        self, url: str, data: dict, timeout: float = DEFAULT_API_TIMEOUT_SECONDS
    ) -> requests.Response:
        try:
            response = self._client.post(
                f"{self.config.api_url}{url}", json=data, timeout=timeout
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ApiHTTPError(e) from e

        return response

    @staticmethod
    def ComponentFromResponse(kw: dict) -> Component:
        # TODO very ugly fix
        kw["extra"] = json.dumps(kw["extra"])
        return Component(**kw)

    @functools.lru_cache(maxsize=None)
    def fetch_part_by_lcsc(self, lcsc: int) -> list[Component]:
        response = self._get(f"/v0/component/lcsc/{lcsc}")
        return [
            self.ComponentFromResponse(part) for part in response.json()["components"]
        ]

    @functools.lru_cache(maxsize=None)
    def fetch_part_by_mfr(self, mfr: str, mfr_pn: str) -> list[Component]:
        response = self._get(f"/v0/component/mfr/{mfr}/{mfr_pn}")
        return [
            self.ComponentFromResponse(part) for part in response.json()["components"]
        ]

    def query_parts(self, method: str, params: BaseParams) -> list[Component]:
        response = self._post(f"/v0/query/{method}", params.convert_to_dict())
        return [
            self.ComponentFromResponse(part) for part in response.json()["components"]
        ]

    def fetch_resistors(self, params: ResistorParams) -> list[Component]:
        return self.query_parts("resistors", params)

    def fetch_capacitors(self, params: CapacitorParams) -> list[Component]:
        return self.query_parts("capacitors", params)

    def fetch_inductors(self, params: InductorParams) -> list[Component]:
        return self.query_parts("inductors", params)

    def fetch_tvs(self, params: TVSParams) -> list[Component]:
        return self.query_parts("tvs", params)

    def fetch_diodes(self, params: DiodeParams) -> list[Component]:
        return self.query_parts("diodes", params)

    def fetch_leds(self, params: LEDParams) -> list[Component]:
        return self.query_parts("leds", params)

    def fetch_mosfets(self, params: MOSFETParams) -> list[Component]:
        return self.query_parts("mosfets", params)

    def fetch_ldos(self, params: LDOParams) -> list[Component]:
        return self.query_parts("ldos", params)


@functools.lru_cache
def get_api_client() -> ApiClient:
    return ApiClient()
