from __future__ import annotations

from typing import Any, TypeAlias

from pydantic import BaseModel, Field, field_validator, model_validator

from .interfaces import (
    AssetRecord,
    ComponentCandidate,
    ComponentType,
    NumericRange,
    ParameterQuery,
)

ExactValue: TypeAlias = str | int | float | bool | None


class NumericRangeModel(BaseModel):
    minimum: float | None = None
    maximum: float | None = None

    @model_validator(mode="after")
    def _validate_bounds(self) -> "NumericRangeModel":
        NumericRange(minimum=self.minimum, maximum=self.maximum)
        return self

    def to_domain(self) -> NumericRange:
        return NumericRange(minimum=self.minimum, maximum=self.maximum)


class ParametersQueryRequest(BaseModel):
    component_type: ComponentType
    qty: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=500)
    package: str | None = None
    exact: dict[str, ExactValue] = Field(default_factory=dict)
    ranges: dict[str, NumericRangeModel] = Field(default_factory=dict)

    def to_domain_query(self) -> ParameterQuery:
        return ParameterQuery(
            qty=self.qty,
            limit=self.limit,
            package=self.package,
            exact=dict(self.exact),
            ranges={key: value.to_domain() for key, value in self.ranges.items()},
        )


class ComponentCandidateModel(BaseModel):
    lcsc_id: int
    stock: int | None = None
    is_basic: bool | None = None
    is_preferred: bool | None = None
    pick_parameters: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, item: ComponentCandidate) -> "ComponentCandidateModel":
        return cls(
            lcsc_id=item.lcsc_id,
            stock=item.stock,
            is_basic=item.is_basic,
            is_preferred=item.is_preferred,
            pick_parameters=dict(item.pick_parameters),
        )


class ParametersQueryResponse(BaseModel):
    component_type: ComponentType
    candidates: list[ComponentCandidateModel]
    total: int


class ComponentsFullRequest(BaseModel):
    component_ids: list[int] = Field(..., min_length=1, max_length=1000)

    @field_validator("component_ids")
    @classmethod
    def _validate_positive_ids(cls, value: list[int]) -> list[int]:
        if any(component_id <= 0 for component_id in value):
            raise ValueError("component_ids must be positive integers")
        return value

    def deduplicated_ids(self) -> list[int]:
        seen: set[int] = set()
        ordered: list[int] = []
        for component_id in self.component_ids:
            if component_id in seen:
                continue
            seen.add(component_id)
            ordered.append(component_id)
        return ordered


class AssetRecordModel(BaseModel):
    lcsc_id: int
    artifact_type: str
    stored_key: str | None = None
    encoding: str = "zstd"
    mime: str | None = None
    raw_sha256: str | None = None
    raw_size_bytes: int | None = None
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, item: AssetRecord) -> "AssetRecordModel":
        return cls(
            lcsc_id=item.lcsc_id,
            artifact_type=item.artifact_type,
            stored_key=item.stored_key,
            encoding=item.encoding,
            mime=item.mime,
            raw_sha256=item.raw_sha256,
            raw_size_bytes=item.raw_size_bytes,
            source_url=item.source_url,
            metadata=dict(item.metadata),
        )


class FullResponseMetadata(BaseModel):
    components: list[dict[str, Any]]
    asset_manifest: dict[str, list[AssetRecordModel]]
    bundle_filename: str
    bundle_media_type: str
    bundle_sha256: str
    bundle_size_bytes: int


def test_full_request_deduplicates_while_preserving_order() -> None:
    model = ComponentsFullRequest(component_ids=[3, 2, 3, 1, 2])
    assert model.deduplicated_ids() == [3, 2, 1]
