# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
import sys
from dataclasses import dataclass
from importlib.metadata import version as get_package_version

import requests

import faebryk.library._F as F
from atopile.config import config
from faebryk.libs.picker.api.models import (
    BaseParams,
    Component,
    LCSCParams,
    ManufacturerPartParams,
)
from faebryk.libs.util import ConfigFlag, once

logger = logging.getLogger(__name__)

DEFAULT_API_TIMEOUT_SECONDS = 30

API_LOG = ConfigFlag("API_LOG", descr="Log API calls (very verbose)", default=False)


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


class ApiClient:
    @dataclass
    class ApiConfig:
        api_url: str = config.project.services.components.url
        api_key: str | None = None

    def __init__(self):
        self._client = requests.Session()
        self._client.headers.update(
            {
                "User-Agent": (
                    f"atopile/{get_package_version('atopile')} "
                    f"({sys.platform}; "
                    f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})"
                ),
            }
        )

    @property
    @once
    def _cfg(self) -> ApiConfig:
        return self.ApiConfig()

    @property
    @once
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._cfg.api_key}"}

    def _get(self, url: str, timeout: float = 10) -> requests.Response:
        try:
            response = self._client.get(
                f"{self._cfg.api_url}{url}",
                timeout=timeout,
                headers=self._headers,
                verify=not config.project.dangerously_skip_ssl_verification,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ApiHTTPError(e) from e

        if API_LOG:
            logger.debug(
                "GET %s%s\n->\n%s",
                self._cfg.api_url,
                url,
                json.dumps(response.json(), indent=2),
            )
        else:
            logger.debug("GET %s%s", self._cfg.api_url, url)

        return response

    def _post(
        self, url: str, data: dict, timeout: float = DEFAULT_API_TIMEOUT_SECONDS
    ) -> requests.Response:
        try:
            response = self._client.post(
                f"{self._cfg.api_url}{url}",
                json=data,
                timeout=timeout,
                headers=self._headers,
                verify=not config.project.dangerously_skip_ssl_verification,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ApiHTTPError(e) from e

        if API_LOG:
            logger.debug(
                "POST %s%s\n%s\n->\n%s",
                self._cfg.api_url,
                url,
                json.dumps(data, indent=2),
                json.dumps(response.json(), indent=2),
            )
        else:
            logger.debug(
                "POST %s%s\n%s", self._cfg.api_url, url, json.dumps(data, indent=2)
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

    def query_parts(
        self, method: F.is_pickable_by_type.Endpoint, params: BaseParams
    ) -> list["Component"]:
        response = self._post(f"/v0/query/{method}", params.serialize())
        return [Component.from_dict(part) for part in response.json()["components"]]  # type: ignore

    @once
    def fetch_parts(self, params: BaseParams) -> list["Component"]:
        assert params.endpoint
        return self.query_parts(params.endpoint, params)

    def fetch_parts_multiple(
        self, params: list[BaseParams | LCSCParams | ManufacturerPartParams]
    ) -> list[list["Component"]]:
        # TODO: batch queries
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
