# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import functools
import json
import logging
from dataclasses import dataclass

import requests
from dataclasses_json import dataclass_json

from faebryk.core.module import Module

# TODO: replace with API-specific data model
from faebryk.core.parameter import Numbers, Parameter
from faebryk.core.solver.solver import Solver
from faebryk.libs.e_series import E_SERIES
from faebryk.libs.picker.common import (
    SIvalue,
    check_compatible_parameters,
    generate_si_values,
    try_attach,
)
from faebryk.libs.picker.jlcpcb.jlcpcb import Component
from faebryk.libs.picker.jlcpcb.picker_lib import _MAPPINGS_BY_TYPE
from faebryk.libs.picker.picker import PickError
from faebryk.libs.util import (
    ConfigFlagString,
    KeyErrorAmbiguous,
    KeyErrorNotFound,
    closest_base_class,
    find,
)

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


def api_filter_by_module_params_and_attach(
    cmp: Module, parts: list[Component], solver: Solver
):
    """
    Find a component with matching parameters
    """
    try:
        mapping = find(_MAPPINGS_BY_TYPE.items(), lambda m: isinstance(cmp, m[0]))[1]
    except KeyErrorAmbiguous as e:
        mapping = _MAPPINGS_BY_TYPE[
            closest_base_class(type(cmp), [k for k, _ in e.duplicates])
        ]
    except KeyErrorNotFound:
        mapping = []

    parts_gen = (
        part
        for part in parts
        if check_compatible_parameters(cmp, part, mapping, solver)
    )

    try:
        try_attach(cmp, parts_gen, mapping, qty=1)
    except PickError as ex:
        try:
            friendly_params = [
                f"{p.param_name} within {getattr(cmp, p.param_name, 'unknown')}"
                for p in mapping
            ]
        except Exception:
            logger.exception("Failed to make a friendly description of the parameters")
            friendly_params = []

        raise PickError(
            f"No components found that match {' and '.join(friendly_params)}",
            cmp,
        ) from ex


def get_footprint_candidates(module: Module) -> list["FootprintCandidate"]:
    import faebryk.library._F as F

    if module.has_trait(F.has_footprint_requirement):
        return [
            FootprintCandidate(footprint, pin_count)
            for footprint, pin_count in module.get_trait(
                F.has_footprint_requirement
            ).get_footprint_requirement()
        ]
    return []


def api_generate_si_values(
    value: Parameter, solver: Solver, e_series: E_SERIES | None = None
) -> list[SIvalue]:
    if not isinstance(value.domain, Numbers):
        raise NotImplementedError(f"Parameter {value} is not a number")

    if not solver.inspect_known_supersets_are_few(value):
        raise NotImplementedError(f"Parameter {value} has too many known supersets")

    candidate_ranges = solver.inspect_get_known_superranges(value)
    # TODO api support for unbounded
    if not candidate_ranges.is_finite():
        logger.warning(f"Parameter {value} has unbounded known supersets")
        raise PickError(
            module=None, message=f"Parameter {value} has unbounded known supersets"
        )
    return generate_si_values(candidate_ranges, e_series=e_series)


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

        logger.debug(
            f"GET {self.config.api_url}{url}\n->\n{json.dumps(response.json(), indent=2)}"
        )

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

        logger.debug(
            f"POST {self.config.api_url}{url}\n{json.dumps(data, indent=2)}\n->\n"
            f"{json.dumps(response.json(), indent=2)}"
        )

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
