from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

from .config import Settings


CATALOG_SCHEMA_VERSION = "private-pve-local-catalog/v1"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
ESTERTION_ICON_BASE_ID_PATTERN = re.compile(r"^[0-9]{4}$")
ESTERTION_ICON_ID_PATTERN = re.compile(r"^[0-9]{6}$")
ESTERTION_ICON_PATH_PATTERN = re.compile(r"^/icon/unit/([0-9]{6})\.webp$")
ESTERTION_ICON_ORIGIN = "https://redive.estertion.win"
ESTERTION_ICON_HOST = "redive.estertion.win"
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}
YOUTU_BE_HOSTS = {"youtu.be", "www.youtu.be"}
ZERO_AXIS_TEAM_IDS = {"deep:water:09-02:r:016"}
ROOT_FIELDS = {"assets", "builder", "schema_version", "sources", "summary"}


class PveLibraryUnavailable(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, str | int | None] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class PveLibraryNotFound(LookupError):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(identifier)
        self.resource = resource
        self.identifier = identifier


@dataclass(frozen=True)
class AssetRecord:
    sha256: str
    filename: str
    mime_type: str
    byte_length: int
    path: Path


@dataclass(frozen=True)
class StageRecord:
    section: Mapping[str, Any]
    source_workbook: Mapping[str, Any]
    staging_catalog: Mapping[str, Any]
    sheet_name: str


