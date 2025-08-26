# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from importlib.metadata import version as get_package_version
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import requests
from dataclasses_json import config as dataclasses_json_config
from dataclasses_json.api import dataclass_json

from atopile.config import config
from faebryk.libs.package.artifacts import Artifacts
from faebryk.libs.package.dist import Dist
from faebryk.libs.util import indented_container, once

logger = logging.getLogger(__name__)


_EXCLUDE_FROM_JSON = dataclasses_json_config(exclude=lambda _: True)


class _Type(Enum):
    GET = auto()
    POST = auto()


class _Schemas:
    @dataclass_json
    @dataclass(frozen=True)
    class Author:
        name: str
        email: str

    @dataclass_json
    @dataclass(frozen=True)
    class PackageStats:
        total_downloads: int | None
        this_week_downloads: int | None
        this_month_downloads: int | None

    @dataclass_json
    @dataclass(frozen=True)
    class FileHashes:
        sha256: str

    @dataclass_json
    @dataclass(frozen=True)
    class RegistryDependencySpec:
        identifier: str
        type: Literal["registry"] = "registry"
        release: str | None = None

    @dataclass_json
    @dataclass(frozen=True)
    class PackageDependencies:
        requires: list["_Schemas.RegistryDependencySpec"]

    @dataclass_json
    @dataclass(frozen=True)
    class ArtifactInfo:
        filename: str
        url: str
        size: int
        hashes: "_Schemas.FileHashes"
        build_name: str | None = None

    @dataclass_json
    @dataclass(frozen=True)
    class ArtifactsInfo:
        artifacts: list["_Schemas.ArtifactInfo"]

    @dataclass_json
    @dataclass(frozen=True)
    class LayoutInfo:
        build_name: str
        url: str

    @dataclass_json
    @dataclass(frozen=True)
    class LayoutsInfo:
        layouts: list["_Schemas.LayoutInfo"]

    @dataclass_json
    @dataclass(frozen=True)
    class PackageReleaseInfo:
        created_at: datetime = field(
            metadata=dataclasses_json_config(decoder=datetime.fromisoformat)
        )
        released_at: datetime = field(
            metadata=dataclasses_json_config(decoder=datetime.fromisoformat)
        )
        key: str = field(metadata=_EXCLUDE_FROM_JSON)
        identifier: str
        version: str
        repository: str
        authors: list["_Schemas.Author"]
        license: str
        summary: str
        homepage: str | None
        readme_url: str | None = field(metadata=_EXCLUDE_FROM_JSON)
        url: str
        stats: "_Schemas.PackageStats"
        hashes: "_Schemas.FileHashes"
        filename: str
        git_ref: str | None
        requires_atopile: str
        size: int
        download_url: str = field(metadata=_EXCLUDE_FROM_JSON)
        builds: list[str] | None
        dependencies: "_Schemas.PackageDependencies"
        artifacts: "_Schemas.ArtifactsInfo | None"
        layouts: "_Schemas.LayoutsInfo | None"
        yanked_at: str | None
        yanked_reason: str | None

    @dataclass_json
    @dataclass(frozen=True)
    class Package:
        info: "_Schemas.PackageInfo"
        readme: str | None

    @dataclass_json
    @dataclass(frozen=True)
    class PackageRelease:
        info: "_Schemas.PackageReleaseInfo"
        readme: str | None

    @dataclass_json
    @dataclass(frozen=True)
    class PackageInfo:
        created_at: datetime | str
        released_at: datetime | str
        key: str
        identifier: str
        version: str
        repository: str
        authors: list["_Schemas.Author"]
        license: str
        summary: str
        homepage: str | None
        readme_url: str | None
        url: str
        stats: "_Schemas.PackageStats"

    @dataclass_json
    @dataclass(frozen=True)
    class PackageInfoBrief:
        identifier: str
        version: str
        summary: str
        url: str
        repository: str
        homepage: str | None

    @dataclass_json
    @dataclass(frozen=True)
    class QueryResult:
        packages: list["_Schemas.PackageInfoBrief"]

    @dataclass_json
    @dataclass(frozen=True)
    class PresignedUploadInfo:
        url: str
        fields: dict[str, str]

    @dataclass_json
    @dataclass(frozen=True)
    class PublishRequest:
        identifier: str
        package_version: str
        git_ref: str | None
        package_size: int
        artifacts_size: int | None
        manifest: dict[str, Any]

    @dataclass_json
    @dataclass(frozen=True)
    class PublishRequestResponse:
        release_id: str
        upload_info: "_Schemas.PresignedUploadInfo"
        artifacts_upload_info: "_Schemas.PresignedUploadInfo"
        status: Literal["ok"] = "ok"

    @dataclass_json
    @dataclass(frozen=True)
    class PublishCompletedResponse:
        url: str
        status: Literal["ok"] = "ok"

    @dataclass_json
    @dataclass(frozen=True)
    class UploadCompleteRequest:
        release_id: str

    @dataclass_json
    @dataclass(frozen=True)
    class ValidationError:
        loc: list[str | int]
        msg: str
        type: str

    @dataclass_json
    @dataclass(frozen=True)
    class HTTPValidationError:
        detail: list["_Schemas.ValidationError"]

    @dataclass_json
    @dataclass(frozen=True)
    class PackageReleases:
        releases: list["_Schemas.PackageReleaseInfo"]


