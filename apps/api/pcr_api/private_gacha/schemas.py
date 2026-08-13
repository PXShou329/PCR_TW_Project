from __future__ import annotations

from datetime import date
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


Sha256Hex = str


class GachaLibrarySourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_addressed_filename: str
    sha256: Sha256Hex = Field(pattern=r"^[0-9a-f]{64}$")
    byte_length: int = Field(ge=1)


class GachaLibraryMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"]
    schema_version: Literal["gacha-community-docx-candidates/v1"]
    dataset_sha256: Sha256Hex = Field(pattern=r"^[0-9a-f]{64}$")
    source_status: Literal["USER_SUPPLIED"]
    authority: Literal["COMMUNITY_FORECAST"]
    source_id: Literal["GACHA-COMM-002"]
    independence_group: Literal["GACHA-COMM-002"]
    canonical_write_count: Literal[0]
    source_document: GachaLibrarySourceDocument


DataT = TypeVar("DataT")


class GachaLibraryEnvelope(BaseModel, Generic[DataT]):
    model_config = ConfigDict(extra="forbid")

    data: DataT
    meta: GachaLibraryMeta


class GachaForecastImage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sha256: Sha256Hex = Field(pattern=r"^[0-9a-f]{64}$")
    mime_type: Literal["image/jpeg", "image/png", "image/webp"]
    byte_length: int = Field(ge=1)
    asset_url: str


class GachaForecastProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description_locators: list[str]
    source_locator: str
    image_locator: str
    relationship_id: str
    package_path: str


class GachaForecastCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(pattern=r"^GACHA-DOCX-[0-9a-f]{24}$")
    review_order: int = Field(ge=1)
    source_declared_pool_kind: Literal[
        "LIMITED_PICKUP", "PERMANENT_PICKUP", "RERUN"
    ]
    forecast_start: date
    forecast_end: date
    precision: Literal["DAY"]
    date_boundary_semantics: Literal["SOURCE_UNSPECIFIED"]
    raw_character_names: list[str] = Field(min_length=1)
    raw_description_lines: list[str] = Field(min_length=1)
    raw_forecast_text: str
    raw_sequence_label: str | None
    identity_status: Literal["UNVERIFIED_COMMUNITY_NAME"]
    review_status: Literal["PENDING"]
    review_reason: Literal[
        "EXACT_EVENT_LINK_NOT_REVIEWED",
        "UNDELIMITED_CHARACTER_TEXT_REQUIRES_REVIEW",
    ]
    promotion_eligible: Literal[False]
    proposed_event_id: None
    parser_warnings: list[Literal["UNQUOTED_CHARACTER_SEQUENCE"]]
    image: GachaForecastImage
    provenance: GachaForecastProvenance


class GachaForecastListData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[GachaForecastCandidate]
    total: int = Field(ge=0)


class GachaLibraryErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, str | int | None] | None = None


class GachaLibraryErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: GachaLibraryErrorBody
