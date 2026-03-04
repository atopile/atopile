from __future__ import annotations

from pathlib import Path


def _emit_interface(name: str, fields: dict[str, str]) -> str:
    body = "\n".join([f"  {key}: {value};" for key, value in fields.items()])
    return f"export interface {name} {{\n{body}\n}}\n"


def generate_types(out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)

    health_fields = {
        "ok": "boolean",
        "sessions": "number",
        "pool": "number",
        "max_machine_count": "number | null",
        "uptime": "number",
    }
    error_fields = {"error": "string"}
    dashboard_point_fields = {
        "timestamp_ms": "number",
        "active": "number",
        "warm": "number",
        "total": "number",
    }
    dashboard_series_fields = {
        "points": "DashboardPoint[]",
        "active": "number",
        "warm": "number",
        "total": "number",
        "max_machine_count": "number | null",
    }

    content = "// Generated from Pydantic models. Do not edit by hand.\n\n"
    content += _emit_interface("HealthResponse", health_fields)
    content += "\n"
    content += _emit_interface("ErrorResponse", error_fields)
    content += "\n"
    content += _emit_interface("DashboardPoint", dashboard_point_fields)
    content += "\n"
    content += _emit_interface("DashboardSeriesResponse", dashboard_series_fields)

    out_file.write_text(content, encoding="utf-8")
