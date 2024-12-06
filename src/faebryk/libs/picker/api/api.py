# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import functools
import json
import logging
from dataclasses import dataclass, field

import requests
from dataclasses_json import config as dataclass_json_config
from dataclasses_json import dataclass_json

from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver
from faebryk.libs.picker.common import check_compatible_parameters, try_attach

# TODO: replace with API-specific data model
from faebryk.libs.picker.jlcpcb.jlcpcb import Component
from faebryk.libs.picker.jlcpcb.picker_lib import _MAPPINGS_BY_TYPE
from faebryk.libs.picker.picker import PickError
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import (
    ConfigFlagString,
    KeyErrorAmbiguous,
    KeyErrorNotFound,
    Serializable,
    SerializableJSONEncoder,
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

    # FIXME: should take the desired qty and respect it
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


def get_package_candidates(module: Module) -> list["PackageCandidate"]:
    import faebryk.library._F as F

    if module.has_trait(F.has_package_requirement):
        return [
            PackageCandidate(package)
            for package in module.get_trait(
                F.has_package_requirement
            ).get_package_candidates()
        ]
    return []


@dataclass_json
@dataclass(frozen=True)
class PackageCandidate:
    package: str


@dataclass_json
@dataclass(frozen=True)
class BaseParams(Serializable):
    package_candidates: list[PackageCandidate]
    qty: int

    def serialize(self) -> dict:
        return self.to_dict()  # type: ignore


@dataclass(frozen=True)
class Interval:
    min: float | None
    max: float | None


def SerializableField():
    return field(
        metadata=dataclass_json_config(encoder=SerializableJSONEncoder().default)
    )


@dataclass(frozen=True)
class ResistorParams(BaseParams):
    resistance: P_Set = SerializableField()
    max_power: P_Set = SerializableField()
    max_voltage: P_Set = SerializableField()


@dataclass(frozen=True)
class CapacitorParams(BaseParams):
    capacitance: P_Set = SerializableField()
    max_voltage: P_Set = SerializableField()
    temperature_coefficient: P_Set = SerializableField()


@dataclass(frozen=True)
class InductorParams(BaseParams):
    inductance: P_Set = SerializableField()
    self_resonant_frequency: P_Set = SerializableField()
    max_current: P_Set = SerializableField()
    dc_resistance: P_Set = SerializableField()


@dataclass(frozen=True)
class DiodeParams(BaseParams):
    forward_voltage: P_Set = SerializableField()
    current: P_Set = SerializableField()
    reverse_working_voltage: P_Set = SerializableField()
    reverse_leakage_current: P_Set = SerializableField()
    max_current: P_Set = SerializableField()


@dataclass(frozen=True)
class TVSParams(DiodeParams):
    reverse_breakdown_voltage: P_Set = SerializableField()


@dataclass(frozen=True)
class LEDParams(DiodeParams):
    brightness: P_Set = SerializableField()
    max_brightness: P_Set = SerializableField()
    color: P_Set = SerializableField()


@dataclass(frozen=True)
class LDOParams(BaseParams):
    max_input_voltage: P_Set = SerializableField()
    output_voltage: P_Set = SerializableField()
    quiescent_current: P_Set = SerializableField()
    dropout_voltage: P_Set = SerializableField()
    psrr: P_Set = SerializableField()
    output_polarity: P_Set = SerializableField()
    output_type: P_Set = SerializableField()
    output_current: P_Set = SerializableField()


@dataclass(frozen=True)
class MOSFETParams(BaseParams):
    channel_type: P_Set = SerializableField()
    saturation_type: P_Set = SerializableField()
    gate_source_threshold_voltage: P_Set = SerializableField()
    max_drain_source_voltage: P_Set = SerializableField()
    max_continuous_drain_current: P_Set = SerializableField()
    on_resistance: P_Set = SerializableField()


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
            f"GET {self.config.api_url}{url}\n->\n{json.dumps(response.json(), indent=2)}"  # noqa: E501  # pre-existing
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
        response = self._post(f"/v0/query/{method}", params.serialize())
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
