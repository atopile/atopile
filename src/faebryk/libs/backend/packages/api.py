# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import sys
from dataclasses import dataclass
from importlib.metadata import version as get_package_version
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import requests
from dataclasses_json.api import dataclass_json
from github_oidc.client import get_actions_header
from pydantic.networks import HttpUrl

from atopile.config import config
from faebryk.libs.package.artifacts import Artifacts
from faebryk.libs.package.dist import Dist
from faebryk.libs.util import indented_container, once

logger = logging.getLogger(__name__)


class _Models:
    class Publish:
        @dataclass_json
        @dataclass(frozen=True)
        class Request:
            identifier: str
            package_version: str
            git_ref: str | None
            package_size: int
            artifacts_size: int | None
            manifest: dict[str, Any]
            """
            contents of the `ato.yaml` file
            """

        @dataclass_json
        @dataclass(frozen=True)
        class Response:
            @dataclass_json
            @dataclass(frozen=True)
            class Info:
                url: HttpUrl
                fields: dict[str, str]

            status: Literal["ok"]
            release_id: str
            upload_info: Info
            artifacts_upload_info: Info

    class PublishUploadComplete:
        @dataclass_json
        @dataclass(frozen=True)
        class Request:
            release_id: str

        @dataclass_json
        @dataclass(frozen=True)
        class Response:
            status: Literal["ok"]
            url: str

    class Package:
        @dataclass_json
        @dataclass(frozen=True)
        class Response:
            @dataclass_json
            @dataclass(frozen=True)
            class Info:
                version: str

            info: Info

    class Release:
        @dataclass_json
        @dataclass(frozen=True)
        class Response:
            @dataclass_json
            @dataclass(frozen=True)
            class Info:
                # @dataclass_json
                # @dataclass(frozen=True)
                # class Dependencies:
                #     @dataclass_json
                #     @dataclass(frozen=True)
                #     class Dependency:
                #         identifier: str
                #         version: str

                #     requires: list[Dependency]

                # dependencies: Dependencies
                download_url: str
                # requires_atopile: str
                filename: str

            info: Info


