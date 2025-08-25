import contextlib
import ssl
from collections.abc import Generator

import httpx
import truststore
from httpx import (  # noqa: F401
    HTTPError,
    HTTPStatusError,
    RequestError,
    Response,
    TimeoutException,
)


@contextlib.contextmanager
def http_client(
    headers: dict[str, str] | None = None, verify: bool | ssl.SSLContext = True
) -> Generator[httpx.Client, None, None]:
    if verify is True:
        verify = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    client = httpx.Client(headers=headers, verify=verify)

    yield client

    client.close()
