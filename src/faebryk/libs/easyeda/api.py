# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.libs.http import http_client
from faebryk.libs.util import once

logger = logging.getLogger(__name__)

# version= pins the EasyEDA API response format so upstream changes don't silently
# break our parser.  The parameter is optional today, but hardcoding it matches
# the original easyeda2kicad behaviour and guards against future format changes.
_EASYEDA_API_VERSION = "6.4.19.5"
API_ENDPOINT = (
    "https://easyeda.com/api/products/{lcsc_id}/components?version="
    + _EASYEDA_API_VERSION
)
ENDPOINT_3D_MODEL_STEP = "https://modules.easyeda.com/qAxj6KHrDKw4blvCG8QJPs7Y/{uuid}"


class EasyEDAApiError(Exception): ...


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


def get_cad_data(lcsc_id: str) -> dict | None:
    """Fetch component CAD data from EasyEDA API. Returns the result dict or None."""
    with http_client(headers=_HEADERS, verify=_get_verify()) as client:
        r = client.get(url=API_ENDPOINT.format(lcsc_id=lcsc_id))

    api_response = r.json()

    if not api_response or (
        "code" in api_response and api_response.get("success") is False
    ):
        logger.debug(f"EasyEDA API returned no data for {lcsc_id}: {api_response}")
        return None

    return api_response.get("result")


def get_step_model(uuid: str) -> bytes | None:
    """Fetch STEP 3D model binary data. Returns bytes or None."""
    headers = {"User-Agent": _HEADERS["User-Agent"]}
    with http_client(headers=headers, verify=_get_verify()) as client:
        r = client.get(url=ENDPOINT_3D_MODEL_STEP.format(uuid=uuid))

    try:
        r.raise_for_status()
    except Exception:
        logger.error(f"No STEP 3D model data found for uuid:{uuid}")
        return None

    return r.content
