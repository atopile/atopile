from __future__ import annotations

import re

_PACKAGE_NUMERIC_RE = re.compile(r"^\d{4,5}$")
_PACKAGE_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")
_COMPONENT_PACKAGE_PREFIX = {
    "resistor": "R",
    "capacitor": "C",
    "capacitor_polarized": "C",
    "inductor": "L",
    "ferrite_bead": "L",
}


def normalize_package(component_type: str, raw_package: str) -> str | None:
    normalized = raw_package.strip().upper()
    if not normalized:
        return None
    if component_type == "crystal":
        canonical = _PACKAGE_NON_ALNUM_RE.sub("", normalized)
        return canonical or normalized

    if component_type == "ferrite_bead":
        for prefix in ("L", "FB"):
            if normalized.startswith(prefix):
                suffix = normalized[len(prefix) :]
                if _PACKAGE_NUMERIC_RE.fullmatch(suffix):
                    return suffix
        return normalized

    prefix = _COMPONENT_PACKAGE_PREFIX.get(component_type)
    if prefix is None:
        return normalized

    if normalized.startswith(prefix):
        suffix = normalized[len(prefix) :]
        if _PACKAGE_NUMERIC_RE.fullmatch(suffix):
            return suffix
    return normalized
