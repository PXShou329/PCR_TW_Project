from __future__ import annotations

import hashlib
import io
import json
import mimetypes
import posixpath
import re
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from xml.etree import ElementTree


CANDIDATE_SCHEMA_VERSION = "gacha-community-docx-candidates/v1"
COMMUNITY_FORECAST = "COMMUNITY_FORECAST"
USER_SUPPLIED_DOCX = "USER_SUPPLIED_DOCX"
PENDING = "PENDING"

_MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
_MAX_ENTRY_COUNT = 1_024
_MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
_MAX_SINGLE_ENTRY_BYTES = 25 * 1024 * 1024
_MAX_COMPRESSION_RATIO = 250

_SOURCE_ID = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,119}$")
_FORECAST = re.compile(
    r"^台服預測\s*"
    r"(?P<start_year>\d{4})/(?P<start_month>\d{1,2})/(?P<start_day>\d{1,2})"
    r"\s*[～~〜]\s*"
    r"(?:(?P<end_year>\d{4})/)?(?P<end_month>\d{1,2})/(?P<end_day>\d{1,2})$"
)
_SEQUENCE_LABEL = re.compile(r"第\s*(\d+)\s*次")
_QUOTED_NAME = re.compile(r"「([^」]+)」")
_UNQUOTED_VARIANT_NAME = re.compile(
    r"[^\s「」、,，（）()]+[（(][^「」（）()]+[）)]"
)

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

_W = f"{{{_W_NS}}}"
_A = f"{{{_A_NS}}}"
_R = f"{{{_R_NS}}}"


class GachaDocxError(ValueError):
    """Raised when a forecast DOCX cannot be parsed without guessing."""


def canonical_json_bytes(value: Any) -> bytes:
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


