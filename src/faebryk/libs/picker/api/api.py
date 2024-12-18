# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import functools
import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import requests
from dataclasses_json import config as dataclass_json_config
from dataclasses_json import dataclass_json

from faebryk.core.module import Module

# TODO: replace with API-specific data model
if TYPE_CHECKING:
    from faebryk.libs.picker.jlcpcb.jlcpcb import Component
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import (
    ConfigFlagString,
    Serializable,
    SerializableJSONEncoder,
    once,
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
        try:
            detail = self.response.json()["detail"]
        except Exception:
            detail = self.response.text
        return f"{super().__str__()}: {status_code} {detail}"


def get_package_candidates(module: Module) -> frozenset["PackageCandidate"]:
    import faebryk.library._F as F

    if module.has_trait(F.has_package_requirement):
        return frozenset(
            PackageCandidate(package)
            for package in module.get_trait(
                F.has_package_requirement
            ).get_package_candidates()
        )
    return frozenset()


@dataclass_json
@dataclass(frozen=True)
class PackageCandidate:
    package: str


@dataclass_json
@dataclass(frozen=True, kw_only=True)
class BaseParams(Serializable):
    package_candidates: frozenset[PackageCandidate]
    qty: int
    endpoint: str | None = None

    def serialize(self) -> dict:
        return self.to_dict()  # type: ignore


@dataclass(frozen=True)
class Interval:
    min: float | None
    max: float | None


ApiParamT = P_Set | None


def SerializableField():
    return field(
        metadata=dataclass_json_config(encoder=SerializableJSONEncoder().default)
    )


@dataclass(frozen=True, kw_only=True)
class ResistorParams(BaseParams):
    endpoint: str = "resistors"
    resistance: ApiParamT = SerializableField()
    max_power: ApiParamT = SerializableField()
    max_voltage: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class CapacitorParams(BaseParams):
    endpoint: str = "capacitors"
    capacitance: ApiParamT = SerializableField()
    max_voltage: ApiParamT = SerializableField()
    temperature_coefficient: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class InductorParams(BaseParams):
    endpoint: str = "inductors"
    inductance: ApiParamT = SerializableField()
    self_resonant_frequency: ApiParamT = SerializableField()
    max_current: ApiParamT = SerializableField()
    dc_resistance: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class DiodeParams(BaseParams):
    endpoint: str = "diodes"
    forward_voltage: ApiParamT = SerializableField()
    reverse_working_voltage: ApiParamT = SerializableField()
    reverse_leakage_current: ApiParamT = SerializableField()
    max_current: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class TVSParams(DiodeParams):
    endpoint: str = "tvs"
    reverse_breakdown_voltage: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class LEDParams(DiodeParams):
    endpoint: str = "leds"
    max_brightness: ApiParamT = SerializableField()
    color: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class LDOParams(BaseParams):
    endpoint: str = "ldos"
    max_input_voltage: ApiParamT = SerializableField()
    output_voltage: ApiParamT = SerializableField()
    quiescent_current: ApiParamT = SerializableField()
    dropout_voltage: ApiParamT = SerializableField()
    # psrr: ApiParamT = SerializableField()  # TODO
    output_polarity: ApiParamT = SerializableField()
    output_type: ApiParamT = SerializableField()
    output_current: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class MOSFETParams(BaseParams):
    endpoint: str = "mosfets"
    channel_type: ApiParamT = SerializableField()
    # saturation_type: ApiParamT = SerializableField()  # TODO
    gate_source_threshold_voltage: ApiParamT = SerializableField()
    max_drain_source_voltage: ApiParamT = SerializableField()
    max_continuous_drain_current: ApiParamT = SerializableField()
    on_resistance: ApiParamT = SerializableField()


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

        if logger.isEnabledFor(logging.DEBUG):
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

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"POST {self.config.api_url}{url}\n{json.dumps(data, indent=2)}\n->\n"
                f"{json.dumps(response.json(), indent=2)}"
            )

        return response

    @staticmethod
    def ComponentFromResponse(kw: dict) -> "Component":
        from faebryk.libs.picker.jlcpcb.jlcpcb import Component

        # TODO very ugly fix
        kw["extra"] = json.dumps(kw["extra"])
        return Component(**kw)

    @once
    def fetch_part_by_lcsc(self, lcsc: int) -> list["Component"]:
        response = self._get(f"/v0/component/lcsc/{lcsc}")
        return [
            self.ComponentFromResponse(part) for part in response.json()["components"]
        ]

    @once
    def fetch_part_by_mfr(self, mfr: str, mfr_pn: str) -> list["Component"]:
        response = self._get(f"/v0/component/mfr/{mfr}/{mfr_pn}")
        return [
            self.ComponentFromResponse(part) for part in response.json()["components"]
        ]

    def query_parts(self, method: str, params: BaseParams) -> list["Component"]:
        response = self._post(f"/v0/query/{method}", params.serialize())
        return [
            self.ComponentFromResponse(part) for part in response.json()["components"]
        ]

    @once
    def fetch_parts(self, params: BaseParams) -> list["Component"]:
        assert params.endpoint
        return self.query_parts(params.endpoint, params)


@functools.lru_cache
def get_api_client() -> ApiClient:
    return ApiClient()
