# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
import time
from dataclasses import dataclass

import requests

from faebryk.core.module import Module
from faebryk.libs.picker.api.models import (
    BaseParams,
    Component,
    LCSCParams,
    ManufacturerPartParams,
    PackageCandidate,
)
from faebryk.libs.util import ConfigFlagString, once

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
        now = time.time()
        try:
            response = self._client.post(
                f"{self.config.api_url}{url}", json=data, timeout=timeout
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ApiHTTPError(e) from e
        finally:
            logger.info(f"Backend query took {time.time() - now:.3f} seconds")

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"POST {self.config.api_url}{url}\n{json.dumps(data, indent=2)}\n->\n"
                f"{json.dumps(response.json(), indent=2)}"
            )

        return response

    @once
    def fetch_part_by_lcsc(self, lcsc: int) -> list["Component"]:
        response = self._get(f"/v0/component/lcsc/{lcsc}")
        return [Component.from_dict(part) for part in response.json()["components"]]  # type: ignore

    @once
    def fetch_part_by_mfr(self, mfr: str, mfr_pn: str) -> list["Component"]:
        response = self._get(f"/v0/component/mfr/{mfr}/{mfr_pn}")
        return [Component.from_dict(part) for part in response.json()["components"]]  # type: ignore

    def query_parts(self, method: str, params: BaseParams) -> list["Component"]:
        response = self._post(f"/v0/query/{method}", params.serialize())
        return [Component.from_dict(part) for part in response.json()["components"]]  # type: ignore

    @once
    def fetch_parts(self, params: BaseParams) -> list["Component"]:
        assert params.endpoint
        return self.query_parts(params.endpoint, params)

    def fetch_parts_multiple(
        self, params: list[BaseParams | LCSCParams | ManufacturerPartParams]
    ) -> list[list["Component"]]:
        response = self._post("/v0/query", {"queries": [p.serialize() for p in params]})
        results = [
            [Component.from_dict(part) for part in result["components"]]  # type: ignore
            for result in response.json()["results"]
        ]

        if len(results) != len(params):
            raise ApiError(f"Expected {len(params)} results, got {len(results)}")

        return results


@once
def get_api_client() -> ApiClient:
    return ApiClient()