def extract_gacha_forecast_docx(
    path: str | Path,
    *,
    source_id: str,
) -> dict[str, Any]:
    """Parse one reviewed-format DOCX into a deterministic candidate bundle.

    The result is deliberately non-canonical.  Names and predicted dates remain
    community observations until a separate human review links them to exact JP
    events.  Embedded images are hashed for provenance only; text inside an image
    is never OCRed or treated as Taiwan schedule evidence.
    """

    source = Path(path)
    if source.suffix.lower() != ".docx" or not source.is_file():
        raise GachaDocxError(f"input must be an existing .docx file: {source}")
    if source.is_symlink():
        raise GachaDocxError("input DOCX must not be a symlink")
    if not _SOURCE_ID.fullmatch(source_id):
        raise GachaDocxError("source_id must be a stable uppercase registry id")

    try:
        raw_bytes = source.read_bytes()
    except OSError as exc:
        raise GachaDocxError(f"cannot read DOCX: {source}") from exc
    if not raw_bytes or len(raw_bytes) > _MAX_ARCHIVE_BYTES:
        raise GachaDocxError("DOCX byte length is outside the supported range")

    document_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw_bytes))
    except (OSError, zipfile.BadZipFile) as exc:
        raise GachaDocxError("input is not a readable DOCX ZIP archive") from exc

    with archive:
        entries = _validate_archive(archive)
        required = {
            "[Content_Types].xml",
            "word/document.xml",
            "word/_rels/document.xml.rels",
        }
        missing = sorted(required - entries)
        if missing:
            raise GachaDocxError(f"DOCX is missing required parts: {missing}")
        if "word/vbaProject.bin" in entries:
            raise GachaDocxError("macro-enabled DOCX content is not supported")

        document_root = _read_xml(archive, "word/document.xml")
        relationships_root = _read_xml(
            archive, "word/_rels/document.xml.rels"
        )
        content_types_root = _read_xml(archive, "[Content_Types].xml")

        _reject_unsupported_document_features(document_root, entries)
        relationships = _load_relationships(relationships_root)
        content_types = _load_content_types(content_types_root)
        parts, paragraph_count = _document_parts(document_root)

        candidate_inputs: list[dict[str, Any]] = []
        description_lines: list[str] = []
        description_locators: list[str] = []
        pending_forecast: dict[str, Any] | None = None
        used_relationship_ids: set[str] = set()

        for part in parts:
            if part["kind"] == "text":
                text = part["text"]
                forecast = _parse_forecast(text)
                if forecast is None:
                    if pending_forecast is not None:
                        raise GachaDocxError(
                            "unexpected text between a forecast date and its image: "
                            f"{part['locator']}"
                        )
                    description_lines.append(text)
                    description_locators.append(part["locator"])
                    continue

                if pending_forecast is not None:
                    raise GachaDocxError("forecast block is missing its image")
                if not description_lines:
                    raise GachaDocxError(
                        f"forecast has no preceding pool description: {part['locator']}"
                    )
                pending_forecast = {
                    **forecast,
                    "raw_forecast_text": text,
                    "forecast_locator": part["locator"],
                }
                continue

            relationship_id = part["relationship_id"]
            if pending_forecast is None:
                raise GachaDocxError(
                    f"image is not paired with a forecast block: {part['locator']}"
                )
            if relationship_id in used_relationship_ids:
                raise GachaDocxError(
                    f"image relationship is reused across forecast blocks: {relationship_id}"
                )
            used_relationship_ids.add(relationship_id)
            image = _read_image(
                archive,
                entries=entries,
                relationships=relationships,
                content_types=content_types,
                relationship_id=relationship_id,
            )
            candidate_inputs.append(
                {
                    "description_lines": list(description_lines),
                    "description_locators": list(description_locators),
                    "image_locator": part["locator"],
                    "image": image,
                    **pending_forecast,
                }
            )
            description_lines.clear()
            description_locators.clear()
            pending_forecast = None

        if pending_forecast is not None:
            raise GachaDocxError("final forecast block is missing its image")
        if description_lines:
            raise GachaDocxError("unpaired trailing pool description text")
        if not candidate_inputs:
            raise GachaDocxError("DOCX contains no supported forecast blocks")

    candidates = [
        _build_candidate(
            item,
            document_sha256=document_sha256,
            review_order=index,
            source_id=source_id,
        )
        for index, item in enumerate(candidate_inputs, start=1)
    ]
    pool_counts = Counter(item["source_declared_pool_kind"] for item in candidates)
    review_counts = Counter(item["review_status"] for item in candidates)
    warning_counts = Counter(
        warning
        for item in candidates
        for warning in item["parser_warnings"]
    )
    unique_date_windows = {
        (item["forecast_start"], item["forecast_end"]) for item in candidates
    }
    coverage_start = min(item["forecast_start"] for item in candidates)
    coverage_end = max(item["forecast_end"] for item in candidates)

    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "source": {
            "authority": COMMUNITY_FORECAST,
            "capture_method": USER_SUPPLIED_DOCX,
            "document_byte_length": len(raw_bytes),
            "document_sha256": document_sha256,
            "embedded_image_policy": "PROVENANCE_ONLY_NOT_TW_DATE_EVIDENCE",
            "independence_group": source_id,
            "source_id": source_id,
            "source_id_origin": "CALLER_DECLARED_NOT_DOCUMENT_CONTENT",
        },
        "document": {
            "body_paragraph_count": paragraph_count,
            "comments_present": False,
            "referenced_image_count": len(used_relationship_ids),
            "table_count": 0,
            "tracked_changes_present": False,
        },
        "candidates": candidates,
        "summary": {
            "candidate_count": len(candidates),
            "canonical_write_count": 0,
            "character_label_count": sum(
                len(item["raw_character_names"]) for item in candidates
            ),
            "coverage_end": coverage_end,
            "coverage_start": coverage_start,
            "pool_kind_counts": dict(sorted(pool_counts.items())),
            "review_status_counts": dict(sorted(review_counts.items())),
            "unique_date_window_count": len(unique_date_windows),
            "warning_counts": dict(sorted(warning_counts.items())),
        },
    }


