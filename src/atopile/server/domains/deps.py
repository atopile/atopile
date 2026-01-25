"""Shared dependencies for domain routers."""

from __future__ import annotations

from fastapi import Request

from atopile.dataclasses import AppContext


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx
