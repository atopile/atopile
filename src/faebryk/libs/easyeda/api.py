# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.libs.http import http_client
from faebryk.libs.util import once

logger = logging.getLogger(__name__)

# LEGACY: version= pins the EasyEDA API response format so upstream changes don't
# silently break our parser.  Hardcoded to match original easyeda2kicad behaviour.
_EASYEDA_API_VERSION = "6.4.19.5"
API_ENDPOINT = (
    "https://easyeda.com/api/products/{lcsc_id}/components?version="
    + _EASYEDA_API_VERSION
)
ENDPOINT_3D_MODEL_STEP = "https://modules.easyeda.com/qAxj6KHrDKw4blvCG8QJPs7Y/{uuid}"


class EasyEDAApiError(Exception): ...


class EasyEDAPartNotFound(EasyEDAApiError):
    def __init__(self, lcsc_id: str):
        self.lcsc_id = lcsc_id
        super().__init__(f"No EasyEDA data found for part {lcsc_id}")


class EasyEDAModelNotFound(EasyEDAApiError):
    def __init__(self, uuid: str):
        self.uuid = uuid
        super().__init__(f"No STEP 3D model found for uuid:{uuid}")


_HEADERS = {
    "Accept-Encoding": "gzip, deflate",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "easyeda2kicad v0.8.0",
}


@once
def _get_verify() -> bool:
    from atopile.config import config

    return not config.project.dangerously_skip_ssl_verification


def get_cad_data(lcsc_id: str) -> dict:
    """Fetch component CAD data from EasyEDA API.

    Raises EasyEDAPartNotFound if the API returns no data for the given part.
    """
    with http_client(headers=_HEADERS, verify=_get_verify()) as client:
        r = client.get(url=API_ENDPOINT.format(lcsc_id=lcsc_id))

    api_response = r.json()

    if not api_response or (
        "code" in api_response and api_response.get("success") is False
    ):
        raise EasyEDAPartNotFound(lcsc_id)

    result = api_response.get("result")
    if not result:
        raise EasyEDAPartNotFound(lcsc_id)

    return result


def get_step_model(uuid: str) -> bytes:
    """Fetch STEP 3D model binary data.

    Raises EasyEDAModelNotFound if the model is not available (HTTP 404).
    Re-raises other HTTP errors.
    """
    from httpx import HTTPStatusError

    headers = {"User-Agent": _HEADERS["User-Agent"]}
    with http_client(headers=headers, verify=_get_verify()) as client:
        r = client.get(url=ENDPOINT_3D_MODEL_STEP.format(uuid=uuid))

    try:
        r.raise_for_status()
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            raise EasyEDAModelNotFound(uuid) from e
        raise

    return r.content
