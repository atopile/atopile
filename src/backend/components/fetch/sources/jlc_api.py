from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import string
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from ..config import FetchConfig

_NONCE_CHARS = string.ascii_letters + string.digits


class JlcApiError(RuntimeError):
    pass


def _canonical_path(path_or_url: str) -> str:
    parsed = urlsplit(path_or_url)
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def _canonical_json(payload: dict[str, object]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _unix_timestamp() -> int:
    return int(time.time())


def _nonce_32() -> str:
    return "".join(secrets.choice(_NONCE_CHARS) for _ in range(32))


def _build_string_to_sign(
    *, method: str, path: str, timestamp: int, nonce: str, body: str
) -> str:
    return f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body}\n"


def _sign_hmac_sha256_base64(*, secret: str, payload: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


class JlcApiClient:
    def __init__(
        self,
        config: FetchConfig,
        *,
        client: httpx.Client | None = None,
        timestamp_factory: Callable[[], int] = _unix_timestamp,
        nonce_factory: Callable[[], str] = _nonce_32,
    ):
        self.config = config
        self._client = client or httpx.Client(
            base_url=config.jlc_api_base_url.rstrip("/"),
            timeout=config.request_timeout_s,
        )
        self._owns_client = client is None
        self._timestamp_factory = timestamp_factory
        self._nonce_factory = nonce_factory
        self.last_trace_id: str | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> JlcApiClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _credentials(self) -> tuple[str, str, str]:
        missing = self.config.missing_jlc_credentials()
        if missing:
            missing_csv = ", ".join(missing)
            raise JlcApiError(f"Missing required env vars: {missing_csv}")

        assert self.config.jlc_app_id is not None
        assert self.config.jlc_access_key is not None
        assert self.config.jlc_secret_key is not None
        return (
            self.config.jlc_app_id,
            self.config.jlc_access_key,
            self.config.jlc_secret_key,
        )

    def _build_authorization_header(
        self,
        *,
        method: str,
        path_or_url: str,
        canonical_body: str,
        timestamp: int,
        nonce: str,
    ) -> str:
        app_id, access_key, secret_key = self._credentials()
        path = _canonical_path(path_or_url)
        string_to_sign = _build_string_to_sign(
            method=method,
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body=canonical_body,
        )
        signature = _sign_hmac_sha256_base64(secret=secret_key, payload=string_to_sign)
        return (
            f'JOP appid="{app_id}",accesskey="{access_key}",'
            f'timestamp="{timestamp}",nonce="{nonce}",signature="{signature}"'
        )

    def _signed_post(self, *, path: str, body: dict[str, object]) -> httpx.Response:
        canonical_body = _canonical_json(body)
        timestamp = self._timestamp_factory()
        nonce = self._nonce_factory()
        authorization = self._build_authorization_header(
            method="POST",
            path_or_url=path,
            canonical_body=canonical_body,
            timestamp=timestamp,
            nonce=nonce,
        )
        return self._client.post(
            path,
            content=canonical_body.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": authorization,
            },
        )

    def _parse_response_payload(
        self, response: httpx.Response, *, context: str
    ) -> dict[str, object]:
        trace_id = response.headers.get("J-Trace-ID")
        if trace_id:
            self.last_trace_id = trace_id

        try:
            payload = response.json()
        except ValueError as ex:
            raise JlcApiError(
                f"{context} did not return valid JSON; "
                f"http={response.status_code} trace={trace_id or '-'}"
            ) from ex

        if not isinstance(payload, dict):
            raise JlcApiError(
                f"{context} did not return an object payload; "
                f"http={response.status_code} trace={trace_id or '-'}"
            )

        if response.status_code != 200:
            raise JlcApiError(
                f"{context} failed; http={response.status_code} "
                f"trace={trace_id or '-'} payload={payload}"
            )

        code = payload.get("code")
        success = payload.get("success")
        if success is False or (code is not None and str(code) != "200"):
            raise JlcApiError(
                f"{context} business error; code={code} "
                f"message={payload.get('message')} trace={trace_id or '-'}"
            )

        return payload

    def get_component_page(self, *, last_key: str | None = None) -> dict[str, object]:
        body: dict[str, object] = {}
        if last_key:
            body["lastKey"] = last_key

        response = self._signed_post(
            path=self.config.jlc_component_infos_path,
            body=body,
        )
        payload = self._parse_response_payload(
            response, context="JLC component page request"
        )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise JlcApiError(f"Invalid component page payload: {payload}")
        return data

    def get_component_detail(self, lcsc_part: str | int) -> dict[str, object]:
        lcsc_part_str = str(lcsc_part).strip()
        if lcsc_part_str.isdigit():
            lcsc_part_str = f"C{lcsc_part_str}"

        body = {"componentCode": lcsc_part_str}
        response = self._signed_post(
            path=self.config.jlc_component_detail_path,
            body=body,
        )
        payload = self._parse_response_payload(
            response,
            context="JLC component detail request",
        )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise JlcApiError(f"Invalid component detail payload: {payload}")
        return data

    def iter_component_infos(self, *, max_pages: int | None = None) -> Iterator[dict]:
        last_key: str | None = None
        pages = 0
        while True:
            page = self.get_component_page(last_key=last_key)
            component_infos = page.get("componentInfos")
            if not component_infos:
                return
            if not isinstance(component_infos, list):
                raise JlcApiError(f"Invalid componentInfos payload: {page}")
            for component in component_infos:
                if isinstance(component, dict):
                    yield component

            pages += 1
            if max_pages is not None and pages >= max_pages:
                return

            next_last_key = page.get("lastKey")
            if not next_last_key or next_last_key == last_key:
                return
            last_key = str(next_last_key)

    def iter_target_component_infos(
        self, *, max_pages: int | None = None
    ) -> Iterator[dict]:
        target = set(self.config.target_categories)
        for component in self.iter_component_infos(max_pages=max_pages):
            if component.get("firstCategory") in target:
                yield component


