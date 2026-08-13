from __future__ import annotations

import hashlib
import io
import json
import posixpath
import re
import threading
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping
from xml.etree import ElementTree

from pcr_pipeline.gacha_ingest.docx import (
    GachaDocxError,
    canonical_json_bytes as replay_json_bytes,
    extract_gacha_forecast_docx,
)

from .config import Settings


CATALOG_SCHEMA_VERSION = "gacha-community-docx-candidates/v1"
SOURCE_ID = "GACHA-COMM-002"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CANDIDATE_ID_PATTERN = re.compile(r"^GACHA-DOCX-[0-9a-f]{24}$")
RELATIONSHIP_ID_PATTERN = re.compile(r"^rId[1-9][0-9]*$")
PARAGRAPH_LOCATOR_PATTERN = re.compile(
    r"^word/document\.xml#paragraph=([1-9][0-9]*)$"
)
IMAGE_LOCATOR_PATTERN = re.compile(
    r"^word/document\.xml#paragraph=([1-9][0-9]*);image=([1-9][0-9]*)$"
)
SEQUENCE_LABEL_PATTERN = re.compile(r"^第([1-9][0-9]*)次$")
FORECAST_TEXT_PATTERN = re.compile(
    r"^台服預測\s*"
    r"(?P<start_year>\d{4})/(?P<start_month>\d{1,2})/(?P<start_day>\d{1,2})"
    r"\s*[～~〜]\s*"
    r"(?:(?P<end_year>\d{4})/)?(?P<end_month>\d{1,2})/(?P<end_day>\d{1,2})$"
)
SEQUENCE_PREFIX_PATTERN = re.compile(r"^第\s*[1-9][0-9]*\s*次")
UNQUOTED_VARIANT_PATTERN = re.compile(
    r"[^\s「」、,，（）()]+[（(][^「」（）()]+[）)]"
)

ROOT_FIELDS = {"candidates", "document", "schema_version", "source", "summary"}
SOURCE_FIELDS = {
    "authority",
    "capture_method",
    "document_byte_length",
    "document_sha256",
    "embedded_image_policy",
    "independence_group",
    "source_id",
    "source_id_origin",
}
DOCUMENT_FIELDS = {
    "body_paragraph_count",
    "comments_present",
    "referenced_image_count",
    "table_count",
    "tracked_changes_present",
}
CANDIDATE_FIELDS = {
    "candidate_id",
    "date_boundary_semantics",
    "description_locators",
    "forecast_end",
    "forecast_start",
    "identity_status",
    "image",
    "image_locator",
    "parser_warnings",
    "precision",
    "promotion_eligible",
    "proposed_event_id",
    "raw_character_names",
    "raw_description_lines",
    "raw_forecast_text",
    "raw_sequence_label",
    "review_order",
    "review_reason",
    "review_status",
    "source_locator",
    "source_declared_pool_kind",
}
IMAGE_FIELDS = {
    "byte_length",
    "filename",
    "mime_type",
    "package_path",
    "relationship_id",
    "sha256",
}
SUMMARY_FIELDS = {
    "candidate_count",
    "canonical_write_count",
    "character_label_count",
    "coverage_end",
    "coverage_start",
    "pool_kind_counts",
    "review_status_counts",
    "unique_date_window_count",
    "warning_counts",
}
POOL_KINDS = {"LIMITED_PICKUP", "PERMANENT_PICKUP", "RERUN"}
PARSER_WARNINGS = {"UNQUOTED_CHARACTER_SEQUENCE"}
MIME_EXTENSIONS = {
    "image/jpeg": {"jpg", "jpeg"},
    "image/png": {"png"},
    "image/webp": {"webp"},
}

MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_ENTRY_COUNT = 1_024
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_SINGLE_ENTRY_BYTES = 25 * 1024 * 1024
MAX_COMPRESSION_RATIO = 250

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
W = f"{{{W_NS}}}"
A = f"{{{A_NS}}}"
R = f"{{{R_NS}}}"


class GachaLibraryUnavailable(RuntimeError):
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


class GachaLibraryNotFound(LookupError):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(identifier)
        self.resource = resource
        self.identifier = identifier


@dataclass(frozen=True)
class GachaAssetRecord:
    sha256: str
    mime_type: str
    byte_length: int
    package_path: str
    data: bytes


@dataclass(frozen=True)
class GachaLibrarySnapshot:
    dataset_sha256: str
    schema_version: str
    source: Mapping[str, Any]
    document: Mapping[str, Any]
    candidates: tuple[Mapping[str, Any], ...]
    assets_by_sha256: Mapping[str, GachaAssetRecord]
    catalog_fingerprint: tuple[int, str]
    docx_fingerprint: tuple[int, str]


class _StrictJsonError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _StrictJsonError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise _StrictJsonError(f"non-finite JSON number: {value}")


def _invalid(reason: str) -> GachaLibraryUnavailable:
    return GachaLibraryUnavailable(
        "GACHA_LIBRARY_INVALID",
        "The configured Gacha forecast library failed validation.",
        details={"reason": reason},
    )


