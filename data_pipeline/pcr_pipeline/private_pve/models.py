from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


SCHEMA_VERSION = "private-pve-xlsx-staging/v1"
PARSER_NAME = "pcr-private-pve-xlsx"
PARSER_VERSION = "1.0.0"


class WorkbookLayoutError(ValueError):
    """Raised when a workbook no longer matches an audited source layout."""


@dataclass(frozen=True)
class SourceRef:
    kind: str
    label_raw: str
    origin_cell: str
    url: str | None = None
    alias_id: str | None = None
    alias_label: str | None = None
    resolution_status: str = "RESOLVED"
    applies_to_cell: str | None = None


@dataclass(frozen=True)
class OperationVariant:
    kind: str
    raw: str
    source_order_states: tuple[str, ...]
    origin_field: str
    origin_cell: str | None


@dataclass(frozen=True)
class ParsedOperation:
    kind: str
    order_basis: str
    member_alignment: str
    variants: tuple[OperationVariant, ...]
    execution_hints: tuple[str, ...]


@dataclass(frozen=True)
class AssetOccurrence:
    sheet_name: str
    anchor_cell: str
    row: int
    column: int
    width_px: int
    height_px: int


@dataclass(frozen=True)
class AssetExtract:
    sha256: str
    byte_length: int
    mime_type: str
    file_extension: str
    width_px: int
    height_px: int
    occurrences: tuple[AssetOccurrence, ...]


@dataclass(frozen=True)
class MemberExtract:
    display_position: int
    anchor_cell: str
    image_sha256: str
    unit_key: None = None
    mapping_status: str = "UNMAPPED"


@dataclass(frozen=True)
class AxisExtract:
    axis_source_id: str
    source_cell: str
    operation_raw: str
    operation: ParsedOperation
    notes_raw: str | None
    source_refs: tuple[SourceRef, ...]


@dataclass(frozen=True)
class TeamExtract:
    team_source_id: str
    display_order: int
    source_range: str
    formation: tuple[MemberExtract, ...]
    axes: tuple[AxisExtract, ...]
    notes_raw: str | None
    source_refs: tuple[SourceRef, ...]
    flags: tuple[str, ...]


@dataclass(frozen=True)
class StageRef:
    kind: str
    area: int
    stage: int


@dataclass(frozen=True)
class EraMarker:
    kind: str
    label_raw: str | None = None


@dataclass(frozen=True)
class SectionExtract:
    section_id: str
    mode: str
    element: str
    stage_refs: tuple[StageRef, ...]
    label_raw: str
    source_range: str
    era: EraMarker
    teams: tuple[TeamExtract, ...]


@dataclass(frozen=True)
class SheetExtract:
    sheet_name: str
    sheet_state: str
    layout_id: str
    collection: str
    element: str | None
    source_refs: tuple[SourceRef, ...]
    sections: tuple[SectionExtract, ...]


@dataclass(frozen=True)
class WorkbookExtract:
    schema_version: str
    parser: dict[str, Any]
    source_workbook: dict[str, Any]
    sheets: tuple[SheetExtract, ...]
    assets: tuple[AssetExtract, ...]
    summary: dict[str, Any]
    diagnostics: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_json_bytes(self) -> bytes:
        return (
            json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
