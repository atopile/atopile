from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, Sequence, TypeAlias

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


class ComponentType(StrEnum):
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    CAPACITOR_POLARIZED = "capacitor_polarized"
    INDUCTOR = "inductor"
    DIODE = "diode"
    LED = "led"
    BJT = "bjt"
    MOSFET = "mosfet"


@dataclass(frozen=True)
class NumericRange:
    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        if self.minimum is None and self.maximum is None:
            raise ValueError("NumericRange must define minimum or maximum")
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("NumericRange minimum cannot exceed maximum")


@dataclass(frozen=True)
class ParameterQuery:
    qty: int = 1
    limit: int = 50
    package: str | None = None
    exact: dict[str, JsonValue] = field(default_factory=dict)
    ranges: dict[str, NumericRange] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.qty < 1:
            raise ValueError("qty must be >= 1")
        if self.limit < 1:
            raise ValueError("limit must be >= 1")


@dataclass(frozen=True)
class ComponentCandidate:
    lcsc_id: int
    stock: int | None
    is_basic: bool | None
    is_preferred: bool | None
    pick_parameters: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class AssetRecord:
    lcsc_id: int
    artifact_type: str
    stored_key: str | None = None
    encoding: str = "zstd"
    mime: str | None = None
    raw_sha256: str | None = None
    raw_size_bytes: int | None = None
    source_url: str | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class BundleArtifact:
    data: bytes
    filename: str
    media_type: str
    sha256: str
    manifest: dict[str, JsonValue] = field(default_factory=dict)


class ServeError(RuntimeError):
    """Base exception for stage-3 serving layer failures."""


class SnapshotSchemaError(ServeError):
    """Raised when a snapshot DB does not match the expected schema."""


class SnapshotNotFoundError(ServeError):
    """Raised when no current immutable snapshot can be resolved."""


class QueryValidationError(ServeError):
    """Raised when client-supplied query constraints are invalid."""


class AssetLoadError(ServeError):
    """Raised when an asset cannot be safely loaded into a response bundle."""


class FastLookupStore(Protocol):
    def query_resistors(self, query: ParameterQuery) -> list[ComponentCandidate]:
        raise NotImplementedError

    def query_capacitors(self, query: ParameterQuery) -> list[ComponentCandidate]:
        raise NotImplementedError

    def query_capacitors_polarized(
        self, query: ParameterQuery
    ) -> list[ComponentCandidate]:
        raise NotImplementedError

    def query_inductors(self, query: ParameterQuery) -> list[ComponentCandidate]:
        raise NotImplementedError

    def query_diodes(self, query: ParameterQuery) -> list[ComponentCandidate]:
        raise NotImplementedError

    def query_leds(self, query: ParameterQuery) -> list[ComponentCandidate]:
        raise NotImplementedError

    def query_bjts(self, query: ParameterQuery) -> list[ComponentCandidate]:
        raise NotImplementedError

    def query_mosfets(self, query: ParameterQuery) -> list[ComponentCandidate]:
        raise NotImplementedError


class DetailStore(Protocol):
    def get_components(self, lcsc_ids: Sequence[int]) -> dict[int, dict[str, Any]]:
        raise NotImplementedError

    def get_asset_manifest(
        self, lcsc_ids: Sequence[int]
    ) -> dict[int, list[AssetRecord]]:
        raise NotImplementedError


class BundleStore(Protocol):
    def build_bundle(self, lcsc_ids: Sequence[int]) -> BundleArtifact:
        raise NotImplementedError


def test_numeric_range_requires_a_bound() -> None:
    try:
        NumericRange()
    except ValueError as exc:
        assert "minimum or maximum" in str(exc)
    else:
        assert False, "Expected ValueError"


def test_parameter_query_validates_qty_and_limit() -> None:
    try:
        ParameterQuery(qty=0)
    except ValueError as exc:
        assert "qty" in str(exc)
    else:
        assert False, "Expected ValueError"