class Errors:
    class PackagesApiError(Exception): ...

    class PackagesApiHTTPError(Exception):
        def __init__(self, error: requests.exceptions.HTTPError, detail: str):
            super().__init__()
            self.error = error
            self.response = error.response
            self.detail = detail

        @classmethod
        def from_http(cls, error: "Errors.PackagesApiHTTPError"):
            return cls(error.error, error.detail)

        @property
        def code(self) -> int:
            return self.response.status_code

        def __str__(self) -> str:
            return f"{type(self).__name__}: {self.code} {self.detail}"

    class AuthenticationError(PackagesApiError): ...

    class PackageNotFoundError(PackagesApiHTTPError):
        def __init__(
            self,
            error: requests.exceptions.HTTPError,
            detail: str,
            package_identifier: str,
        ):
            super().__init__(error, detail)
            self.package_identifier = package_identifier

        def __str__(self) -> str:
            return f"{type(self).__name__}: {self.package_identifier}: {self.detail}"

        @classmethod
        def from_http(
            cls, error: "Errors.PackagesApiHTTPError", package_identifier: str
        ):
            return cls(error.error, error.detail, package_identifier)

    class InvalidPackageIdentifierError(PackagesApiHTTPError):
        def __init__(
            self,
            error: requests.exceptions.HTTPError,
            detail: str,
            package_identifier: str,
        ):
            super().__init__(error, detail)
            self.package_identifier = package_identifier

        def __str__(self) -> str:
            return f"{type(self).__name__}: {self.package_identifier}: {self.detail}"

        @classmethod
        def from_http(
            cls, error: "Errors.PackagesApiHTTPError", package_identifier: str
        ):
            return cls(error.error, error.detail, package_identifier)

    class ReleaseNotFoundError(PackagesApiHTTPError):
        def __init__(
            self,
            error: requests.exceptions.HTTPError,
            detail: str,
            package_identifier: str,
            release: str,
        ):
            super().__init__(error, detail)
            self.package_identifier = package_identifier
            self.release = release

        def __str__(self) -> str:
            return (
                f"{type(self).__name__}: {self.package_identifier}@{self.release}:"
                f" {self.detail}"
            )

        @classmethod
        def from_http(
            cls,
            error: "Errors.PackagesApiHTTPError",
            package_identifier: str,
            release: str,
        ):
            return cls(error.error, error.detail, package_identifier, release)

    class ReleaseAlreadyExistsError(PackagesApiHTTPError): ...


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
        self._client.headers.update(
            {
                "User-Agent": (
                    f"atopile/{get_package_version('atopile')} "
                    f"({sys.platform}; "
                    f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})"
                ),
            }
        )

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
            raise Errors.PackagesApiHTTPError(e, detail) from e
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
            raise Errors.PackagesApiHTTPError(e, detail) from e
        return response

    def _upload(
        self,
        url: str,
        file_path: Path,
        data: dict[str, str],
        timeout: float = 10,
        skip_verify: bool = False,
    ) -> requests.Response:
        response = self._client.post(
            url,
            data=data,
            files={
                "file": (file_path.name, file_path.read_bytes()),
                "Content-Type": "application/zip",
            },
            timeout=timeout,
            verify=not skip_verify,
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                detail = response.json()["detail"]
            except (requests.JSONDecodeError, KeyError):
                detail = response.text
            raise Errors.PackagesApiHTTPError(e, detail) from e
        return response

    def _authenticate(self) -> dict[str, str]:
        """
        Currently, the only supported authentication method is Github Actions OIDC.
        """
        try:
            return get_actions_header(urlparse(self._cfg.api_url).netloc)
        except Exception as e:
            raise Errors.AuthenticationError(e) from e

    def publish(
        self,
        identifier: str,
        version: str,
        git_ref: str | None,
        dist: Dist,
        artifacts: Artifacts | None,
        skip_auth: bool = False,
    ) -> _Models.PublishUploadComplete.Response:
        """
        Publish a package to the package registry.

        Only works in Github Actions.
        """
        ## Request upload
        try:
            r = self._post(
                "/v1/publish",
                data=_Models.Publish.Request(
                    identifier=identifier,
                    package_version=version,
                    git_ref=git_ref,
                    package_size=dist.bytes,
                    artifacts_size=artifacts.bytes if artifacts else None,
                    manifest=dist.manifest.model_dump(mode="json"),
                ).to_dict(),  # type: ignore
                authenticate=not skip_auth,
            )
        except Errors.PackagesApiHTTPError as e:
            if e.code == 409:
                raise Errors.ReleaseAlreadyExistsError.from_http(e) from e
            raise

        response = _Models.Publish.Response.from_dict(r.json())  # type: ignore

        ## Upload the package
        try:
            r = self._upload(
                url=response.upload_info.url,
                file_path=dist.path,
                data=response.upload_info.fields,
                skip_verify=skip_auth,
            )
        except Errors.PackagesApiHTTPError:
            raise

        ## Upload the artifacts
        if artifacts:
            try:
                r = self._upload(
                    url=response.artifacts_upload_info.url,
                    file_path=artifacts.path,
                    data=response.artifacts_upload_info.fields,
                    skip_verify=skip_auth,
                )
            except Errors.PackagesApiHTTPError:
                raise

        ## Confirm upload
        try:
            r = self._post(
                "/v1/publish/upload-complete",
                data=_Models.PublishUploadComplete.Request(
                    release_id=response.release_id,
                ).to_dict(),  # type: ignore
                authenticate=not skip_auth,
            )
        except Errors.PackagesApiHTTPError:
            raise

        response = _Models.PublishUploadComplete.Response.from_dict(r.json())  # type: ignore
        return response

    def package(
        self, identifier: str, version: str | None = None
    ) -> _Models.Release.Response:
        """
        Get a package from the package registry.
        """
        if version is None:
            try:
                r = self._get(f"/v1/package/{identifier}")
            except Errors.PackagesApiHTTPError as e:
                if e.code == 404:
                    raise Errors.PackageNotFoundError.from_http(e, identifier) from e
                if e.code == 422:
                    raise Errors.InvalidPackageIdentifierError.from_http(
                        e, identifier
                    ) from e
                raise
            response = _Models.Package.Response.from_dict(r.json())  # type: ignore
            assert isinstance(response, _Models.Package.Response)
            version = response.info.version

        try:
            r = self._get(f"/v1/package/{identifier}/releases/{version}")
        except Errors.PackagesApiHTTPError as e:
            if e.code == 404:
                raise Errors.ReleaseNotFoundError.from_http(
                    e, identifier, version
                ) from e
            raise
        try:
            response = _Models.Release.Response.from_dict(r.json())  # type: ignore
        except Exception:
            logger.error(indented_container(r.json(), recursive=True))
            raise
        return response

    def release_dist(
        self, identifier: str, output_path: Path, version: str | None = None
    ) -> Dist:
        release = self.package(identifier, version)
        url = release.info.download_url
        filepath = output_path / release.info.filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        # use requests to download the file to output_path
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with filepath.open("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        return Dist(filepath)
