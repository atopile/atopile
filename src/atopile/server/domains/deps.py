"""Shared dependencies for domain routers."""

from __future__ import annotations

from fastapi import Request

from atopile.server.app_context import AppContext


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx
