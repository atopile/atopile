"""Layout editor routes for the backend integration server.

Thin wrapper: creates a router from the shared factory wired to the
global ``layout_service`` singleton.
"""

from __future__ import annotations

from atopile.layout_server.server import create_layout_router
from atopile.server.domains.layout import layout_service

router = create_layout_router(layout_service)