def _expect_dict(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _invalid(f"{path} must be an object")
    return value


def _expect_exact_fields(
    value: Mapping[str, Any], fields: set[str], path: str
) -> None:
    if set(value) != fields:
        raise _invalid(f"{path} fields do not match the v1 schema")


def _expect_list(value: object, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise _invalid(f"{path} must be an array")
    return value


def _expect_string(
    value: object,
    path: str,
    *,
    nullable: bool = False,
    nonempty: bool = True,
) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str):
        raise _invalid(f"{path} must be a string")
    if nonempty and (not value or value != value.strip()):
        raise _invalid(f"{path} must be a nonempty, trimmed string")
    return value


def _expect_int(value: object, path: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise _invalid(f"{path} must be an integer >= {minimum}")
    return value


def _expect_bool(value: object, expected: bool, path: str) -> None:
    if type(value) is not bool or value is not expected:
        raise _invalid(f"{path} must be {str(expected).lower()}")


def _expect_sha256(value: object, path: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise _invalid(f"{path} must be lowercase SHA-256")
    return value


def _parse_iso_date(value: object, path: str) -> date:
    text = _expect_string(value, path)
    assert text is not None
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise _invalid(f"{path} must be an ISO calendar date") from error
    if parsed.isoformat() != text:
        raise _invalid(f"{path} must be a canonical ISO calendar date")
    return parsed


def _paragraph_number(locator: object, path: str) -> int:
    text = _expect_string(locator, path)
    assert text is not None
    match = PARAGRAPH_LOCATOR_PATTERN.fullmatch(text)
    if match is None:
        raise _invalid(f"{path} must be an exact paragraph locator")
    return int(match.group(1))


def _image_paragraph(locator: object, path: str) -> tuple[int, int]:
    text = _expect_string(locator, path)
    assert text is not None
    match = IMAGE_LOCATOR_PATTERN.fullmatch(text)
    if match is None:
        raise _invalid(f"{path} must be an exact image locator")
    return int(match.group(1)), int(match.group(2))


def _parse_raw_forecast(value: object, path: str) -> tuple[date, date]:
    text = _expect_string(value, path)
    assert text is not None
    match = FORECAST_TEXT_PATTERN.fullmatch(text)
    if match is None:
        raise _invalid(f"{path} is not a supported Taiwan forecast line")
    start_year = int(match.group("start_year"))
    end_year = int(match.group("end_year") or start_year)
    try:
        start = date(
            start_year,
            int(match.group("start_month")),
            int(match.group("start_day")),
        )
        end = date(
            end_year,
            int(match.group("end_month")),
            int(match.group("end_day")),
        )
    except ValueError as error:
        raise _invalid(f"{path} contains an invalid calendar date") from error
    if end < start:
        raise _invalid(f"{path} has a reversed or implicit cross-year interval")
    return start, end


def _expected_pool_kind(lines: list[str], path: str) -> str:
    joined = "\n".join(lines)
    markers = {
        "RERUN": "復刻池" in joined,
        "LIMITED_PICKUP": "限定UP角色" in joined,
        "PERMANENT_PICKUP": "常駐角色" in joined,
    }
    matched = [kind for kind, present in markers.items() if present]
    if len(matched) != 1:
        raise _invalid(f"{path} must contain exactly one explicit pool-kind marker")
    return matched[0]


def _validate_character_token(token: str, path: str) -> None:
    if (
        token.count("(") != token.count(")")
        or token.count("（") != token.count("）")
        or "「" in token
        or "」" in token
    ):
        raise _invalid(f"{path} contains unbalanced character punctuation")


def _parse_character_line(line: str, path: str) -> tuple[list[str], str]:
    text = line.strip()
    text = SEQUENCE_PREFIX_PATTERN.sub("", text, count=1).strip()
    for prefix in ("限定UP角色", "常駐角色"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    if text.endswith("復刻池"):
        text = text[: -len("復刻池")].strip()
    if not text:
        raise _invalid(f"{path} contains no character text")

    tokens: list[str] = []
    styles: set[str] = set()
    position = 0
    while position < len(text):
        delimiter = re.match(r"[\s、,，]+", text[position:])
        if delimiter is not None:
            position += delimiter.end()
            continue
        if text[position] == "「":
            closing = text.find("」", position + 1)
            if closing < 0:
                raise _invalid(f"{path} contains an unbalanced character quote")
            token = text[position + 1 : closing].strip()
            if not token or "「" in token:
                raise _invalid(f"{path} contains an invalid quoted character label")
            styles.add("QUOTED")
            position = closing + 1
        else:
            match = UNQUOTED_VARIANT_PATTERN.match(text, position)
            if match is None:
                raise _invalid(f"{path} contains residual or unparsed character text")
            token = match.group(0).strip()
            styles.add("UNQUOTED")
            position = match.end()
        _validate_character_token(token, path)
        tokens.append(token)
    if len(styles) != 1:
        raise _invalid(f"{path} mixes quoted and unquoted character text")
    return tokens, next(iter(styles))


def _expected_raw_names(
    lines: list[str], path: str
) -> tuple[list[str], list[str]]:
    names: list[str] = []
    warnings: list[str] = []
    for line_index, line in enumerate(lines):
        tokens, style = _parse_character_line(
            line, f"{path}.raw_description_lines[{line_index}]"
        )
        names.extend(tokens)
        if style == "UNQUOTED":
            warnings.append("UNQUOTED_CHARACTER_SEQUENCE")
    return names, sorted(set(warnings))


def _validate_count_map(value: object, path: str) -> dict[str, int]:
    raw = _expect_dict(value, path)
    result: dict[str, int] = {}
    for key, count in raw.items():
        normalized = _expect_string(key, f"{path} key")
        assert normalized is not None
        result[normalized] = _expect_int(count, f"{path}.{normalized}")
    return result


def _validate_candidate(
    raw_candidate: object,
    *,
    index: int,
    document_sha256: str,
    source_id: str,
    body_paragraph_count: int,
) -> tuple[dict[str, Any], tuple[int, int]]:
    path = f"catalog.candidates[{index}]"
    candidate = _expect_dict(raw_candidate, path)
    _expect_exact_fields(candidate, CANDIDATE_FIELDS, path)

    candidate_id = _expect_string(candidate["candidate_id"], f"{path}.candidate_id")
    assert candidate_id is not None
    if CANDIDATE_ID_PATTERN.fullmatch(candidate_id) is None:
        raise _invalid(f"{path}.candidate_id has an invalid format")
    if candidate["review_order"] != index + 1:
        raise _invalid("catalog.candidates review_order must be exactly 1..N")
    _expect_int(candidate["review_order"], f"{path}.review_order", minimum=1)

    start = _parse_iso_date(candidate["forecast_start"], f"{path}.forecast_start")
    end = _parse_iso_date(candidate["forecast_end"], f"{path}.forecast_end")
    if end < start:
        raise _invalid(f"{path} forecast interval is reversed")
    raw_start, raw_end = _parse_raw_forecast(
        candidate["raw_forecast_text"], f"{path}.raw_forecast_text"
    )
    if (start, end) != (raw_start, raw_end):
        raise _invalid(f"{path} normalized dates differ from raw_forecast_text")

    if candidate["precision"] != "DAY":
        raise _invalid(f"{path}.precision must remain DAY")
    if candidate["date_boundary_semantics"] != "SOURCE_UNSPECIFIED":
        raise _invalid(
            f"{path}.date_boundary_semantics must remain SOURCE_UNSPECIFIED"
        )
    if candidate["identity_status"] != "UNVERIFIED_COMMUNITY_NAME":
        raise _invalid(f"{path}.identity_status must remain unverified")
    if candidate["review_status"] != "PENDING":
        raise _invalid(f"{path}.review_status must remain PENDING")
    _expect_bool(candidate["promotion_eligible"], False, f"{path}.promotion_eligible")
    if candidate["proposed_event_id"] is not None:
        raise _invalid(f"{path}.proposed_event_id must remain null")

    raw_lines = _expect_list(candidate["raw_description_lines"], f"{path}.raw_description_lines")
    description_lines: list[str] = []
    for line_index, raw_line in enumerate(raw_lines):
        line = _expect_string(raw_line, f"{path}.raw_description_lines[{line_index}]")
        assert line is not None
        description_lines.append(line)
    if not description_lines:
        raise _invalid(f"{path}.raw_description_lines must not be empty")

    description_locators = _expect_list(
        candidate["description_locators"], f"{path}.description_locators"
    )
    if len(description_locators) != len(description_lines):
        raise _invalid(f"{path} description locators and lines differ in length")
    description_paragraphs = [
        _paragraph_number(locator, f"{path}.description_locators[{locator_index}]")
        for locator_index, locator in enumerate(description_locators)
    ]
    if description_paragraphs != sorted(set(description_paragraphs)):
        raise _invalid(f"{path}.description_locators must be unique and ordered")

    forecast_paragraph = _paragraph_number(
        candidate["source_locator"], f"{path}.source_locator"
    )
    image_paragraph, image_index = _image_paragraph(
        candidate["image_locator"], f"{path}.image_locator"
    )
    if image_index != 1:
        raise _invalid(f"{path}.image_locator must point to the only image in its paragraph")
    if not (
        description_paragraphs[-1] < forecast_paragraph < image_paragraph
        <= body_paragraph_count
    ):
        raise _invalid(f"{path} paragraph locators are inconsistent")

    expected_pool = _expected_pool_kind(description_lines, path)
    if (
        candidate["source_declared_pool_kind"] not in POOL_KINDS
        or candidate["source_declared_pool_kind"] != expected_pool
    ):
        raise _invalid(
            f"{path}.source_declared_pool_kind differs from its explicit source marker"
        )

    expected_names, expected_warnings = _expected_raw_names(description_lines, path)
    raw_names = _expect_list(candidate["raw_character_names"], f"{path}.raw_character_names")
    names: list[str] = []
    for name_index, raw_name in enumerate(raw_names):
        name = _expect_string(raw_name, f"{path}.raw_character_names[{name_index}]")
        assert name is not None
        names.append(name)
    if not names or names != expected_names:
        raise _invalid(f"{path}.raw_character_names differ from source text")

    raw_warnings = _expect_list(candidate["parser_warnings"], f"{path}.parser_warnings")
    warnings: list[str] = []
    for warning_index, raw_warning in enumerate(raw_warnings):
        warning = _expect_string(
            raw_warning, f"{path}.parser_warnings[{warning_index}]"
        )
        assert warning is not None
        if warning not in PARSER_WARNINGS:
            raise _invalid(f"{path}.parser_warnings contains an unknown warning")
        warnings.append(warning)
    if warnings != sorted(set(warnings)) or warnings != expected_warnings:
        raise _invalid(f"{path}.parser_warnings differ from source text")
    expected_reason = (
        "UNDELIMITED_CHARACTER_TEXT_REQUIRES_REVIEW"
        if warnings
        else "EXACT_EVENT_LINK_NOT_REVIEWED"
    )
    if candidate["review_reason"] != expected_reason:
        raise _invalid(f"{path}.review_reason differs from parser warnings")

    sequence = candidate["raw_sequence_label"]
    if sequence is not None:
        sequence_text = _expect_string(sequence, f"{path}.raw_sequence_label")
        assert sequence_text is not None
        match = SEQUENCE_LABEL_PATTERN.fullmatch(sequence_text)
        if match is None or sequence_text not in "\n".join(description_lines):
            raise _invalid(f"{path}.raw_sequence_label is not present in source text")

    image = _expect_dict(candidate["image"], f"{path}.image")
    _expect_exact_fields(image, IMAGE_FIELDS, f"{path}.image")
    image_sha256 = _expect_sha256(image["sha256"], f"{path}.image.sha256")
    _expect_int(image["byte_length"], f"{path}.image.byte_length", minimum=1)
    filename = _expect_string(image["filename"], f"{path}.image.filename")
    package_path = _expect_string(image["package_path"], f"{path}.image.package_path")
    relationship_id = _expect_string(
        image["relationship_id"], f"{path}.image.relationship_id"
    )
    mime_type = _expect_string(image["mime_type"], f"{path}.image.mime_type")
    assert filename is not None and package_path is not None
    assert relationship_id is not None and mime_type is not None
    if (
        Path(filename).name != filename
        or package_path != f"word/media/{filename}"
        or posixpath.normpath(package_path) != package_path
    ):
        raise _invalid(f"{path}.image package path is not exact and safe")
    if RELATIONSHIP_ID_PATTERN.fullmatch(relationship_id) is None:
        raise _invalid(f"{path}.image.relationship_id has an invalid format")
    extension = PurePosixPath(filename).suffix.lower().lstrip(".")
    if mime_type not in MIME_EXTENSIONS or extension not in MIME_EXTENSIONS[mime_type]:
        raise _invalid(f"{path}.image MIME type and filename disagree")

    identity_payload = {
        "description_lines": description_lines,
        "document_sha256": document_sha256,
        "forecast_end": end.isoformat(),
        "forecast_start": start.isoformat(),
        "image_sha256": image_sha256,
        "source_id": source_id,
        "source_locator": candidate["source_locator"],
    }
    expected_id = "GACHA-DOCX-" + _sha256(_canonical_json_bytes(identity_payload))[:24]
    if candidate_id != expected_id:
        raise _invalid(f"{path}.candidate_id does not close over source identity")

    return candidate, (description_paragraphs[0], image_paragraph)


def _validate_archive_entries(archive: zipfile.ZipFile) -> set[str]:
    infos = archive.infolist()
    if not infos or len(infos) > MAX_ENTRY_COUNT:
        raise _invalid("DOCX ZIP entry count is outside the supported range")
    names: set[str] = set()
    total_uncompressed = 0
    for info in infos:
        name = info.filename
        normalized = name.replace("\\", "/")
        path = PurePosixPath(normalized)
        unix_mode = (info.external_attr >> 16) & 0o170000
        if (
            normalized != name
            or normalized.startswith("/")
            or any(part in {"", ".", ".."} for part in path.parts)
            or unix_mode == 0o120000
        ):
            raise _invalid("DOCX ZIP contains an unsafe entry path")
        if normalized in names:
            raise _invalid("DOCX ZIP contains duplicate entries")
        if info.flag_bits & 0x1:
            raise _invalid("encrypted DOCX ZIP entries are unsupported")
        if (
            normalized == "word/vbaProject.bin"
            or normalized.startswith(("word/activeX/", "word/embeddings/"))
        ):
            raise _invalid("active, macro, or embedded DOCX content is unsupported")
        if info.file_size > MAX_SINGLE_ENTRY_BYTES:
            raise _invalid("DOCX ZIP contains an oversized entry")
        if (
            info.file_size > 1_048_576
            and info.compress_size > 0
            and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO
        ):
            raise _invalid("DOCX ZIP contains an unsafe compression ratio")
        names.add(normalized)
        total_uncompressed += info.file_size
    if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
        raise _invalid("DOCX ZIP uncompressed size is too large")
    return names


def _has_valid_magic(payload: bytes, mime_type: str) -> bool:
    if mime_type == "image/jpeg":
        return len(payload) >= 5 and payload.startswith(b"\xff\xd8\xff") and payload.endswith(b"\xff\xd9")
    if mime_type == "image/png":
        return len(payload) >= 8 and payload.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/webp":
        return len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WEBP"
    return False


def _read_docx_xml(
    archive: zipfile.ZipFile,
    entries: set[str],
    package_path: str,
) -> ElementTree.Element:
    if package_path not in entries:
        raise _invalid(f"DOCX is missing required package part: {package_path}")
    try:
        payload = archive.read(package_path)
    except (KeyError, OSError, RuntimeError) as error:
        raise _invalid(f"DOCX package part cannot be read: {package_path}") from error
    try:
        decoded = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise _invalid("DOCX XML parts must use UTF-8 encoding") from error
    upper = decoded.upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        raise _invalid("DTD and entity declarations are forbidden in DOCX XML")
    declaration = re.match(
        r"\s*<\?xml\s+[^>]*encoding=['\"]([^'\"]+)['\"]",
        decoded,
    )
    if (
        declaration is not None
        and declaration.group(1).lower().replace("_", "-")
        not in {"utf-8", "us-ascii"}
    ):
        raise _invalid("DOCX XML declares a non-UTF-8 encoding")
    try:
        return ElementTree.fromstring(decoded)
    except ElementTree.ParseError as error:
        raise _invalid(f"DOCX contains invalid XML: {package_path}") from error


def _relationship_package_path(target: str) -> str:
    if not target or "\\" in target or target.startswith("/"):
        raise _invalid("DOCX contains an unsafe image relationship target")
    package_path = posixpath.normpath(posixpath.join("word", target))
    if (
        not package_path.startswith("word/media/")
        or ".." in PurePosixPath(package_path).parts
    ):
        raise _invalid("DOCX image relationship escapes word/media")
    return package_path


def _inspect_docx_provenance(
    archive: zipfile.ZipFile,
    entries: set[str],
) -> dict[str, Any]:
    document_root = _read_docx_xml(
        archive, entries, "word/document.xml"
    )
    relationships_root = _read_docx_xml(
        archive, entries, "word/_rels/document.xml.rels"
    )
    content_types_root = _read_docx_xml(
        archive, entries, "[Content_Types].xml"
    )
    forbidden_content_type_markers = (
        "macroenabled",
        "vba",
        "activex",
        "oleobject",
    )
    for item in content_types_root:
        if item.tag not in {
            f"{{{CT_NS}}}Default",
            f"{{{CT_NS}}}Override",
        }:
            raise _invalid("DOCX content types contain an unsupported element")
        content_type = item.attrib.get("ContentType", "").lower()
        if any(marker in content_type for marker in forbidden_content_type_markers):
            raise _invalid("DOCX declares an active or macro-enabled content type")
    relationships: dict[str, str] = {}
    for relationship in relationships_root.findall(f"{{{REL_NS}}}Relationship"):
        relationship_id = relationship.attrib.get("Id", "")
        if not relationship_id or relationship_id in relationships:
            raise _invalid("DOCX relationship ids must be unique and nonempty")
        if relationship.attrib.get("TargetMode", "Internal").lower() == "external":
            raise _invalid("external DOCX relationships are forbidden")
        if not relationship.attrib.get("Type", "").endswith("/image"):
            continue
        relationships[relationship_id] = _relationship_package_path(
            relationship.attrib.get("Target", "")
        )

    body = document_root.find(f"{W}body")
    if body is None:
        raise _invalid("DOCX document body is missing")
    paragraph_text: dict[int, str] = {}
    image_locators: dict[str, str] = {}
    paragraph_count = 0
    for child in body:
        if child.tag == f"{W}sectPr":
            continue
        if child.tag != f"{W}p":
            if child.tag == f"{W}tbl":
                continue
            raise _invalid("DOCX body contains an unsupported direct element")
        paragraph_count += 1
        text_fragments: list[str] = []
        image_index = 0
        for element in child.iter():
            if element.tag == f"{W}t":
                text_fragments.append(element.text or "")
            elif element.tag == f"{W}tab":
                text_fragments.append("\t")
            elif element.tag in {f"{W}br", f"{W}cr"}:
                text_fragments.append("\n")
            elif element.tag == f"{A}blip":
                linked = element.attrib.get(f"{R}link")
                embedded = element.attrib.get(f"{R}embed")
                if linked or not embedded:
                    raise _invalid("DOCX drawing must use an embedded image relationship")
                image_index += 1
                if embedded in image_locators:
                    raise _invalid("DOCX reuses an image relationship")
                if embedded not in relationships:
                    raise _invalid("DOCX drawing relationship is missing or is not an image")
                image_locators[embedded] = (
                    f"word/document.xml#paragraph={paragraph_count};"
                    f"image={image_index}"
                )
        text = "".join(text_fragments).strip()
        if text:
            paragraph_text[paragraph_count] = text

    revision_local_names = {
        "cellDel",
        "cellIns",
        "del",
        "ins",
        "moveFrom",
        "moveTo",
        "numberingChange",
        "pPrChange",
        "rPrChange",
        "sectPrChange",
        "tblPrChange",
        "tcPrChange",
        "trPrChange",
    }
    elements = list(document_root.iter())
    comment_local_names = {
        "commentRangeEnd",
        "commentRangeStart",
        "commentReference",
    }
    unsupported_local_names = {"altChunk", "control", "object", "oleObject"}
    local_name = lambda tag: tag.rsplit("}", 1)[-1]
    if any(local_name(element.tag) in unsupported_local_names for element in elements):
        raise _invalid("active or embedded DOCX objects are unsupported")
    if any(local_name(element.tag) == "vanish" for element in elements):
        raise _invalid("hidden DOCX text is unsupported")
    return {
        "body_paragraph_count": paragraph_count,
        "comments_present": (
            "word/comments.xml" in entries
            or any(local_name(element.tag) in comment_local_names for element in elements)
        ),
        "image_locators": image_locators,
        "paragraph_text": paragraph_text,
        "relationships": relationships,
        "referenced_image_count": len(image_locators),
        "table_count": sum(
            1 for element in elements if element.tag == f"{W}tbl"
        ),
        "tracked_changes_present": any(
            local_name(element.tag) in revision_local_names for element in elements
        ),
    }


def _preflight_docx_security(document_bytes: bytes) -> None:
    try:
        archive = zipfile.ZipFile(io.BytesIO(document_bytes))
    except (OSError, zipfile.BadZipFile) as error:
        raise _invalid("configured source is not a readable DOCX ZIP archive") from error
    with archive:
        entries = _validate_archive_entries(archive)
        provenance = _inspect_docx_provenance(archive, entries)
    if provenance["comments_present"]:
        raise _invalid("comments must be removed before DOCX serving")
    if provenance["tracked_changes_present"]:
        raise _invalid("tracked changes must be accepted before DOCX serving")
    if provenance["table_count"]:
        raise _invalid("table-based forecast layouts are unsupported")


def _load_assets(
    document_bytes: bytes,
    candidates: list[dict[str, Any]],
    document: dict[str, Any],
) -> dict[str, GachaAssetRecord]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(document_bytes))
    except (OSError, zipfile.BadZipFile) as error:
        raise _invalid("configured source is not a readable DOCX ZIP archive") from error
    assets: dict[str, GachaAssetRecord] = {}
    with archive:
        entries = _validate_archive_entries(archive)
        provenance = _inspect_docx_provenance(archive, entries)
        for field in DOCUMENT_FIELDS:
            if provenance[field] != document[field]:
                raise _invalid(
                    f"catalog.document.{field} differs from the source DOCX"
                )
        expected_relationship_ids = {
            candidate["image"]["relationship_id"] for candidate in candidates
        }
        if set(provenance["image_locators"]) != expected_relationship_ids:
            raise _invalid("catalog candidates differ from DOCX drawing relationships")
        for index, candidate in enumerate(candidates):
            image = candidate["image"]
            package_path = image["package_path"]
            relationship_id = image["relationship_id"]
            if (
                provenance["relationships"].get(relationship_id) != package_path
                or provenance["image_locators"].get(relationship_id)
                != candidate["image_locator"]
            ):
                raise _invalid(
                    f"catalog.candidates[{index}].image provenance differs from DOCX"
                )
            for locator, raw_line in zip(
                candidate["description_locators"],
                candidate["raw_description_lines"],
                strict=True,
            ):
                paragraph = _paragraph_number(locator, "candidate description locator")
                if provenance["paragraph_text"].get(paragraph) != raw_line:
                    raise _invalid(
                        f"catalog.candidates[{index}] description text differs from DOCX"
                    )
            forecast_paragraph = _paragraph_number(
                candidate["source_locator"], "candidate source locator"
            )
            if (
                provenance["paragraph_text"].get(forecast_paragraph)
                != candidate["raw_forecast_text"]
            ):
                raise _invalid(
                    f"catalog.candidates[{index}] forecast text differs from DOCX"
                )
            if package_path not in entries:
                raise _invalid(
                    f"catalog.candidates[{index}].image package part is missing"
                )
            try:
                payload = archive.read(package_path)
            except (KeyError, OSError, RuntimeError) as error:
                raise _invalid(
                    f"catalog.candidates[{index}].image cannot be read"
                ) from error
            if (
                len(payload) != image["byte_length"]
                or _sha256(payload) != image["sha256"]
                or not _has_valid_magic(payload, image["mime_type"])
            ):
                raise _invalid(
                    f"catalog.candidates[{index}].image bytes fail hash, length, or magic validation"
                )
            existing = assets.get(image["sha256"])
            if existing is not None and (
                existing.data != payload or existing.mime_type != image["mime_type"]
            ):
                raise _invalid("one asset SHA-256 has inconsistent representations")
            assets[image["sha256"]] = GachaAssetRecord(
                sha256=image["sha256"],
                mime_type=image["mime_type"],
                byte_length=image["byte_length"],
                package_path=package_path,
                data=payload,
            )
    return assets


def _validate_catalog(
    raw_catalog: object,
    *,
    document_bytes: bytes,
    configured_docx_path: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, GachaAssetRecord],
]:
    root = _expect_dict(raw_catalog, "catalog")
    _expect_exact_fields(root, ROOT_FIELDS, "catalog")
    if root["schema_version"] != CATALOG_SCHEMA_VERSION:
        raise _invalid("unsupported Gacha library schema_version")

    source = _expect_dict(root["source"], "catalog.source")
    _expect_exact_fields(source, SOURCE_FIELDS, "catalog.source")
    if source["authority"] != "COMMUNITY_FORECAST":
        raise _invalid("catalog.source.authority must remain COMMUNITY_FORECAST")
    if source["capture_method"] != "USER_SUPPLIED_DOCX":
        raise _invalid("catalog.source.capture_method must remain USER_SUPPLIED_DOCX")
    if source["embedded_image_policy"] != "PROVENANCE_ONLY_NOT_TW_DATE_EVIDENCE":
        raise _invalid("catalog.source embedded image policy is invalid")
    if source["source_id"] != SOURCE_ID or source["independence_group"] != SOURCE_ID:
        raise _invalid("DOCX must remain in the GACHA-COMM-002 independence group")
    if source["source_id_origin"] != "CALLER_DECLARED_NOT_DOCUMENT_CONTENT":
        raise _invalid("catalog.source.source_id_origin is invalid")
    document_sha256 = _expect_sha256(
        source["document_sha256"], "catalog.source.document_sha256"
    )
    document_byte_length = _expect_int(
        source["document_byte_length"],
        "catalog.source.document_byte_length",
        minimum=1,
    )
    if document_byte_length > MAX_ARCHIVE_BYTES:
        raise _invalid("source DOCX exceeds the supported size")
    if configured_docx_path.name != f"{document_sha256}.docx":
        raise _invalid("configured DOCX filename is not its lowercase content address")
    if len(document_bytes) != document_byte_length or _sha256(document_bytes) != document_sha256:
        raise _invalid("configured DOCX does not match the catalog source hash and length")

    document = _expect_dict(root["document"], "catalog.document")
    _expect_exact_fields(document, DOCUMENT_FIELDS, "catalog.document")
    body_paragraph_count = _expect_int(
        document["body_paragraph_count"],
        "catalog.document.body_paragraph_count",
        minimum=1,
    )
    referenced_image_count = _expect_int(
        document["referenced_image_count"],
        "catalog.document.referenced_image_count",
        minimum=1,
    )
    _expect_bool(document["comments_present"], False, "catalog.document.comments_present")
    _expect_bool(
        document["tracked_changes_present"],
        False,
        "catalog.document.tracked_changes_present",
    )
    if _expect_int(document["table_count"], "catalog.document.table_count") != 0:
        raise _invalid("catalog.document.table_count must remain zero")

    raw_candidates = _expect_list(root["candidates"], "catalog.candidates")
    if not raw_candidates:
        raise _invalid("catalog.candidates must not be empty")
    candidates: list[dict[str, Any]] = []
    candidate_ids: set[str] = set()
    relationship_ids: set[str] = set()
    package_paths: set[str] = set()
    previous_end_paragraph = 0
    for index, raw_candidate in enumerate(raw_candidates):
        candidate, paragraph_range = _validate_candidate(
            raw_candidate,
            index=index,
            document_sha256=document_sha256,
            source_id=source["source_id"],
            body_paragraph_count=body_paragraph_count,
        )
        if candidate["candidate_id"] in candidate_ids:
            raise _invalid("catalog.candidates contains duplicate candidate_id")
        candidate_ids.add(candidate["candidate_id"])
        relationship_id = candidate["image"]["relationship_id"]
        package_path = candidate["image"]["package_path"]
        if relationship_id in relationship_ids or package_path in package_paths:
            raise _invalid("catalog.candidates reuses an image relationship or package path")
        relationship_ids.add(relationship_id)
        package_paths.add(package_path)
        if paragraph_range[0] <= previous_end_paragraph:
            raise _invalid("catalog.candidates paragraph ranges overlap or are unordered")
        previous_end_paragraph = paragraph_range[1]
        candidates.append(candidate)
    if referenced_image_count != len(candidates):
        raise _invalid("catalog.document.referenced_image_count differs from candidates")

    summary = _expect_dict(root["summary"], "catalog.summary")
    _expect_exact_fields(summary, SUMMARY_FIELDS, "catalog.summary")
    pool_counts = dict(
        sorted(
            Counter(
                item["source_declared_pool_kind"] for item in candidates
            ).items()
        )
    )
    review_counts = dict(sorted(Counter(item["review_status"] for item in candidates).items()))
    warning_counts = dict(
        sorted(
            Counter(
                warning
                for item in candidates
                for warning in item["parser_warnings"]
            ).items()
        )
    )
    date_windows = {
        (item["forecast_start"], item["forecast_end"]) for item in candidates
    }
    expected_summary = {
        "candidate_count": len(candidates),
        "canonical_write_count": 0,
        "character_label_count": sum(
            len(item["raw_character_names"]) for item in candidates
        ),
        "coverage_end": max(item["forecast_end"] for item in candidates),
        "coverage_start": min(item["forecast_start"] for item in candidates),
        "pool_kind_counts": pool_counts,
        "review_status_counts": review_counts,
        "unique_date_window_count": len(date_windows),
        "warning_counts": warning_counts,
    }
    _validate_count_map(summary["pool_kind_counts"], "catalog.summary.pool_kind_counts")
    _validate_count_map(summary["review_status_counts"], "catalog.summary.review_status_counts")
    _validate_count_map(summary["warning_counts"], "catalog.summary.warning_counts")
    for field in (
        "candidate_count",
        "canonical_write_count",
        "character_label_count",
        "unique_date_window_count",
    ):
        _expect_int(summary[field], f"catalog.summary.{field}")
    _parse_iso_date(summary["coverage_start"], "catalog.summary.coverage_start")
    _parse_iso_date(summary["coverage_end"], "catalog.summary.coverage_end")
    if summary != expected_summary:
        raise _invalid("catalog.summary does not exactly match candidates")

    assets = _load_assets(document_bytes, candidates, document)
    return source, document, candidates, assets


class GachaLibraryRuntime:
    """Lazy immutable view of one content-addressed private Gacha DOCX."""

    def __init__(self, catalog_path: Path | None, docx_path: Path | None) -> None:
        self._catalog_path = catalog_path
        self._docx_path = docx_path
        self._snapshot: GachaLibrarySnapshot | None = None
        self._drifted = False
        self._lock = threading.RLock()

    @classmethod
    def from_settings(cls, settings: Settings) -> GachaLibraryRuntime:
        return cls(
            settings.gacha_library_catalog_path,
            settings.gacha_library_docx_path,
        )

    def snapshot(self) -> GachaLibrarySnapshot:
        with self._lock:
            if self._catalog_path is None or self._docx_path is None:
                raise GachaLibraryUnavailable(
                    "GACHA_LIBRARY_NOT_CONFIGURED",
                    "The local Gacha forecast library is not configured.",
                )
            if self._drifted:
                raise GachaLibraryUnavailable(
                    "GACHA_LIBRARY_DRIFT",
                    "The local Gacha forecast library changed after loading.",
                )
            if self._snapshot is None:
                self._snapshot = self._load()
            else:
                try:
                    catalog_fingerprint, docx_fingerprint = self._fingerprints()
                except OSError as error:
                    self._drifted = True
                    raise GachaLibraryUnavailable(
                        "GACHA_LIBRARY_DRIFT",
                        "The local Gacha forecast library changed after loading.",
                        details={"reason": type(error).__name__},
                    ) from error
                if (
                    catalog_fingerprint != self._snapshot.catalog_fingerprint
                    or docx_fingerprint != self._snapshot.docx_fingerprint
                ):
                    self._drifted = True
                    raise GachaLibraryUnavailable(
                        "GACHA_LIBRARY_DRIFT",
                        "The local Gacha forecast library changed after loading.",
                    )
            return self._snapshot

    def read_asset(self, sha256: str) -> GachaAssetRecord:
        snapshot = self.snapshot()
        if SHA256_PATTERN.fullmatch(sha256) is None:
            raise GachaLibraryNotFound("gacha_asset", sha256)
        asset = snapshot.assets_by_sha256.get(sha256)
        if asset is None:
            raise GachaLibraryNotFound("gacha_asset", sha256)
        return asset

    def _read_inputs(self) -> tuple[bytes, bytes]:
        assert self._catalog_path is not None
        assert self._docx_path is not None
        if (
            self._catalog_path.is_symlink()
            or self._docx_path.is_symlink()
            or not self._catalog_path.is_file()
            or not self._docx_path.is_file()
        ):
            raise GachaLibraryUnavailable(
                "GACHA_LIBRARY_UNAVAILABLE",
                "The configured Gacha catalog or DOCX is missing or unsafe.",
            )
        return self._catalog_path.read_bytes(), self._docx_path.read_bytes()

    def _fingerprints(self) -> tuple[tuple[int, str], tuple[int, str]]:
        catalog_bytes, docx_bytes = self._read_inputs()
        return (
            (len(catalog_bytes), _sha256(catalog_bytes)),
            (len(docx_bytes), _sha256(docx_bytes)),
        )

    def _load(self) -> GachaLibrarySnapshot:
        assert self._docx_path is not None
        try:
            catalog_bytes, docx_bytes = self._read_inputs()
        except GachaLibraryUnavailable:
            raise
        except OSError as error:
            raise GachaLibraryUnavailable(
                "GACHA_LIBRARY_UNAVAILABLE",
                "The configured Gacha catalog or DOCX cannot be read.",
                details={"reason": type(error).__name__},
            ) from error
        try:
            raw_catalog = json.loads(
                catalog_bytes.decode("utf-8"),
                object_pairs_hook=_strict_json_object,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, _StrictJsonError) as error:
            raise _invalid("catalog is not strict UTF-8 JSON") from error

        _preflight_docx_security(docx_bytes)
        try:
            replay = extract_gacha_forecast_docx(
                self._docx_path,
                source_id=SOURCE_ID,
            )
        except GachaDocxError as error:
            raise _invalid(f"source DOCX replay was rejected: {error}") from error
        if replay_json_bytes(replay) != catalog_bytes:
            raise _invalid(
                "catalog bytes do not exactly match deterministic source DOCX replay"
            )

        source, document, candidates, assets = _validate_catalog(
            raw_catalog,
            document_bytes=docx_bytes,
            configured_docx_path=self._docx_path,
        )
        before = (
            (len(catalog_bytes), _sha256(catalog_bytes)),
            (len(docx_bytes), _sha256(docx_bytes)),
        )
        try:
            after = self._fingerprints()
        except OSError as error:
            raise GachaLibraryUnavailable(
                "GACHA_LIBRARY_UNAVAILABLE",
                "The local Gacha forecast library changed while loading.",
                details={"reason": type(error).__name__},
            ) from error
        if before != after:
            raise GachaLibraryUnavailable(
                "GACHA_LIBRARY_UNAVAILABLE",
                "The local Gacha forecast library changed while loading.",
            )
        return GachaLibrarySnapshot(
            dataset_sha256=_sha256(catalog_bytes),
            schema_version=CATALOG_SCHEMA_VERSION,
            source=MappingProxyType(dict(source)),
            document=MappingProxyType(dict(document)),
            candidates=tuple(MappingProxyType(dict(item)) for item in candidates),
            assets_by_sha256=MappingProxyType(assets),
            catalog_fingerprint=before[0],
            docx_fingerprint=before[1],
        )


def gacha_library_meta(snapshot: GachaLibrarySnapshot) -> dict[str, Any]:
    source = snapshot.source
    return {
        "api_version": "v1",
        "authority": source["authority"],
        "canonical_write_count": 0,
        "dataset_sha256": snapshot.dataset_sha256,
        "independence_group": source["independence_group"],
        "schema_version": snapshot.schema_version,
        "source_document": {
            "byte_length": source["document_byte_length"],
            "content_addressed_filename": f'{source["document_sha256"]}.docx',
            "sha256": source["document_sha256"],
        },
        "source_id": source["source_id"],
        "source_status": "USER_SUPPLIED",
    }


def forecast_view(candidate: Mapping[str, Any]) -> dict[str, Any]:
    image = candidate["image"]
    return {
        "candidate_id": candidate["candidate_id"],
        "date_boundary_semantics": candidate["date_boundary_semantics"],
        "forecast_end": candidate["forecast_end"],
        "forecast_start": candidate["forecast_start"],
        "identity_status": candidate["identity_status"],
        "image": {
            "asset_url": "/api/v1/gacha-library/assets/" + image["sha256"],
            "byte_length": image["byte_length"],
            "mime_type": image["mime_type"],
            "sha256": image["sha256"],
        },
        "parser_warnings": list(candidate["parser_warnings"]),
        "precision": candidate["precision"],
        "promotion_eligible": candidate["promotion_eligible"],
        "proposed_event_id": candidate["proposed_event_id"],
        "provenance": {
            "description_locators": list(candidate["description_locators"]),
            "image_locator": candidate["image_locator"],
            "package_path": image["package_path"],
            "relationship_id": image["relationship_id"],
            "source_locator": candidate["source_locator"],
        },
        "raw_character_names": list(candidate["raw_character_names"]),
        "raw_description_lines": list(candidate["raw_description_lines"]),
        "raw_forecast_text": candidate["raw_forecast_text"],
        "raw_sequence_label": candidate["raw_sequence_label"],
        "review_order": candidate["review_order"],
        "review_reason": candidate["review_reason"],
        "review_status": candidate["review_status"],
        "source_declared_pool_kind": candidate["source_declared_pool_kind"],
    }


def forecast_list_view(snapshot: GachaLibrarySnapshot) -> dict[str, Any]:
    items = [forecast_view(candidate) for candidate in snapshot.candidates]
    return {"items": items, "total": len(items)}
