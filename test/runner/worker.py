import os
import sys
import time

import httpx
import pytest

# Ensure the current directory is in sys.path
sys.path.insert(0, os.getcwd())

from test.runner.common import (
    ORCHESTRATOR_URL_ENV,
    ClaimRequest,
    ClaimResponse,
    EventRequest,
    EventType,
)

ORCHESTRATOR_URL = os.environ.get(ORCHESTRATOR_URL_ENV)


def main():
    if not ORCHESTRATOR_URL:
        print(f"{ORCHESTRATOR_URL_ENV} not set", file=sys.stderr)
        sys.exit(1)

    client = httpx.Client(timeout=10.0)
    pid = os.getpid()
    print(f"Worker {pid} started against {ORCHESTRATOR_URL}")

    # Keep session separate? Pytest reuses sys.modules.

    try:
        while True:
            try:
                request = ClaimRequest(pid=pid)
                resp = client.post(
                    f"{ORCHESTRATOR_URL}/claim", content=request.model_dump_json()
                )
                if resp.status_code != 200:
                    print(
                        f"Worker {pid} failed to claim test: {resp.status_code}",
                        file=sys.stderr,
                    )
                    time.sleep(1)
                    continue

                response = ClaimResponse.model_validate_json(resp.content)
                nodeid = response.nodeid

                if not nodeid:
                    print(f"Worker {pid} received no work, exiting.")
                    break

                # Run pytest for this nodeid
                # We inject our http adapter plugin
                pytest.main(
                    [
                        nodeid,
                        "-p",
                        "test.runner.plugin",
                        "-q",
                        "--no-header",
                        "--no-summary",
                        "--disable-warnings",
                    ]
                )

            except httpx.RequestError as e:
                print(f"Worker {pid} connection error: {e}", file=sys.stderr)
                time.sleep(1)
                # If the orchestrator is down, we might want to exit eventually
                continue
            except Exception as e:
                print(f"Worker {pid} unexpected error: {e}", file=sys.stderr)
                time.sleep(1)

    finally:
        print(f"Worker {pid} shutting down")
        try:
            client.post(
                f"{ORCHESTRATOR_URL}/event",
                content=EventRequest(
                    type=EventType.EXIT, pid=pid, timestamp=time.time()
                ).model_dump_json(),
            )
        except Exception as e:
            print(f"Failed to send exit event: {e}", file=sys.stderr)
        client.close()


if __name__ == "__main__":
    main()
