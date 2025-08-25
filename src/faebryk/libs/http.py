import contextlib
from collections.abc import Generator

import httpx
from httpx import (  # noqa: F401
    HTTPError,
    HTTPStatusError,
    RequestError,
    Response,
    TimeoutException,
)


@contextlib.contextmanager
def http_client(
    headers: dict[str, str] | None = None, verify: bool = True
) -> Generator[httpx.Client, None, None]:
    client = httpx.Client(headers=headers, verify=verify)

    yield client

    client.close()
