from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


Sha256Hex = str


class PveLibrarySourceWorkbook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    sha256: Sha256Hex = Field(pattern=r"^[0-9a-f]{64}$")
    byte_length: int = Field(ge=0)
    staging_catalog_sha256: Sha256Hex = Field(pattern=r"^[0-9a-f]{64}$")


class PveLibraryMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"]
    schema_version: Literal["private-pve-local-catalog/v1"]
    dataset_sha256: Sha256Hex = Field(pattern=r"^[0-9a-f]{64}$")
    source_status: Literal["SOURCE_PROVIDED"]
    independent_clear_verification: Literal["NOT_PERFORMED"]
    source_workbooks: list[PveLibrarySourceWorkbook]


DataT = TypeVar("DataT")


class PveLibraryEnvelope(BaseModel, Generic[DataT]):
    model_config = ConfigDict(extra="forbid")

    data: DataT
    meta: PveLibraryMeta


class PveStageRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    area: int = Field(ge=1)
    stage: int = Field(ge=1)


class PveProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_workbook_sha256: Sha256Hex = Field(pattern=r"^[0-9a-f]{64}$")
    source_workbook_filename: str
    staging_catalog_sha256: Sha256Hex = Field(pattern=r"^[0-9a-f]{64}$")
    sheet_name: str
    source_range: str


class PveStageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str
    mode: str
    element: str
    label_raw: str | None
    stage_refs: list[PveStageRef]
    team_count: int = Field(ge=0)
    provenance: PveProvenance


class PveStageFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str | None
    element: str | None
    area: int | None
    stage: int | None


class PveAvailableFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modes: list[str]
    elements: list[str]
    areas: list[int]
    stages: list[int]


class PveStageListData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PveStageSummary]
    filters: PveStageFilters
    available_filters: PveAvailableFilters
    total: int = Field(ge=0)


class PveLinkMedia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["YOUTUBE", "EXTERNAL"]
    external_url: str
    embed_url: str | None = None
    video_id: str | None = None


class PveSourceLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    label_raw: str | None
    origin_cell: str
    resolution_status: str
    alias_id: str | None
    alias_label: str | None
    applies_to_cell: str | None
    url: str | None
    media: PveLinkMedia | None


class PveOperationVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    raw: str
    origin_field: str
    origin_cell: str
    source_order_states: list[Literal["SET", "NOT_SET"]]


class PveOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    order_basis: str
    member_alignment: str
    execution_hints: list[str]
    variants: list[PveOperationVariant]


class PveAxis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    axis_id: str
    operation_raw: str | None
    notes_raw: str | None
    source_cell: str
    operation: PveOperation
    source_links: list[PveSourceLink]


class PvePortrait(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_position: int = Field(ge=1, le=5)
    asset_sha256: Sha256Hex = Field(pattern=r"^[0-9a-f]{64}$")
    asset_url: str
    icon_url: str | None
    mapping_status: str
    unit_key: str | None
    tw_name: str | None
    display_rarity: Literal["THREE_STAR", "SIX_STAR"] | None
    display_source: str
    anchor_cell: str


class PveTeam(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: str
    display_order: int = Field(ge=1)
    notes_raw: str | None
    flags: list[str]
    source_range: str
    portraits: list[PvePortrait] = Field(min_length=5, max_length=5)
    axes: list[PveAxis]
    source_links: list[PveSourceLink]
    provenance: PveProvenance


class PveStageDetail(PveStageSummary):
    teams: list[PveTeam]


class PveLibraryErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, str | int | None] | None = None


class PveLibraryErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: PveLibraryErrorBody