def _validate_archive(archive: zipfile.ZipFile) -> set[str]:
    infos = archive.infolist()
    if not infos or len(infos) > _MAX_ENTRY_COUNT:
        raise GachaDocxError("DOCX ZIP entry count is outside the supported range")
    names: set[str] = set()
    total_uncompressed = 0
    for info in infos:
        name = info.filename
        normalized = name.replace("\\", "/")
        path = PurePosixPath(normalized)
        if (
            normalized != name
            or normalized.startswith("/")
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise GachaDocxError(f"unsafe DOCX ZIP entry path: {name!r}")
        if normalized in names:
            raise GachaDocxError(f"duplicate DOCX ZIP entry: {normalized}")
        if info.flag_bits & 0x1:
            raise GachaDocxError("encrypted DOCX ZIP entries are not supported")
        if normalized.startswith(("word/activeX/", "word/embeddings/")):
            raise GachaDocxError(
                f"active or embedded DOCX content is not supported: {normalized}"
            )
        if info.file_size > _MAX_SINGLE_ENTRY_BYTES:
            raise GachaDocxError(f"DOCX ZIP entry is too large: {normalized}")
        if (
            info.file_size > 1_048_576
            and info.compress_size > 0
            and info.file_size / info.compress_size > _MAX_COMPRESSION_RATIO
        ):
            raise GachaDocxError(
                f"DOCX ZIP entry compression ratio is unsafe: {normalized}"
            )
        names.add(normalized)
        total_uncompressed += info.file_size
    if total_uncompressed > _MAX_UNCOMPRESSED_BYTES:
        raise GachaDocxError("DOCX uncompressed byte length is too large")
    return names


def _read_xml(archive: zipfile.ZipFile, name: str) -> ElementTree.Element:
    try:
        payload = archive.read(name)
    except (KeyError, OSError, RuntimeError) as exc:
        raise GachaDocxError(f"cannot read DOCX XML part: {name}") from exc
    try:
        decoded = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise GachaDocxError(
            f"DOCX XML parts must use UTF-8 encoding: {name}"
        ) from exc
    upper = decoded.upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        raise GachaDocxError(f"DTD/entity declarations are forbidden in DOCX XML: {name}")
    declaration = re.match(r"\s*<\?xml\s+[^>]*encoding=['\"]([^'\"]+)['\"]", decoded)
    if declaration is not None and declaration.group(1).lower().replace("_", "-") not in {
        "utf-8",
        "us-ascii",
    }:
        raise GachaDocxError(f"DOCX XML declares a non-UTF-8 encoding: {name}")
    try:
        return ElementTree.fromstring(decoded)
    except ElementTree.ParseError as exc:
        raise GachaDocxError(f"invalid DOCX XML part: {name}") from exc


def _reject_unsupported_document_features(
    document_root: ElementTree.Element,
    entries: set[str],
) -> None:
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
    if any(_local_name(element.tag) in revision_local_names for element in elements):
        raise GachaDocxError("tracked changes must be accepted before ingestion")
    comment_local_names = {"commentRangeEnd", "commentRangeStart", "commentReference"}
    if "word/comments.xml" in entries or any(
        _local_name(element.tag) in comment_local_names for element in elements
    ):
        raise GachaDocxError("comments must be removed before ingestion")
    if any(element.tag == f"{_W}tbl" for element in elements):
        raise GachaDocxError("table-based forecast layouts are not supported")
    unsupported_local_names = {"altChunk", "control", "object", "oleObject"}
    if any(_local_name(element.tag) in unsupported_local_names for element in elements):
        raise GachaDocxError("active or embedded DOCX objects are not supported")
    if any(_local_name(element.tag) == "vanish" for element in elements):
        raise GachaDocxError("hidden DOCX text is not supported")


def _load_relationships(
    root: ElementTree.Element,
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for relationship in root.findall(f"{{{_REL_NS}}}Relationship"):
        relationship_id = relationship.attrib.get("Id", "")
        target = relationship.attrib.get("Target", "")
        relationship_type = relationship.attrib.get("Type", "")
        target_mode = relationship.attrib.get("TargetMode", "Internal")
        if not relationship_id or relationship_id in result:
            raise GachaDocxError("DOCX relationship ids must be unique and nonempty")
        if target_mode.lower() == "external":
            raise GachaDocxError("external DOCX relationships are forbidden")
        result[relationship_id] = {
            "target": target,
            "target_mode": target_mode,
            "type": relationship_type,
        }
    return result


def _load_content_types(root: ElementTree.Element) -> dict[str, str]:
    defaults: dict[str, str] = {}
    overrides: dict[str, str] = {}
    for item in root:
        if item.tag == f"{{{_CT_NS}}}Default":
            extension = item.attrib.get("Extension", "").lower()
            content_type = item.attrib.get("ContentType", "")
            if extension and content_type:
                defaults[extension] = content_type
        elif item.tag == f"{{{_CT_NS}}}Override":
            part_name = item.attrib.get("PartName", "").lstrip("/")
            content_type = item.attrib.get("ContentType", "")
            if part_name and content_type:
                overrides[part_name] = content_type
    result = {f"*.{extension}": value for extension, value in defaults.items()}
    result.update(overrides)
    return result


def _document_parts(
    document_root: ElementTree.Element,
) -> tuple[list[dict[str, str]], int]:
    body = document_root.find(f"{_W}body")
    if body is None:
        raise GachaDocxError("DOCX document body is missing")
    parts: list[dict[str, str]] = []
    paragraph_count = 0
    for child in body:
        if child.tag != f"{_W}p":
            if child.tag == f"{_W}sectPr":
                continue
            raise GachaDocxError(f"unsupported DOCX body element: {child.tag}")
        paragraph_count += 1
        current_text: list[str] = []

        def flush_text() -> None:
            text = "".join(current_text).strip()
            current_text.clear()
            if text:
                parts.append(
                    {
                        "kind": "text",
                        "locator": f"word/document.xml#paragraph={paragraph_count}",
                        "text": text,
                    }
                )

        image_index = 0
        for element in child.iter():
            if element.tag == f"{_W}t":
                current_text.append(element.text or "")
            elif element.tag == f"{_W}tab":
                current_text.append("\t")
            elif element.tag in {f"{_W}br", f"{_W}cr"}:
                current_text.append("\n")
            elif element.tag == f"{_A}blip":
                flush_text()
                image_index += 1
                linked = element.attrib.get(f"{_R}link")
                embedded = element.attrib.get(f"{_R}embed")
                if linked:
                    raise GachaDocxError("externally linked DOCX images are forbidden")
                if not embedded:
                    raise GachaDocxError("DOCX image is missing an embedded relationship")
                parts.append(
                    {
                        "kind": "image",
                        "locator": (
                            f"word/document.xml#paragraph={paragraph_count};"
                            f"image={image_index}"
                        ),
                        "relationship_id": embedded,
                    }
                )
        flush_text()
    return parts, paragraph_count


def _parse_forecast(text: str) -> dict[str, str] | None:
    match = _FORECAST.fullmatch(text.strip())
    if match is None:
        if "台服預測" in text:
            raise GachaDocxError(f"unsupported Taiwan forecast date format: {text!r}")
        return None
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
    except ValueError as exc:
        raise GachaDocxError(f"forecast contains an invalid calendar date: {text!r}") from exc
    if end < start:
        raise GachaDocxError(
            "forecast end precedes start; cross-year ranges must state the end year"
        )
    return {
        "forecast_end": end.isoformat(),
        "forecast_start": start.isoformat(),
        "precision": "DAY",
    }


def _read_image(
    archive: zipfile.ZipFile,
    *,
    entries: set[str],
    relationships: dict[str, dict[str, str]],
    content_types: dict[str, str],
    relationship_id: str,
) -> dict[str, Any]:
    relationship = relationships.get(relationship_id)
    if relationship is None:
        raise GachaDocxError(f"image relationship does not exist: {relationship_id}")
    if not relationship["type"].endswith("/image"):
        raise GachaDocxError(f"relationship is not an image: {relationship_id}")
    if relationship["target_mode"].lower() == "external":
        raise GachaDocxError("externally linked DOCX images are forbidden")
    target = relationship["target"]
    if not target or "\\" in target or target.startswith("/"):
        raise GachaDocxError(f"unsafe image relationship target: {target!r}")
    package_path = posixpath.normpath(posixpath.join("word", target))
    if not package_path.startswith("word/media/") or ".." in PurePosixPath(
        package_path
    ).parts:
        raise GachaDocxError(f"image target escapes word/media: {target!r}")
    if package_path not in entries:
        raise GachaDocxError(f"embedded image part is missing: {package_path}")
    try:
        payload = archive.read(package_path)
    except (KeyError, OSError, RuntimeError) as exc:
        raise GachaDocxError(f"cannot read embedded image: {package_path}") from exc
    if not payload:
        raise GachaDocxError(f"embedded image is empty: {package_path}")
    extension = PurePosixPath(package_path).suffix.lower().lstrip(".")
    mime_type = content_types.get(package_path) or content_types.get(f"*.{extension}")
    if mime_type is None:
        mime_type = mimetypes.guess_type(package_path)[0]
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise GachaDocxError(
            f"unsupported embedded image MIME type for {package_path}: {mime_type!r}"
        )
    _validate_image_signature(payload, mime_type=mime_type, package_path=package_path)
    return {
        "byte_length": len(payload),
        "filename": PurePosixPath(package_path).name,
        "mime_type": mime_type,
        "package_path": package_path,
        "relationship_id": relationship_id,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _build_candidate(
    item: dict[str, Any],
    *,
    document_sha256: str,
    review_order: int,
    source_id: str,
) -> dict[str, Any]:
    description_lines = item["description_lines"]
    joined = "\n".join(description_lines)
    marker_matches = {
        "LIMITED_PICKUP": "限定UP角色" in joined,
        "PERMANENT_PICKUP": "常駐角色" in joined,
        "RERUN": "復刻池" in joined,
    }
    matched_pool_kinds = sorted(
        pool_kind for pool_kind, present in marker_matches.items() if present
    )
    if not matched_pool_kinds:
        raise GachaDocxError(
            f"pool kind is not explicit for forecast block {review_order}"
        )
    if len(matched_pool_kinds) != 1:
        raise GachaDocxError(
            "pool kind markers are ambiguous for forecast block "
            f"{review_order}: {matched_pool_kinds}"
        )
    pool_kind = matched_pool_kinds[0]

    raw_character_names: list[str] = []
    warnings: list[str] = []
    for line in description_lines:
        tokens, token_style = _parse_character_line(line)
        raw_character_names.extend(tokens)
        if token_style == "UNQUOTED":
            warnings.append("UNQUOTED_CHARACTER_SEQUENCE")
    if not raw_character_names:
        raise GachaDocxError(
            f"forecast block {review_order} contains no parseable character labels"
        )

    sequence_match = _SEQUENCE_LABEL.search(joined)
    sequence_number = int(sequence_match.group(1)) if sequence_match else None
    identity_payload = {
        "description_lines": description_lines,
        "document_sha256": document_sha256,
        "forecast_end": item["forecast_end"],
        "forecast_start": item["forecast_start"],
        "image_sha256": item["image"]["sha256"],
        "source_id": source_id,
        "source_locator": item["forecast_locator"],
    }
    candidate_digest = hashlib.sha256(
        canonical_json_bytes(identity_payload)
    ).hexdigest()
    return {
        "candidate_id": f"GACHA-DOCX-{candidate_digest[:24]}",
        "description_locators": item["description_locators"],
        "date_boundary_semantics": "SOURCE_UNSPECIFIED",
        "forecast_end": item["forecast_end"],
        "forecast_start": item["forecast_start"],
        "image": item["image"],
        "image_locator": item["image_locator"],
        "identity_status": "UNVERIFIED_COMMUNITY_NAME",
        "parser_warnings": sorted(set(warnings)),
        "source_declared_pool_kind": pool_kind,
        "precision": item["precision"],
        "proposed_event_id": None,
        "promotion_eligible": False,
        "raw_character_names": raw_character_names,
        "raw_description_lines": description_lines,
        "raw_forecast_text": item["raw_forecast_text"],
        "raw_sequence_label": (
            f"第{sequence_number}次" if sequence_number is not None else None
        ),
        "review_order": review_order,
        "review_reason": (
            "UNDELIMITED_CHARACTER_TEXT_REQUIRES_REVIEW"
            if warnings
            else "EXACT_EVENT_LINK_NOT_REVIEWED"
        ),
        "review_status": PENDING,
        "source_locator": item["forecast_locator"],
    }


def _parse_character_line(line: str) -> tuple[list[str], str | None]:
    text = line.strip()
    text = _SEQUENCE_LABEL.sub("", text, count=1).strip()
    for prefix in ("限定UP角色", "常駐角色"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    if text.endswith("復刻池"):
        text = text[: -len("復刻池")].strip()
    if not text:
        raise GachaDocxError(f"pool description line has no character text: {line!r}")

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
                raise GachaDocxError(
                    f"unbalanced character quote in pool description: {line!r}"
                )
            token = text[position + 1 : closing].strip()
            if not token or "「" in token:
                raise GachaDocxError(
                    f"invalid quoted character label in pool description: {line!r}"
                )
            styles.add("QUOTED")
            position = closing + 1
        else:
            match = _UNQUOTED_VARIANT_NAME.match(text, position)
            if match is None:
                raise GachaDocxError(
                    f"unparsed character text in pool description: {line!r}"
                )
            token = match.group(0).strip()
            styles.add("UNQUOTED")
            position = match.end()
        _validate_character_token(token, line=line)
        tokens.append(token)

    if len(styles) != 1:
        raise GachaDocxError(
            f"mixed quoted and unquoted character text is ambiguous: {line!r}"
        )
    return tokens, next(iter(styles))


def _validate_character_token(token: str, *, line: str) -> None:
    if (
        token.count("(") != token.count(")")
        or token.count("（") != token.count("）")
        or "「" in token
        or "」" in token
    ):
        raise GachaDocxError(
            f"unbalanced character punctuation in pool description: {line!r}"
        )


def _validate_image_signature(
    payload: bytes,
    *,
    mime_type: str,
    package_path: str,
) -> None:
    valid = False
    if mime_type == "image/jpeg":
        valid = len(payload) >= 5 and payload.startswith(b"\xff\xd8\xff") and payload.endswith(b"\xff\xd9")
    elif mime_type == "image/png":
        valid = payload.startswith(b"\x89PNG\r\n\x1a\n")
    elif mime_type == "image/webp":
        valid = (
            len(payload) >= 12
            and payload.startswith(b"RIFF")
            and payload[8:12] == b"WEBP"
        )
    if not valid:
        raise GachaDocxError(
            f"embedded image bytes do not match {mime_type}: {package_path}"
        )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