@dataclass(frozen=True)
class PveLibrarySnapshot:
    dataset_sha256: str
    schema_version: str
    source_workbooks: tuple[Mapping[str, Any], ...]
    stages: tuple[StageRecord, ...]
    stages_by_id: Mapping[str, StageRecord]
    assets_by_sha256: Mapping[str, AssetRecord]
    fingerprint: tuple[Any, ...]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _StrictJsonError(ValueError):
    pass


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _StrictJsonError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise _StrictJsonError(f"non-finite JSON number: {value}")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _column_letters(column: int) -> str:
    result = ""
    value = column
    while value:
        value, remainder = divmod(value - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def _catalog_error(reason: str) -> PveLibraryUnavailable:
    return PveLibraryUnavailable(
        "PVE_LIBRARY_INVALID",
        "The configured PVE library failed validation.",
        details={"reason": reason},
    )


def _expect_dict(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _catalog_error(f"{path} must be an object")
    return value


def _expect_exact_fields(
    value: Mapping[str, Any],
    fields: set[str],
    path: str,
) -> None:
    if set(value) != fields:
        raise _catalog_error(f"{path} fields do not match the v1 schema")


def _expect_list(value: object, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise _catalog_error(f"{path} must be an array")
    return value


def _expect_string(value: object, path: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str):
        raise _catalog_error(f"{path} must be a string")
    return value


def _expect_int(value: object, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise _catalog_error(f"{path} must be an integer >= {minimum}")
    return value


def _validate_source_ref(value: object, path: str) -> None:
    ref = _expect_dict(value, path)
    _expect_string(ref.get("kind"), f"{path}.kind")
    _expect_string(ref.get("label_raw"), f"{path}.label_raw", nullable=True)
    _expect_string(ref.get("origin_cell"), f"{path}.origin_cell")
    _expect_string(ref.get("resolution_status"), f"{path}.resolution_status")
    for field in ("alias_id", "alias_label", "applies_to_cell", "url"):
        _expect_string(ref.get(field), f"{path}.{field}", nullable=True)


def _validate_operation(value: object, path: str) -> None:
    operation = _expect_dict(value, path)
    _expect_exact_fields(
        operation,
        {
            "execution_hints",
            "kind",
            "member_alignment",
            "order_basis",
            "variants",
        },
        path,
    )
    for field in ("kind", "order_basis", "member_alignment"):
        _expect_string(operation.get(field), f"{path}.{field}")
    if operation["order_basis"] != "WORKBOOK_TEXT_LEFT_TO_RIGHT":
        raise _catalog_error(f"{path}.order_basis must preserve workbook text order")
    if operation["member_alignment"] != "UNRESOLVED":
        raise _catalog_error(f"{path}.member_alignment must remain unresolved")
    hints = _expect_list(operation.get("execution_hints"), f"{path}.execution_hints")
    if not all(isinstance(hint, str) for hint in hints):
        raise _catalog_error(f"{path}.execution_hints must contain only strings")
    variants = _expect_list(operation.get("variants"), f"{path}.variants")
    for variant_index, raw_variant in enumerate(variants):
        variant_path = f"{path}.variants[{variant_index}]"
        variant = _expect_dict(raw_variant, variant_path)
        _expect_exact_fields(
            variant,
            {
                "kind",
                "origin_cell",
                "origin_field",
                "raw",
                "source_order_states",
            },
            variant_path,
        )
        for field in ("kind", "raw", "origin_field", "origin_cell"):
            _expect_string(variant.get(field), f"{variant_path}.{field}")
        states = _expect_list(
            variant.get("source_order_states"),
            f"{variant_path}.source_order_states",
        )
        if any(state not in {"SET", "NOT_SET"} for state in states):
            raise _catalog_error(
                f"{variant_path}.source_order_states contains an invalid state"
            )
        if len(states) != 5:
            raise _catalog_error(
                f"{variant_path}.source_order_states must contain exactly five states"
            )


def _safe_web_url(value: str) -> bool:
    if value != value.strip() or "\\" in value or any(ord(char) < 32 for char in value):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and (
            port is None
            or (parsed.scheme == "http" and port == 80)
            or (parsed.scheme == "https" and port == 443)
        )
    )


def _youtube_video_id(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
    ):
        return None
    host = (parsed.hostname or "").lower()
    candidate: str | None = None
    parts = [part for part in parsed.path.split("/") if part]
    if host in YOUTU_BE_HOSTS and len(parts) == 1:
        candidate = parts[0]
    elif host in YOUTUBE_HOSTS:
        if parsed.path == "/watch":
            values = parse_qs(parsed.query, keep_blank_values=True).get("v", [])
            if len(values) == 1:
                candidate = values[0]
        elif len(parts) == 2 and parts[0] in {"embed", "shorts"}:
            candidate = parts[1]
    if candidate is None or YOUTUBE_ID_PATTERN.fullmatch(candidate) is None:
        return None
    return candidate


def media_for_url(value: str | None) -> dict[str, str | None] | None:
    if value is None or not _safe_web_url(value):
        return None
    video_id = _youtube_video_id(value)
    if video_id is not None:
        return {
            "kind": "YOUTUBE",
            "external_url": value,
            "embed_url": f"https://www.youtube-nocookie.com/embed/{video_id}",
            "video_id": video_id,
        }
    return {
        "kind": "EXTERNAL",
        "external_url": value,
        "embed_url": None,
        "video_id": None,
    }


def source_link_view(raw_ref: Mapping[str, Any]) -> dict[str, Any]:
    raw_url = raw_ref["url"]
    url = raw_url if raw_url is not None and _safe_web_url(raw_url) else None
    return {
        "kind": raw_ref["kind"],
        "label_raw": raw_ref["label_raw"],
        "origin_cell": raw_ref["origin_cell"],
        "resolution_status": raw_ref["resolution_status"],
        "alias_id": raw_ref["alias_id"],
        "alias_label": raw_ref["alias_label"],
        "applies_to_cell": raw_ref["applies_to_cell"],
        "url": url,
        "media": media_for_url(url),
    }


class PveLibraryRuntime:
    """Lazy, immutable, file-backed PVE catalog snapshot.

    The first read validates the whole catalog and every asset. Once loaded, any
    catalog or asset-directory metadata change makes the runtime unavailable
    until the process is restarted; requests never combine two file revisions.
    """

    def __init__(self, catalog_path: Path | None, asset_dir: Path | None) -> None:
        self._catalog_path = catalog_path
        self._asset_dir = asset_dir
        self._snapshot: PveLibrarySnapshot | None = None
        self._drifted = False
        self._lock = threading.RLock()

    @classmethod
    def from_settings(cls, settings: Settings) -> PveLibraryRuntime:
        return cls(
            settings.pve_library_catalog_path,
            settings.pve_library_asset_dir,
        )

    def snapshot(self) -> PveLibrarySnapshot:
        with self._lock:
            if self._catalog_path is None or self._asset_dir is None:
                raise PveLibraryUnavailable(
                    "PVE_LIBRARY_NOT_CONFIGURED",
                    "The local PVE library is not configured.",
                )
            if self._drifted:
                raise PveLibraryUnavailable(
                    "PVE_LIBRARY_DRIFT",
                    "The local PVE library changed after its immutable snapshot was loaded.",
                )
            if self._snapshot is None:
                self._snapshot = self._load()
            else:
                try:
                    current = self._fingerprint()
                except OSError as error:
                    self._drifted = True
                    raise PveLibraryUnavailable(
                        "PVE_LIBRARY_DRIFT",
                        "The local PVE library changed after its immutable snapshot was loaded.",
                        details={"reason": type(error).__name__},
                    ) from error
                if current != self._snapshot.fingerprint:
                    self._drifted = True
                    raise PveLibraryUnavailable(
                        "PVE_LIBRARY_DRIFT",
                        "The local PVE library changed after its immutable snapshot was loaded.",
                    )
            return self._snapshot

    def read_asset(self, sha256: str) -> tuple[bytes, AssetRecord]:
        snapshot = self.snapshot()
        asset = snapshot.assets_by_sha256.get(sha256)
        if asset is None:
            raise PveLibraryNotFound("pve_asset", sha256)
        try:
            data = asset.path.read_bytes()
        except OSError as error:
            self._drifted = True
            raise PveLibraryUnavailable(
                "PVE_LIBRARY_DRIFT",
                "A PVE portrait asset is no longer readable.",
                details={"asset_sha256": sha256},
            ) from error
        if len(data) != asset.byte_length or _sha256(data) != asset.sha256:
            self._drifted = True
            raise PveLibraryUnavailable(
                "PVE_LIBRARY_DRIFT",
                "A PVE portrait asset no longer matches the catalog.",
                details={"asset_sha256": sha256},
            )
        return data, asset

    def _fingerprint(self) -> tuple[Any, ...]:
        assert self._catalog_path is not None
        assert self._asset_dir is not None
        catalog_stat = self._catalog_path.stat()
        entries: list[tuple[str, int, int]] = []
        for path in self._asset_dir.iterdir():
            if path.is_file():
                stat = path.stat()
                entries.append((path.name, stat.st_size, stat.st_mtime_ns))
        entries.sort()
        return (
            catalog_stat.st_size,
            catalog_stat.st_mtime_ns,
            tuple(entries),
        )

    def _load(self) -> PveLibrarySnapshot:
        assert self._catalog_path is not None
        assert self._asset_dir is not None
        if not self._catalog_path.is_file():
            raise PveLibraryUnavailable(
                "PVE_LIBRARY_UNAVAILABLE",
                "The configured PVE catalog file is missing.",
            )
        if not self._asset_dir.is_dir():
            raise PveLibraryUnavailable(
                "PVE_LIBRARY_UNAVAILABLE",
                "The configured PVE asset directory is missing.",
            )
        try:
            before = self._fingerprint()
            raw_catalog = self._catalog_path.read_bytes()
            catalog = json.loads(
                raw_catalog.decode("utf-8"),
                object_pairs_hook=_strict_json_object,
                parse_constant=_reject_json_constant,
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, _StrictJsonError) as error:
            raise PveLibraryUnavailable(
                "PVE_LIBRARY_INVALID",
                "The configured PVE catalog cannot be read as UTF-8 JSON.",
                details={"reason": type(error).__name__},
            ) from error
        root = _expect_dict(catalog, "catalog")
        if set(root) != ROOT_FIELDS:
            raise _catalog_error("catalog top-level fields do not match the v1 schema")
        if root.get("schema_version") != CATALOG_SCHEMA_VERSION:
            raise _catalog_error("unsupported schema_version")
        builder = _expect_dict(root.get("builder"), "catalog.builder")
        if set(builder) != {"name", "version"}:
            raise _catalog_error("catalog.builder fields do not match the v1 schema")
        if builder.get("name") != "pcr-private-pve-catalog" or builder.get("version") != "1.0.0":
            raise _catalog_error("unsupported catalog builder")

        assets_by_sha256 = self._validate_assets(root)
        stages, stages_by_id, source_workbooks = self._validate_sources(
            root,
            set(assets_by_sha256),
        )
        summary = _expect_dict(root.get("summary"), "catalog.summary")
        expected_counts = {
            "source_workbook_count": len(source_workbooks),
            "asset_count": len(assets_by_sha256),
            "asset_occurrence_count": sum(
                len(_expect_list(asset.get("occurrences"), "catalog.assets[].occurrences"))
                for asset in _expect_list(root.get("assets"), "catalog.assets")
            ),
            "section_count": len(stages),
            "sheet_count": sum(
                len(_expect_list(source.get("sheets"), "catalog.sources[].sheets"))
                for source in _expect_list(root.get("sources"), "catalog.sources")
            ),
            "diagnostic_count": sum(
                len(_expect_list(source.get("diagnostics"), "catalog.sources[].diagnostics"))
                for source in _expect_list(root.get("sources"), "catalog.sources")
            ),
            "team_count": sum(len(record.section["teams"]) for record in stages),
            "axis_count": sum(
                len(team["axes"])
                for record in stages
                for team in record.section["teams"]
            ),
        }
        for field, actual in expected_counts.items():
            if _expect_int(summary.get(field), f"catalog.summary.{field}") != actual:
                raise _catalog_error(f"catalog.summary.{field} does not match content")

        try:
            after = self._fingerprint()
        except OSError as error:
            raise PveLibraryUnavailable(
                "PVE_LIBRARY_UNAVAILABLE",
                "The local PVE library changed while it was being loaded.",
            ) from error
        if before != after:
            raise PveLibraryUnavailable(
                "PVE_LIBRARY_UNAVAILABLE",
                "The local PVE library changed while it was being loaded.",
            )
        return PveLibrarySnapshot(
            dataset_sha256=_sha256(raw_catalog),
            schema_version=CATALOG_SCHEMA_VERSION,
            source_workbooks=tuple(source_workbooks),
            stages=tuple(stages),
            stages_by_id=MappingProxyType(stages_by_id),
            assets_by_sha256=MappingProxyType(assets_by_sha256),
            fingerprint=after,
        )

    def _validate_assets(self, root: Mapping[str, Any]) -> dict[str, AssetRecord]:
        assert self._asset_dir is not None
        raw_assets = _expect_list(root.get("assets"), "catalog.assets")
        assets: dict[str, AssetRecord] = {}
        expected_filenames: set[str] = set()
        for index, raw_asset in enumerate(raw_assets):
            path = f"catalog.assets[{index}]"
            asset = _expect_dict(raw_asset, path)
            sha256 = asset.get("sha256")
            if not _is_sha256(sha256):
                raise _catalog_error(f"{path}.sha256 must be lowercase SHA-256")
            if sha256 in assets:
                raise _catalog_error(f"duplicate asset SHA-256: {sha256}")
            extension = _expect_string(asset.get("file_extension"), f"{path}.file_extension")
            mime_type = _expect_string(asset.get("mime_type"), f"{path}.mime_type")
            filename = _expect_string(asset.get("filename"), f"{path}.filename")
            byte_length = _expect_int(
                asset.get("byte_length"),
                f"{path}.byte_length",
                minimum=1,
            )
            allowed = {"jpg": "image/jpeg", "png": "image/png"}
            if extension not in allowed or mime_type != allowed[extension]:
                raise _catalog_error(f"{path} has an unsupported media type")
            expected_filename = f"{sha256}.{extension}"
            if filename != expected_filename or Path(filename).name != filename:
                raise _catalog_error(f"{path}.filename is not the exact digest filename")
            asset_path = self._asset_dir / filename
            if asset_path.is_symlink() or not asset_path.is_file():
                raise _catalog_error(f"asset file is missing or is a symlink: {filename}")
            try:
                data = asset_path.read_bytes()
            except OSError as error:
                raise _catalog_error(f"asset file cannot be read: {filename}") from error
            if len(data) != byte_length or _sha256(data) != sha256:
                raise _catalog_error(f"asset file digest mismatch: {filename}")
            expected_filenames.add(filename)
            occurrences = _expect_list(asset.get("occurrences"), f"{path}.occurrences")
            for occurrence_index, raw_occurrence in enumerate(occurrences):
                occurrence_path = f"{path}.occurrences[{occurrence_index}]"
                occurrence = _expect_dict(raw_occurrence, occurrence_path)
                for field in ("anchor_cell", "sheet_name", "source_workbook_sha256"):
                    _expect_string(occurrence.get(field), f"{occurrence_path}.{field}")
                if not _is_sha256(occurrence["source_workbook_sha256"]):
                    raise _catalog_error(
                        f"{occurrence_path}.source_workbook_sha256 must be lowercase SHA-256"
                    )
                for field in ("row", "column", "width_px", "height_px"):
                    _expect_int(
                        occurrence.get(field),
                        f"{occurrence_path}.{field}",
                        minimum=1,
                    )
                expected_anchor = (
                    f"{_column_letters(occurrence['column'])}{occurrence['row']}"
                )
                if occurrence["anchor_cell"] != expected_anchor:
                    raise _catalog_error(
                        f"{occurrence_path}.anchor_cell does not match row/column"
                    )
            assets[sha256] = AssetRecord(
                sha256=sha256,
                filename=filename,
                mime_type=mime_type,
                byte_length=byte_length,
                path=asset_path,
            )

        actual_files = {path.name for path in self._asset_dir.iterdir() if path.is_file()}
        if actual_files != expected_filenames:
            raise _catalog_error("asset directory filenames do not exactly match catalog.assets")
        return assets

    def _validate_sources(
        self,
        root: Mapping[str, Any],
        asset_sha256s: set[str],
    ) -> tuple[list[StageRecord], dict[str, StageRecord], list[Mapping[str, Any]]]:
        raw_sources = _expect_list(root.get("sources"), "catalog.sources")
        stages: list[StageRecord] = []
        stages_by_id: dict[str, StageRecord] = {}
        source_workbooks: list[Mapping[str, Any]] = []
        source_sha256s: set[str] = set()
        source_sheet_pairs: set[tuple[str, str]] = set()
        team_ids: set[str] = set()
        axis_ids: set[str] = set()
        for source_index, raw_source in enumerate(raw_sources):
            source_path = f"catalog.sources[{source_index}]"
            source = _expect_dict(raw_source, source_path)
            workbook = _expect_dict(
                source.get("source_workbook"),
                f"{source_path}.source_workbook",
            )
            filename = _expect_string(
                workbook.get("filename"),
                f"{source_path}.source_workbook.filename",
            )
            workbook_sha256 = workbook.get("sha256")
            if not _is_sha256(workbook_sha256):
                raise _catalog_error(
                    f"{source_path}.source_workbook.sha256 must be lowercase SHA-256"
                )
            if not filename or Path(filename).name != filename:
                raise _catalog_error(f"{source_path}.source_workbook.filename must be a basename")
            if workbook_sha256 in source_sha256s:
                raise _catalog_error(f"duplicate source workbook SHA-256: {workbook_sha256}")
            source_sha256s.add(workbook_sha256)
            workbook_length = _expect_int(
                workbook.get("byte_length"),
                f"{source_path}.source_workbook.byte_length",
                minimum=1,
            )
            staging = _expect_dict(
                source.get("staging_catalog"),
                f"{source_path}.staging_catalog",
            )
            if staging.get("schema_version") != "private-pve-xlsx-staging/v1":
                raise _catalog_error(f"{source_path} has an unsupported staging schema")
            staging_sha256 = staging.get("sha256")
            if not _is_sha256(staging_sha256):
                raise _catalog_error(
                    f"{source_path}.staging_catalog.sha256 must be lowercase SHA-256"
                )
            workbook_view: Mapping[str, Any] = MappingProxyType(
                {
                    "filename": filename,
                    "sha256": workbook_sha256,
                    "byte_length": workbook_length,
                    "staging_catalog_sha256": staging_sha256,
                }
            )
            source_workbooks.append(workbook_view)

            sheets = _expect_list(source.get("sheets"), f"{source_path}.sheets")
            sheet_names: set[str] = set()
            for sheet_index, raw_sheet in enumerate(sheets):
                sheet_path = f"{source_path}.sheets[{sheet_index}]"
                sheet = _expect_dict(raw_sheet, sheet_path)
                sheet_name = _expect_string(sheet.get("sheet_name"), f"{sheet_path}.sheet_name")
                if not sheet_name or sheet_name in sheet_names:
                    raise _catalog_error(f"duplicate or empty sheet_name: {sheet_name}")
                sheet_names.add(sheet_name)
                source_sheet_pairs.add((workbook_sha256, sheet_name))
                sections = _expect_list(sheet.get("sections"), f"{sheet_path}.sections")
                for section_index, raw_section in enumerate(sections):
                    section_path = f"{sheet_path}.sections[{section_index}]"
                    section = _expect_dict(raw_section, section_path)
                    section_id = _expect_string(
                        section.get("section_id"),
                        f"{section_path}.section_id",
                    )
                    if not section_id or section_id in stages_by_id:
                        raise _catalog_error(f"duplicate or empty section_id: {section_id}")
                    for field in ("mode", "element", "source_range"):
                        _expect_string(section.get(field), f"{section_path}.{field}")
                    _expect_string(
                        section.get("label_raw"),
                        f"{section_path}.label_raw",
                        nullable=True,
                    )
                    stage_refs = _expect_list(
                        section.get("stage_refs"),
                        f"{section_path}.stage_refs",
                    )
                    if not stage_refs:
                        raise _catalog_error(f"{section_path}.stage_refs must not be empty")
                    for ref_index, raw_ref in enumerate(stage_refs):
                        ref_path = f"{section_path}.stage_refs[{ref_index}]"
                        ref = _expect_dict(raw_ref, ref_path)
                        _expect_exact_fields(ref, {"area", "kind", "stage"}, ref_path)
                        _expect_string(ref.get("kind"), f"{ref_path}.kind")
                        _expect_int(ref.get("area"), f"{ref_path}.area", minimum=1)
                        _expect_int(ref.get("stage"), f"{ref_path}.stage", minimum=1)
                    teams = _expect_list(section.get("teams"), f"{section_path}.teams")
                    for team_index, raw_team in enumerate(teams):
                        self._validate_team(
                            raw_team,
                            f"{section_path}.teams[{team_index}]",
                            asset_sha256s,
                            team_ids,
                            axis_ids,
                        )
                    display_orders = [team["display_order"] for team in teams]
                    if display_orders != list(range(1, len(teams) + 1)):
                        raise _catalog_error(
                            f"{section_path}.teams display_order must be exactly 1..N"
                        )
                    record = StageRecord(
                        section=section,
                        source_workbook=workbook_view,
                        staging_catalog=MappingProxyType(dict(staging)),
                        sheet_name=sheet_name,
                    )
                    stages.append(record)
                    stages_by_id[section_id] = record
        for asset_index, raw_asset in enumerate(
            _expect_list(root.get("assets"), "catalog.assets")
        ):
            asset = _expect_dict(raw_asset, f"catalog.assets[{asset_index}]")
            for occurrence_index, raw_occurrence in enumerate(
                _expect_list(asset.get("occurrences"), "catalog.assets[].occurrences")
            ):
                occurrence = _expect_dict(
                    raw_occurrence,
                    f"catalog.assets[{asset_index}].occurrences[{occurrence_index}]",
                )
                pair = (
                    occurrence["source_workbook_sha256"],
                    occurrence["sheet_name"],
                )
                if pair not in source_sheet_pairs:
                    raise _catalog_error(
                        "asset occurrence references an unknown source workbook sheet"
                    )
        return stages, stages_by_id, source_workbooks

    def _validate_team(
        self,
        raw_team: object,
        path: str,
        asset_sha256s: set[str],
        team_ids: set[str],
        axis_ids: set[str],
    ) -> None:
        team = _expect_dict(raw_team, path)
        team_id = _expect_string(team.get("team_source_id"), f"{path}.team_source_id")
        if not team_id or team_id in team_ids:
            raise _catalog_error(f"duplicate or empty team_source_id: {team_id}")
        team_ids.add(team_id)
        _expect_int(team.get("display_order"), f"{path}.display_order", minimum=1)
        _expect_string(team.get("notes_raw"), f"{path}.notes_raw", nullable=True)
        _expect_string(team.get("source_range"), f"{path}.source_range")
        flags = _expect_list(team.get("flags"), f"{path}.flags")
        if not all(isinstance(flag, str) for flag in flags):
            raise _catalog_error(f"{path}.flags must contain only strings")

        formation = _expect_list(team.get("formation"), f"{path}.formation")
        if len(formation) != 5:
            raise _catalog_error(f"{path}.formation must contain exactly five portraits")
        positions: list[int] = []
        for member_index, raw_member in enumerate(formation):
            member_path = f"{path}.formation[{member_index}]"
            member = _expect_dict(raw_member, member_path)
            position = _expect_int(
                member.get("display_position"),
                f"{member_path}.display_position",
                minimum=1,
            )
            positions.append(position)
            sha256 = member.get("image_sha256")
            if not _is_sha256(sha256) or sha256 not in asset_sha256s:
                raise _catalog_error(f"{member_path}.image_sha256 is not a catalog asset")
            _expect_string(member.get("anchor_cell"), f"{member_path}.anchor_cell")
            for field in (
                "mapping_status",
                "mapping_reason",
                "unit_key",
                "tw_name",
                "estertion_base_id",
                "icon_id",
            ):
                if field in member:
                    _expect_string(
                        member[field],
                        f"{member_path}.{field}",
                        nullable=True,
                    )
            if "display_rarity" in member:
                display_rarity = _expect_string(
                    member["display_rarity"],
                    f"{member_path}.display_rarity",
                    nullable=True,
                )
                if display_rarity not in {None, "THREE_STAR", "SIX_STAR"}:
                    raise _catalog_error(
                        f"{member_path}.display_rarity is not supported"
                    )
            if "display_source" in member:
                _expect_string(
                    member["display_source"],
                    f"{member_path}.display_source",
                    nullable=True,
                )
        if positions != [1, 2, 3, 4, 5]:
            raise _catalog_error(f"{path}.formation positions must be ordered exactly 1..5")

        axes = _expect_list(team.get("axes"), f"{path}.axes")
        if not axes and team_id not in ZERO_AXIS_TEAM_IDS:
            raise _catalog_error(f"{path}.axes is empty for a non-allowlisted team")
        for axis_index, raw_axis in enumerate(axes):
            axis_path = f"{path}.axes[{axis_index}]"
            axis = _expect_dict(raw_axis, axis_path)
            axis_id = _expect_string(axis.get("axis_source_id"), f"{axis_path}.axis_source_id")
            if not axis_id or axis_id in axis_ids:
                raise _catalog_error(f"duplicate or empty axis_source_id: {axis_id}")
            axis_ids.add(axis_id)
            _expect_string(axis.get("operation_raw"), f"{axis_path}.operation_raw", nullable=True)
            _expect_string(axis.get("notes_raw"), f"{axis_path}.notes_raw", nullable=True)
            _expect_string(axis.get("source_cell"), f"{axis_path}.source_cell")
            _validate_operation(axis.get("operation"), f"{axis_path}.operation")
            axis_refs = _expect_list(axis.get("source_refs"), f"{axis_path}.source_refs")
            for ref_index, raw_ref in enumerate(axis_refs):
                _validate_source_ref(raw_ref, f"{axis_path}.source_refs[{ref_index}]")
        source_refs = _expect_list(team.get("source_refs"), f"{path}.source_refs")
        for ref_index, raw_ref in enumerate(source_refs):
            _validate_source_ref(raw_ref, f"{path}.source_refs[{ref_index}]")


def pve_meta(snapshot: PveLibrarySnapshot) -> dict[str, Any]:
    return {
        "api_version": "v1",
        "schema_version": snapshot.schema_version,
        "dataset_sha256": snapshot.dataset_sha256,
        "source_status": "SOURCE_PROVIDED",
        "independent_clear_verification": "NOT_PERFORMED",
        "source_workbooks": [dict(workbook) for workbook in snapshot.source_workbooks],
    }


def provenance_view(record: StageRecord, source_range: str) -> dict[str, Any]:
    return {
        "source_workbook_sha256": record.source_workbook["sha256"],
        "source_workbook_filename": record.source_workbook["filename"],
        "staging_catalog_sha256": record.source_workbook["staging_catalog_sha256"],
        "sheet_name": record.sheet_name,
        "source_range": source_range,
    }


def stage_summary_view(record: StageRecord) -> dict[str, Any]:
    section = record.section
    return {
        "stage_id": section["section_id"],
        "mode": section["mode"],
        "element": section["element"],
        "label_raw": section["label_raw"],
        "stage_refs": [dict(stage_ref) for stage_ref in section["stage_refs"]],
        "team_count": len(section["teams"]),
        "provenance": provenance_view(record, section["source_range"]),
    }


def _nonempty_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _allowed_estertion_icon_url(icon_id: str) -> str | None:
    candidate = f"{ESTERTION_ICON_ORIGIN}/icon/unit/{icon_id}.webp"
    parsed = urlsplit(candidate)
    try:
        port = parsed.port
    except ValueError:
        return None
    path_match = ESTERTION_ICON_PATH_PATTERN.fullmatch(parsed.path)
    if (
        parsed.scheme != "https"
        or parsed.hostname != ESTERTION_ICON_HOST
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
        or path_match is None
        or path_match.group(1) != icon_id
    ):
        return None
    return candidate


def _estertion_icon_url(
    member: Mapping[str, Any],
    *,
    external_icons_enabled: bool,
) -> str | None:
    if not external_icons_enabled:
        return None
    mapping_reason = member.get("mapping_reason")
    if (
        member.get("mapping_status") != "RESOLVED"
        or mapping_reason
        not in {"EXACT_VARIANT", "EXACT_SIX_STAR_ICON_MISSING"}
        or member.get("display_source") != "ESTERTION"
        or _nonempty_text(member.get("unit_key")) is None
        or _nonempty_text(member.get("tw_name")) is None
    ):
        return None

    base_id = member.get("estertion_base_id")
    icon_id = member.get("icon_id")
    if (
        not isinstance(base_id, str)
        or ESTERTION_ICON_BASE_ID_PATTERN.fullmatch(base_id) is None
        or not isinstance(icon_id, str)
        or ESTERTION_ICON_ID_PATTERN.fullmatch(icon_id) is None
    ):
        return None

    rarity_suffix = {
        "THREE_STAR": "31",
        "SIX_STAR": "61",
    }.get(member.get("display_rarity"))
    if (
        rarity_suffix is None
        or icon_id != f"{base_id}{rarity_suffix}"
        or (
            mapping_reason == "EXACT_SIX_STAR_ICON_MISSING"
            and member.get("display_rarity") != "THREE_STAR"
        )
    ):
        return None
    return _allowed_estertion_icon_url(icon_id)


def _portrait_view(
    member: Mapping[str, Any],
    *,
    external_icons_enabled: bool,
) -> dict[str, Any]:
    icon_url = _estertion_icon_url(
        member,
        external_icons_enabled=external_icons_enabled,
    )
    return {
        "display_position": member["display_position"],
        "asset_sha256": member["image_sha256"],
        "asset_url": "/api/v1/pve-library/assets/" + member["image_sha256"],
        "icon_url": icon_url,
        "mapping_status": member.get("mapping_status") or "UNMAPPED",
        "unit_key": member.get("unit_key"),
        "tw_name": member.get("tw_name"),
        "display_rarity": member.get("display_rarity") if icon_url else None,
        "display_source": "ESTERTION" if icon_url else "WORKBOOK_EMBEDDED",
        "anchor_cell": member["anchor_cell"],
    }


def stage_detail_view(
    record: StageRecord,
    *,
    external_icons_enabled: bool = False,
) -> dict[str, Any]:
    result = stage_summary_view(record)
    teams: list[dict[str, Any]] = []
    for team in record.section["teams"]:
        teams.append(
            {
                "team_id": team["team_source_id"],
                "display_order": team["display_order"],
                "notes_raw": team["notes_raw"],
                "flags": list(team["flags"]),
                "source_range": team["source_range"],
                "portraits": [
                    _portrait_view(
                        member,
                        external_icons_enabled=external_icons_enabled,
                    )
                    for member in sorted(
                        team["formation"],
                        key=lambda item: item["display_position"],
                    )
                ],
                "axes": [
                    {
                        "axis_id": axis["axis_source_id"],
                        "operation_raw": axis["operation_raw"],
                        "notes_raw": axis["notes_raw"],
                        "source_cell": axis["source_cell"],
                        "operation": axis["operation"],
                        "source_links": [
                            source_link_view(ref) for ref in axis["source_refs"]
                        ],
                    }
                    for axis in team["axes"]
                ],
                "source_links": [source_link_view(ref) for ref in team["source_refs"]],
                "provenance": provenance_view(record, team["source_range"]),
            }
        )
    result["teams"] = teams
    return result


def filter_stages(
    snapshot: PveLibrarySnapshot,
    *,
    mode: str | None,
    element: str | None,
    area: int | None,
    stage: int | None,
) -> list[StageRecord]:
    result: list[StageRecord] = []
    for record in snapshot.stages:
        section = record.section
        if mode is not None and section["mode"] != mode:
            continue
        if element is not None and section["element"] != element:
            continue
        if area is not None or stage is not None:
            if not any(
                (area is None or ref["area"] == area)
                and (stage is None or ref["stage"] == stage)
                for ref in section["stage_refs"]
            ):
                continue
        result.append(record)
    return result


def available_stage_filters(
    snapshot: PveLibrarySnapshot,
    *,
    mode: str | None,
    element: str | None,
) -> dict[str, list[str] | list[int]]:
    """Return deterministic choices without applying the current area/stage choice.

    Modes describe the whole loaded catalog. Elements are scoped by mode, while
    areas and stages are scoped by both mode and element. This makes the response
    useful for dependent dropdowns and lets newly imported positive area/stage
    values appear without an API change.
    """

    modes = {record.section["mode"] for record in snapshot.stages}
    elements = {
        record.section["element"]
        for record in snapshot.stages
        if mode is None or record.section["mode"] == mode
    }
    ref_scope = (
        record
        for record in snapshot.stages
        if (mode is None or record.section["mode"] == mode)
        and (element is None or record.section["element"] == element)
    )
    refs = [ref for record in ref_scope for ref in record.section["stage_refs"]]
    return {
        "modes": sorted(modes),
        "elements": sorted(elements),
        "areas": sorted({ref["area"] for ref in refs}),
        "stages": sorted({ref["stage"] for ref in refs}),
    }