class _Endpoints:
    class PackageReleases:
        TYPE = _Type.GET

        @staticmethod
        def url(request: "_Endpoints.PackageReleases.Request") -> str:
            return f"/v1/package/{request.identifier}/releases"

        @dataclass_json
        @dataclass(frozen=True)
        class Request:
            identifier: str

        Response = _Schemas.PackageReleases

    class PackageRelease:
        TYPE = _Type.GET

        @staticmethod
        def url(request: "_Endpoints.PackageRelease.Request") -> str:
            return f"/v1/package/{request.identifier}/releases/{request.version}"

        @dataclass_json
        @dataclass(frozen=True)
        class Request:
            identifier: str
            version: str

        Response = _Schemas.PackageRelease

    class Package:
        TYPE = _Type.GET

        @staticmethod
        def url(request: "_Endpoints.Package.Request") -> str:
            return f"/v1/package/{request.identifier}"

        @dataclass_json
        @dataclass(frozen=True)
        class Request:
            identifier: str

        Response = _Schemas.Package

    class Packages:
        TYPE = _Type.GET

        @staticmethod
        def url(request: "_Endpoints.Packages.Request") -> str:
            return f"/v1/packages?query={request.query}"

        @dataclass_json
        @dataclass(frozen=True)
        class Request:
            query: str

        Response = _Schemas.QueryResult

    class Publish:
        TYPE = _Type.POST

        @staticmethod
        def url() -> str:
            return "/v1/publish"

        Request = _Schemas.PublishRequest
        Response = _Schemas.PublishRequestResponse

    class PublishUploadComplete:
        TYPE = _Type.POST

        @staticmethod
        def url() -> str:
            return "/v1/publish/upload-complete"

        Request = _Schemas.UploadCompleteRequest
        Response = _Schemas.PublishCompletedResponse


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
        def from_http(  # type: ignore
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
        def from_http(  # type: ignore
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
        def from_http(  # type: ignore
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
        response = self._client.get(
            f"{self._cfg.api_url}{url}",
            timeout=timeout,
            verify=not config.project.dangerously_skip_ssl_verification,
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
            verify=not config.project.dangerously_skip_ssl_verification,
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
            from github_oidc.client import get_actions_header

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
    ) -> _Endpoints.PublishUploadComplete.Response:
        """
        Publish a package to the package registry.

        Only works in Github Actions.
        """
        ## Request upload
        try:
            r = self._post(
                _Endpoints.Publish.url(),
                data=_Endpoints.Publish.Request(
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

        response = _Endpoints.Publish.Response.from_dict(r.json())  # type: ignore

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
                _Endpoints.PublishUploadComplete.url(),
                data=_Endpoints.PublishUploadComplete.Request(
                    release_id=response.release_id,
                ).to_dict(),  # type: ignore
                authenticate=not skip_auth,
            )
        except Errors.PackagesApiHTTPError:
            raise

        response = _Endpoints.PublishUploadComplete.Response.from_dict(r.json())  # type: ignore
        return response

    def get_package(
        self, identifier: str, version: str | None = None
    ) -> _Endpoints.PackageRelease.Response:
        """
        Get a package from the package registry.
        """
        if version is None:
            try:
                r = self._get(
                    _Endpoints.Package.url(_Endpoints.Package.Request(identifier))
                )
            except Errors.PackagesApiHTTPError as e:
                if e.code == 404:
                    raise Errors.PackageNotFoundError.from_http(e, identifier) from e
                if e.code == 422:
                    raise Errors.InvalidPackageIdentifierError.from_http(
                        e, identifier
                    ) from e
                raise
            response = _Endpoints.Package.Response.from_dict(r.json())  # type: ignore
            assert isinstance(response, _Endpoints.Package.Response)
            version = response.info.version

        try:
            r = self._get(
                _Endpoints.PackageRelease.url(
                    _Endpoints.PackageRelease.Request(identifier, version)
                )
            )
        except Errors.PackagesApiHTTPError as e:
            if e.code == 404:
                raise Errors.ReleaseNotFoundError.from_http(
                    e, identifier, version
                ) from e
            raise
        try:
            response = _Endpoints.PackageRelease.Response.from_dict(r.json())  # type: ignore
        except Exception:
            logger.error(indented_container(r.json(), recursive=True))
            raise
        return response

    def get_release_dist(
        self, identifier: str, output_path: Path, version: str | None = None
    ) -> Dist:
        release = self.get_package(identifier, version)
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

    def query_packages(self, query: str) -> _Endpoints.Packages.Response:
        r = self._get(_Endpoints.Packages.url(_Endpoints.Packages.Request(query)))
        return _Endpoints.Packages.Response.from_dict(r.json())  # type: ignore