def test_jlc_api_client_signs_requests_and_filters_targets() -> None:
    captured_requests: list[tuple[str, str, str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8")
        auth = request.headers["Authorization"]
        captured_requests.append(
            (
                request.url.path,
                body,
                auth,
                request.headers.get("Content-Type", ""),
            )
        )

        if body == "{}":
            return httpx.Response(
                200,
                headers={"J-Trace-ID": "trace-1"},
                json={
                    "code": 200,
                    "success": True,
                    "data": {
                        "lastKey": "page-1",
                        "componentInfos": [
                            {"lcscPart": "C1", "firstCategory": "Resistors"},
                            {"lcscPart": "C2", "firstCategory": "ICs"},
                        ],
                    },
                },
            )

        if body == '{"lastKey":"page-1"}':
            return httpx.Response(
                200,
                headers={"J-Trace-ID": "trace-2"},
                json={
                    "code": 200,
                    "success": True,
                    "data": {
                        "lastKey": None,
                        "componentInfos": [
                            {"lcscPart": "C3", "firstCategory": "Capacitors"}
                        ],
                    },
                },
            )

        return httpx.Response(400, json={"message": "unexpected request body"})

    first_nonce = "A" * 32
    second_nonce = "B" * 32
    nonce_values = iter((first_nonce, second_nonce))
    transport = httpx.MockTransport(handler)
    client = httpx.Client(base_url="https://open.jlcpcb.com", transport=transport)
    config = FetchConfig(
        cache_dir=Path("/tmp/atopile-components-test"),
        jlc_api_base_url="https://open.jlcpcb.com",
        jlc_app_id="app-id",
        jlc_access_key="access-key",
        jlc_secret_key="secret-key",
        jlc_component_infos_path="/overseas/openapi/component/getComponentInfos",
        jlc_component_detail_path="/overseas/openapi/component/getComponentDetail",
        request_timeout_s=10.0,
        target_categories=("Resistors", "Capacitors"),
    )

    with JlcApiClient(
        config,
        client=client,
        timestamp_factory=lambda: 1700000000,
        nonce_factory=lambda: next(nonce_values),
    ) as api:
        parts = [row["lcscPart"] for row in api.iter_target_component_infos()]
        assert api.last_trace_id == "trace-2"

    assert parts == ["C1", "C3"]
    assert len(captured_requests) == 2
    assert all(
        path == "/overseas/openapi/component/getComponentInfos"
        for path, _, _, _ in captured_requests
    )
    assert all(
        content_type == "application/json"
        for _, _, _, content_type in captured_requests
    )

    first_to_sign = _build_string_to_sign(
        method="POST",
        path="/overseas/openapi/component/getComponentInfos",
        timestamp=1700000000,
        nonce=first_nonce,
        body="{}",
    )
    first_signature = _sign_hmac_sha256_base64(
        secret="secret-key", payload=first_to_sign
    )
    assert captured_requests[0][2] == (
        'JOP appid="app-id",accesskey="access-key",'
        f'timestamp="1700000000",nonce="{first_nonce}",signature="{first_signature}"'
    )

    second_to_sign = _build_string_to_sign(
        method="POST",
        path="/overseas/openapi/component/getComponentInfos",
        timestamp=1700000000,
        nonce=second_nonce,
        body='{"lastKey":"page-1"}',
    )
    second_signature = _sign_hmac_sha256_base64(
        secret="secret-key", payload=second_to_sign
    )
    assert captured_requests[1][2] == (
        'JOP appid="app-id",accesskey="access-key",'
        f'timestamp="1700000000",nonce="{second_nonce}",signature="{second_signature}"'
    )


def test_jlc_api_client_requires_jlc_openapi_credentials() -> None:
    config = FetchConfig(
        cache_dir=Path("/tmp/atopile-components-test"),
        jlc_api_base_url="https://open.jlcpcb.com",
        jlc_app_id=None,
        jlc_access_key=None,
        jlc_secret_key=None,
        jlc_component_infos_path="/overseas/openapi/component/getComponentInfos",
        jlc_component_detail_path="/overseas/openapi/component/getComponentDetail",
        request_timeout_s=10.0,
        target_categories=("Resistors", "Capacitors"),
    )

    api = JlcApiClient(config)
    try:
        try:
            api.get_component_page()
            assert False, "expected JlcApiError"
        except JlcApiError as ex:
            assert "Missing required env vars" in str(ex)
            assert "JLC_APP_ID" in str(ex)
            assert "JLC_ACCESS_KEY" in str(ex)
            assert "JLC_SECRET_KEY" in str(ex)
    finally:
        api.close()


def test_jlc_api_client_surfaces_business_errors_with_trace_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            headers={"J-Trace-ID": "trace-denied"},
            json={
                "code": 403,
                "success": False,
                "message": "API insufficient permissions, access denied",
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(base_url="https://open.jlcpcb.com", transport=transport)
    config = FetchConfig(
        cache_dir=Path("/tmp/atopile-components-test"),
        jlc_api_base_url="https://open.jlcpcb.com",
        jlc_app_id="app-id",
        jlc_access_key="access-key",
        jlc_secret_key="secret-key",
        jlc_component_infos_path="/overseas/openapi/component/getComponentInfos",
        jlc_component_detail_path="/overseas/openapi/component/getComponentDetail",
        request_timeout_s=10.0,
        target_categories=("Resistors", "Capacitors"),
    )

    with JlcApiClient(config, client=client) as api:
        try:
            api.get_component_page()
            assert False, "expected JlcApiError"
        except JlcApiError as ex:
            assert "code=403" in str(ex)
            assert "trace-denied" in str(ex)


def test_jlc_api_client_get_component_detail() -> None:
    captured_requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8")
        captured_requests.append((request.url.path, body))
        if request.url.path.endswith("/getComponentDetail"):
            return httpx.Response(
                200,
                headers={"J-Trace-ID": "trace-detail"},
                json={
                    "code": 200,
                    "success": True,
                    "data": {"componentCode": "C2040", "description": "part"},
                },
            )
        return httpx.Response(404, json={"code": 404, "success": False})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(base_url="https://open.jlcpcb.com", transport=transport)
    config = FetchConfig(
        cache_dir=Path("/tmp/atopile-components-test"),
        jlc_api_base_url="https://open.jlcpcb.com",
        jlc_app_id="app-id",
        jlc_access_key="access-key",
        jlc_secret_key="secret-key",
        jlc_component_infos_path="/overseas/openapi/component/getComponentInfos",
        jlc_component_detail_path="/overseas/openapi/component/getComponentDetail",
        request_timeout_s=10.0,
        target_categories=("Resistors", "Capacitors"),
    )

    with JlcApiClient(config, client=client) as api:
        detail = api.get_component_detail(2040)
        assert detail["componentCode"] == "C2040"
        assert api.last_trace_id == "trace-detail"

    assert captured_requests
    path, body = captured_requests[0]
    assert path.endswith("/getComponentDetail")
    assert body == '{"componentCode":"C2040"}'
