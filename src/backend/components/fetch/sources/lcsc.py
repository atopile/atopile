from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from ..config import FetchConfig
from ..models import FetchArtifactRecord
from ..storage.manifest_store import LocalManifestStore
from ..storage.object_store import LocalObjectStore
from .datasheets import fetch_store_datasheet_with_roundtrip
from .easyeda import fetch_store_easyeda_assets_with_roundtrip


@dataclass(frozen=True)
class LcscFetchSeed:
    lcsc_id: int
    datasheet_url: str | None = None


def fetch_lcsc_artifacts_with_roundtrip(
    *,
    seed: LcscFetchSeed,
    config: FetchConfig,
    object_store: LocalObjectStore,
    manifest_store: LocalManifestStore,
    client: httpx.Client | None = None,
    easyeda_footprint_converter: Callable[[dict[str, Any]], bytes] | None = None,
) -> list[FetchArtifactRecord]:
    records: list[FetchArtifactRecord] = []
    records.extend(
        fetch_store_easyeda_assets_with_roundtrip(
            lcsc_id=seed.lcsc_id,
            config=config,
            object_store=object_store,
            manifest_store=manifest_store,
            client=client,
            footprint_converter=easyeda_footprint_converter,
        )
    )
    if seed.datasheet_url:
        records.append(
            fetch_store_datasheet_with_roundtrip(
                lcsc_id=seed.lcsc_id,
                datasheet_url=seed.datasheet_url,
                config=config,
                object_store=object_store,
                manifest_store=manifest_store,
                client=client,
            )
        )
    return records
