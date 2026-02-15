from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import httpx

from ..config import FetchConfig


class JlcApiError(RuntimeError):
    pass


class JlcApiClient:
    def __init__(self, config: FetchConfig, *, client: httpx.Client | None = None):
        self.config = config
        self._client = client or httpx.Client(
            base_url=config.jlc_api_base_url.rstrip("/"),
            timeout=config.request_timeout_s,
        )
        self._owns_client = client is None
        self._token: str | None = None
        self.last_trace_id: str | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> JlcApiClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def refresh_token(self) -> str:
        if not self.config.jlc_app_key or not self.config.jlc_app_secret:
            raise JlcApiError(
                "Missing JLC credentials. Set JLC_API_KEY and JLC_API_SECRET."
            )
        response = self._client.post(
            self.config.jlc_token_path,
            json={
                "appKey": self.config.jlc_app_key,
                "appSecret": self.config.jlc_app_secret,
            },
            headers={"Content-Type": "application/json"},
        )
        payload = self._parse_response_payload(response, context="JLC token request")
        token = payload.get("data")
        if not isinstance(token, str) or not token:
            raise JlcApiError(f"Unexpected token response: {payload}")
        self._token = token
        return token

    def get_component_page(
        self, *, last_key: str | None = None, _retry: bool = True
    ) -> dict:
        token = self._token or self.refresh_token()
        body: dict[str, str] = {}
        if last_key:
            body["lastKey"] = last_key

        response = self._client.post(
            self.config.jlc_component_infos_path,
            json=body,
            headers={
                "externalApiToken": token,
                "Content-Type": "application/json",
            },
        )
        if response.status_code in (401, 403) and _retry:
            self.refresh_token()
            return self.get_component_page(last_key=last_key, _retry=False)

        payload = self._parse_response_payload(
            response, context="JLC component page request"
        )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise JlcApiError(f"Failed to fetch component page: {payload}")
        return data

    def _parse_response_payload(
        self, response: httpx.Response, *, context: str
    ) -> dict:
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

        if response.status_code != 200:
            raise JlcApiError(
                f"{context} failed; http={response.status_code} "
                f"trace={trace_id or '-'} payload={payload}"
            )

        code = payload.get("code")
        if code is not None and code != 200:
            raise JlcApiError(
                f"{context} business error; code={code} "
                f"message={payload.get('message')} trace={trace_id or '-'}"
            )
        return payload

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
            first_category = component.get("firstCategory")
            if first_category in target:
                yield component


def test_jlc_api_client_filters_target_categories() -> None:
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8")
        requests.append((request.url.path, body))
        if request.url.path == "/external/genToken":
            return httpx.Response(
                200,
                headers={"J-Trace-ID": "trace-token"},
                json={"code": 200, "data": "token-1"},
            )
        if request.url.path == "/external/component/getComponentInfos":
            if '"lastKey":"page-1"' in body:
                return httpx.Response(
                    200,
                    json={
                        "code": 200,
                        "data": {
                            "lastKey": None,
                            "componentInfos": [
                                {"lcscPart": "C3", "firstCategory": "Capacitors"}
                            ],
                        },
                    },
                )
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {
                        "lastKey": "page-1",
                        "componentInfos": [
                            {"lcscPart": "C1", "firstCategory": "Resistors"},
                            {"lcscPart": "C2", "firstCategory": "ICs"},
                        ],
                    },
                },
            )
        return httpx.Response(404, json={"error": "unexpected path"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(base_url="https://jlcpcb.com", transport=transport)
    config = FetchConfig(
        cache_dir=Path("/tmp/atopile-components-test"),
        jlc_api_base_url="https://jlcpcb.com",
        jlc_app_key="key",
        jlc_app_secret="secret",
        jlc_token_path="/external/genToken",
        jlc_component_infos_path="/external/component/getComponentInfos",
        jlc_component_detail_path="/external/component/getComponentDetail",
        request_timeout_s=10.0,
        target_categories=("Resistors", "Capacitors"),
    )

    with JlcApiClient(config, client=client) as api:
        parts = [row["lcscPart"] for row in api.iter_target_component_infos()]

    assert parts == ["C1", "C3"]
    assert requests[0][0] == "/external/genToken"


def test_jlc_api_client_requires_credentials() -> None:
    config = FetchConfig(
        cache_dir=Path("/tmp/atopile-components-test"),
        jlc_api_base_url="https://jlcpcb.com",
        jlc_app_key=None,
        jlc_app_secret=None,
        jlc_token_path="/external/genToken",
        jlc_component_infos_path="/external/component/getComponentInfos",
        jlc_component_detail_path="/external/component/getComponentDetail",
        request_timeout_s=10.0,
        target_categories=("Resistors", "Capacitors"),
    )
    api = JlcApiClient(config)
    try:
        try:
            api.refresh_token()
            assert False, "expected JlcApiError"
        except JlcApiError:
            pass
    finally:
        api.close()
