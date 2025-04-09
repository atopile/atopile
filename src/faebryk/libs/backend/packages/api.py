# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from dataclasses_json.api import dataclass_json
from github_oidc.client import get_actions_header

from atopile.config import config
from faebryk.libs.package.dist import Dist
from faebryk.libs.util import once

logger = logging.getLogger(__name__)


class _Models:
    class Publish:
        @dataclass_json
        @dataclass(frozen=True)
        class Request:
            identifier: str
            package_version: str
            manifest: dict[str, Any]
            """
            contents of the `ato.yaml` file
            """

        @dataclass_json
        @dataclass(frozen=True)
        class Response:
            upload_url: str
            release_id: str

    class PublishUploadComplete:
        @dataclass_json
        @dataclass(frozen=True)
        class Request:
            release_id: str

        @dataclass_json
        @dataclass(frozen=True)
        class Response:
            url: str

    class Package:
        @dataclass_json
        @dataclass(frozen=True)
        class Response:
            version: str

    class Release:
        @dataclass_json
        @dataclass(frozen=True)
        class Response:
            @dataclass_json
            @dataclass(frozen=True)
            class Dependencies:
                @dataclass_json
                @dataclass(frozen=True)
                class Dependency:
                    name: str
                    version: str

                requires: list[Dependency]

            dependencies: Dependencies
            download_url: str
            requires_atopile: str


class _Errors:
    class PackagesApiError(Exception): ...

    class PackagesApiHTTPError(Exception):
        def __init__(self, error: requests.exceptions.HTTPError, detail: str):
            super().__init__()
            self.error = error
            self.response = error.response

        @classmethod
        def from_http(cls, error: "_Errors.PackagesApiHTTPError", detail: str):
            return cls(error.error, detail)

        @property
        def code(self) -> int:
            return self.response.status_code

    class AuthenticationError(PackagesApiError): ...

    class PackageNotFoundError(PackagesApiHTTPError): ...

    class ReleaseNotFoundError(PackagesApiHTTPError): ...


class PackagesAPIClient:
    @dataclass
    class ApiConfig:
        api_url: str = config.project.services.packages.url

    @property
    @once
    def _cfg(self) -> ApiConfig:
        return self.ApiConfig()

    def __init__(self):
        self._client = requests.Session()

    def _get(
        self,
        url: str,
        timeout: float = 10,
    ) -> requests.Response:
        response = self._client.get(f"{self._cfg.api_url}{url}", timeout=timeout)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                detail = response.json()["detail"]
            except (requests.JSONDecodeError, KeyError):
                detail = response.text
            raise _Errors.PackagesApiHTTPError(e, detail) from e
        return response

    def _post(
        self,
        url: str,
        data: Any,
        timeout: float = 10,
        authenticate: bool = False,
    ) -> requests.Response:
        headers = {}
        if authenticate:
            headers |= self._authenticate()

        response = self._client.post(
            f"{self._cfg.api_url}{url}",
            json=data,
            timeout=timeout,
            headers=headers,
        )
        try:
            response.raise_for_status()
            assert response.json()["status"] == "ok"
        except requests.exceptions.HTTPError as e:
            try:
                detail = response.json()["detail"]
            except (requests.JSONDecodeError, KeyError):
                detail = response.text
            raise _Errors.PackagesApiHTTPError(e, detail) from e
        return response

    @staticmethod
    def _upload(
        url: str,
        file_path: Path,
        timeout: float = 10,
        skip_verify: bool = False,
    ) -> requests.Response:
        response = requests.put(
            url,
            files={"file": file_path.read_bytes(), "Content-Type": "application/zip"},
            timeout=timeout,
            verify=not skip_verify,
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise _Errors.PackagesApiHTTPError(e, detail="") from e
        return response

    def _authenticate(self) -> dict[str, str]:
        """
        Currently, the only supported authentication method is Github Actions OIDC.
        """
        try:
            return get_actions_header(urlparse(self._cfg.api_url).netloc)
        except Exception as e:
            raise _Errors.AuthenticationError(e) from e

    def publish(
        self, identifier: str, version: str, dist: Dist, skip_auth: bool = False
    ) -> _Models.PublishUploadComplete.Response:
        """
        Publish a package to the package registry.

        Only works in Github Actions.
        """
        ## Request upload
        r = self._post(
            "/v1/publish",
            data=_Models.Publish.Request(
                identifier=identifier,
                package_version=version,
                manifest=dist.manifest,
            ).to_dict(),  # type: ignore
            authenticate=not skip_auth,
        )
        response = _Models.Publish.Response.from_dict(r.json())  # type: ignore

        ## Upload the package
        self._upload(response.upload_url, dist.path, skip_verify=skip_auth)

        ## Confirm upload
        r = self._post(
            "/v1/publish/upload-complete",
            data=_Models.PublishUploadComplete.Request(
                release_id=response.release_id,
            ).to_dict(),  # type: ignore
            authenticate=not skip_auth,
        )
        response = _Models.PublishUploadComplete.Response.from_dict(r.json())  # type: ignore
        return response

    def package(self, identifier: str) -> _Models.Package.Response:
        """
        Get a package from the package registry.
        """
        if "@" in identifier:
            identifier, version = identifier.split("@", 1)
        else:
            try:
                r = self._get(f"/v1/package/{identifier}")
            except _Errors.PackagesApiHTTPError as e:
                if e.code == 404:
                    raise _Errors.PackageNotFoundError.from_http(e, detail="") from e
                raise
            response = _Models.Package.Response.from_dict(r.json())  # type: ignore
            version = response.version

        try:
            r = self._get(f"/v1/package/{identifier}/releases/{version}")
        except _Errors.PackagesApiHTTPError as e:
            if e.code == 404:
                raise _Errors.ReleaseNotFoundError.from_http(e, detail="") from e
            raise
        response = _Models.Release.Response.from_dict(r.json())  # type: ignore

        return response
