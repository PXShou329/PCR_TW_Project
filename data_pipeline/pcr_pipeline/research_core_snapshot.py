from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import shutil
import stat
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class SnapshotContract:
    """Immutable structural pins for one research-core manifest generation."""

    file_count: int
    csv_file_count: int
    csv_row_count: int
    evidence_to_claim_count: int
    claim_to_evidence_count: int


# RP-A4 是 Water read-mirror 的輸入契約；歷史 RP-A2／RP-A3 pins 與
# manifests 保留供 version-aware rollback 測試，不覆寫 immutable checkpoints。
EXPECTED_MANIFEST_SHA256 = "3daf2ab7c212b4f11c58883980d0ada3862400923c81a9bdedcc0500e59b1a9e"
EXPECTED_FILE_COUNT = 48
EXPECTED_CSV_FILE_COUNT = 13
EXPECTED_CSV_ROW_COUNT = 325
EXPECTED_EVIDENCE_TO_CLAIM_COUNT = 102
EXPECTED_CLAIM_TO_EVIDENCE_COUNT = 268
TREE_SERIALIZATION_VERSION = 1

RP_A3_MANIFEST_SHA256 = "ab62e07483dfea07c992b950b9c05c74fa0e3767fa0b3bce64b20193a1860333"
RP_A2_MANIFEST_SHA256 = "3a242b521d830af12ce8559d88b733068fb1b6cb503219395d2986b89e5dc352"
CURRENT_SNAPSHOT_CONTRACT = SnapshotContract(
    file_count=EXPECTED_FILE_COUNT,
    csv_file_count=EXPECTED_CSV_FILE_COUNT,
    csv_row_count=EXPECTED_CSV_ROW_COUNT,
    evidence_to_claim_count=EXPECTED_EVIDENCE_TO_CLAIM_COUNT,
    claim_to_evidence_count=EXPECTED_CLAIM_TO_EVIDENCE_COUNT,
)
RP_A3_SNAPSHOT_CONTRACT = SnapshotContract(
    file_count=48,
    csv_file_count=13,
    csv_row_count=239,
    evidence_to_claim_count=81,
    claim_to_evidence_count=184,
)
RP_A2_SNAPSHOT_CONTRACT = SnapshotContract(
    file_count=48,
    csv_file_count=13,
    csv_row_count=215,
    evidence_to_claim_count=75,
    claim_to_evidence_count=162,
)
PINNED_SNAPSHOT_CONTRACTS: Mapping[str, SnapshotContract] = {
    EXPECTED_MANIFEST_SHA256: CURRENT_SNAPSHOT_CONTRACT,
    RP_A3_MANIFEST_SHA256: RP_A3_SNAPSHOT_CONTRACT,
    RP_A2_MANIFEST_SHA256: RP_A2_SNAPSHOT_CONTRACT,
}

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESEARCH_CORE = REPOSITORY_ROOT / "research_core" / "pcr_tw_project"
DEFAULT_MANIFEST = REPOSITORY_ROOT / "scripts" / "research_core_rp_a4_manifest.sha256"

CSV_NATURAL_KEYS: Mapping[str, str] = {
    "17_TEST_EXECUTION_LOG.csv": "run_id",
    "18_TW_CHARACTER_AVAILABILITY.csv": "unit_key",
    "24_PVE_GUIDE_REGISTRY.csv": "guide_id",
    "25_PVE_TEAM_REGISTRY.csv": "team_id",
    "26_PVE_OPERATION_TIMELINES.csv": "source_axis_id",
    "27_PVE_TIMELINE_STEPS.csv": "timeline_step_id",
    "39_ARENA_COUNTER_REGISTRY.csv": "counter_id",
    "41_GACHA_TIMELINE.csv": "event_id",
    "45_GACHA_COMMUNITY_SOURCE_INDEX.csv": "source_id",
    "46_ARENA_SOURCE_REGISTRY.csv": "source_id",
    "47_PRINCESS_ARENA_CASE_REGISTRY.csv": "case_id",
    "92_EVIDENCE_LEDGER.csv": "evidence_id",
    "93_CLAIM_REGISTER.csv": "claim_id",
}

VALIDATOR_GENERATED_PATHS = frozenset(
    {
        "13_ACCEPTANCE_RESULTS.md",
        "15_DATA_QUALITY_REPORT.md",
        "16_STATIC_VALIDATION_REPORT.md",
        "tools/stats.json",
    }
)

# Validator mode reports are explicitly non-canonical diagnostics (README ADR
# 35).  They may exist after the required validation workflow, but must never
# enter a revision manifest or the immutable CoreFile mirror.
VALIDATOR_RUNTIME_PATHS = frozenset(
    {
        "tools/reports/pre_suite.json",
        "tools/reports/operational.json",
        "tools/reports/artifact_ready.json",
    }
)

FILE_ROLE_STRUCTURED_DATA = "STRUCTURED_DATA"
FILE_ROLE_VALIDATOR_GENERATED = "VALIDATOR_GENERATED"
FILE_ROLE_VALIDATOR_TOOL = "VALIDATOR_TOOL"
FILE_ROLE_VERSIONED_STATIC_ASSET = "VERSIONED_STATIC_ASSET"

ENCODING_UTF8 = "UTF-8"
ENCODING_UTF8_BOM = "UTF-8-BOM"
ENCODING_BINARY = "BINARY"

NEWLINE_LF = "LF"
NEWLINE_CRLF = "CRLF"
NEWLINE_CR = "CR"
NEWLINE_MIXED = "MIXED"
NEWLINE_NONE = "NONE"
NEWLINE_NOT_APPLICABLE = "NOT_APPLICABLE"


class SnapshotValidationError(ValueError):
    """研究核心不符合 manifest、路徑、CSV 或 FK 契約。"""


class SnapshotDriftError(RuntimeError):
    """已物化 revision 與預期 snapshot 不一致。"""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = reason
        self.detail = detail or reason
        super().__init__(self.detail)


class ExportSafetyError(ValueError):
    """export 目的地不符合外部、全新且可原子建立的安全邊界。"""


@dataclass(frozen=True)
class ManifestEntry:
    relative_path: str
    sha256: str


@dataclass(frozen=True)
class CsvRowSnapshot:
    ordinal: int
    natural_key: str
    values: tuple[str, ...]
    row_sha256: str

    def as_mapping(self, header: Sequence[str]) -> dict[str, str]:
        return dict(zip(header, self.values, strict=True))


@dataclass(frozen=True)
class CsvFileSnapshot:
    relative_path: str
    natural_key_field: str
    header: tuple[str, ...]
    rows: tuple[CsvRowSnapshot, ...]
    semantic_sha256: str

    def row_by_key(self, natural_key: str) -> CsvRowSnapshot:
        for row in self.rows:
            if row.natural_key == natural_key:
                return row
        raise KeyError(natural_key)


@dataclass(frozen=True)
class CoreFileSnapshot:
    relative_path: str
    ordinal: int
    content: bytes
    sha256: str
    semantic_kind: str
    semantic_sha256: str
    file_role: str
    encoding_profile: str
    newline_profile: str
    csv: CsvFileSnapshot | None


@dataclass(frozen=True)
class ParityReport:
    revision_id: str
    manifest_sha256: str
    raw_tree_sha256: str
    semantic_tree_sha256: str
    file_count: int
    csv_file_count: int
    csv_row_count: int
    file_sha256: Mapping[str, str]
    csv_row_counts: Mapping[str, int]
    csv_semantic_sha256: Mapping[str, str]
    evidence_to_claim_count: int
    evidence_to_claim_sha256: str
    claim_to_evidence_count: int
    claim_to_evidence_sha256: str
    ev053_asymmetry_preserved: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "manifest_sha256": self.manifest_sha256,
            "raw_tree_sha256": self.raw_tree_sha256,
            "semantic_tree_sha256": self.semantic_tree_sha256,
            "file_count": self.file_count,
            "csv_file_count": self.csv_file_count,
            "csv_row_count": self.csv_row_count,
            "file_sha256": dict(self.file_sha256),
            "csv_row_counts": dict(self.csv_row_counts),
            "csv_semantic_sha256": dict(self.csv_semantic_sha256),
            "evidence_to_claim": {
                "count": self.evidence_to_claim_count,
                "sha256": self.evidence_to_claim_sha256,
            },
            "claim_to_evidence": {
                "count": self.claim_to_evidence_count,
                "sha256": self.claim_to_evidence_sha256,
            },
            "ev053_asymmetry_preserved": self.ev053_asymmetry_preserved,
        }


@dataclass(frozen=True)
class ResearchCoreSnapshot:
    root: Path
    manifest_sha256: str
    raw_tree_sha256: str
    semantic_tree_sha256: str
    files: tuple[CoreFileSnapshot, ...]
    evidence_to_claim_edges: tuple[tuple[str, str], ...]
    claim_to_evidence_edges: tuple[tuple[str, str], ...]

    @property
    def revision_id(self) -> str:
        # raw tree 是 exact-byte revision identity；semantic tree 另行揭露，不取代它。
        return self.raw_tree_sha256

    @property
    def csv_files(self) -> tuple[CsvFileSnapshot, ...]:
        return tuple(file.csv for file in self.files if file.csv is not None)

    @property
    def csv_row_count(self) -> int:
        return sum(len(csv_file.rows) for csv_file in self.csv_files)

    def file(self, relative_path: str) -> CoreFileSnapshot:
        for file in self.files:
            if file.relative_path == relative_path:
                return file
        raise KeyError(relative_path)

    def csv_file(self, relative_path: str) -> CsvFileSnapshot:
        file = self.file(relative_path)
        if file.csv is None:
            raise KeyError(f"not a CSV file: {relative_path}")
        return file.csv

    def report(self) -> ParityReport:
        return _build_report(
            revision_id=self.revision_id,
            manifest_sha256=self.manifest_sha256,
            raw_tree_sha256=self.raw_tree_sha256,
            semantic_tree_sha256=self.semantic_tree_sha256,
            files=self.files,
            evidence_to_claim_edges=self.evidence_to_claim_edges,
            claim_to_evidence_edges=self.claim_to_evidence_edges,
        )


def canonical_json_bytes(value: Any) -> bytes:
    """跨 importer／API 共用的 canonical JSON bytes（不含時間或環境輸入）。"""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """回傳原始 bytes 的小寫 SHA-256。"""
    return hashlib.sha256(value).hexdigest()


def canonical_json_sha256(value: Any) -> str:
    """回傳 canonical JSON payload 的 SHA-256。"""
    return sha256_bytes(canonical_json_bytes(value))


def _file_role(relative_path: str) -> str:
    if relative_path in CSV_NATURAL_KEYS:
        return FILE_ROLE_STRUCTURED_DATA
    if relative_path in VALIDATOR_GENERATED_PATHS:
        return FILE_ROLE_VALIDATOR_GENERATED
    if relative_path.startswith("tools/") and relative_path.endswith(".py"):
        return FILE_ROLE_VALIDATOR_TOOL
    return FILE_ROLE_VERSIONED_STATIC_ASSET


def _decode_utf8(content: bytes) -> tuple[str | None, str]:
    encoding_profile = ENCODING_UTF8_BOM if content.startswith(b"\xef\xbb\xbf") else ENCODING_UTF8
    encoding = "utf-8-sig" if encoding_profile == ENCODING_UTF8_BOM else "utf-8"
    try:
        return content.decode(encoding), encoding_profile
    except UnicodeDecodeError:
        return None, ENCODING_BINARY


def _newline_profile(text: str | None) -> str:
    if text is None:
        return NEWLINE_NOT_APPLICABLE
    crlf_count = text.count("\r\n")
    lf_count = text.count("\n") - crlf_count
    cr_count = text.count("\r") - crlf_count
    present = [
        profile
        for profile, count in (
            (NEWLINE_CRLF, crlf_count),
            (NEWLINE_LF, lf_count),
            (NEWLINE_CR, cr_count),
        )
        if count
    ]
    if not present:
        return NEWLINE_NONE
    if len(present) == 1:
        return present[0]
    return NEWLINE_MIXED


def derive_artifact_profiles(relative_path: str, content: bytes) -> tuple[str, str, str]:
    """只由 canonical path 與 exact bytes 推導 role／encoding／newline profiles。"""
    _validate_relative_path(relative_path)
    text, encoding_profile = _decode_utf8(content)
    return _file_role(relative_path), encoding_profile, _newline_profile(text)


def _reject_nonfinite_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def _json_object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _assert_finite_json_numbers(value: Any) -> None:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite JSON number is not allowed")
        return
    if isinstance(value, list):
        for item in value:
            _assert_finite_json_numbers(item)
        return
    if isinstance(value, dict):
        for item in value.values():
            _assert_finite_json_numbers(item)


def json_semantic_sha256(relative_path: str, content: bytes) -> str:
    """嚴格 parse UTF-8 JSON，再以 sorted-key canonical JSON 計算 semantic digest。"""
    text, encoding_profile = _decode_utf8(content)
    if text is None:
        raise SnapshotValidationError(f"JSON must be UTF-8: {relative_path}")
    try:
        value = json.loads(
            text,
            parse_constant=_reject_nonfinite_json_constant,
            object_pairs_hook=_json_object_without_duplicate_keys,
        )
        _assert_finite_json_numbers(value)
        return canonical_json_sha256(value)
    except (json.JSONDecodeError, UnicodeEncodeError, ValueError) as exc:
        raise SnapshotValidationError(
            f"invalid {encoding_profile} JSON {relative_path}: {exc}"
        ) from exc


def canonical_manifest_bytes(lines: Iterable[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


def canonical_manifest_sha256(lines: Iterable[str]) -> str:
    """與 immutable baseline checker 相同：splitlines 後以 LF＋尾端 LF 計算。"""
    return sha256_bytes(canonical_manifest_bytes(lines))


def csv_row_payload_sha256(header: Sequence[str], values: Sequence[str]) -> str:
    """保留欄位順序與所有 raw string sentinel 的單列 digest。"""
    return canonical_json_sha256(
        {
            "serialization_version": TREE_SERIALIZATION_VERSION,
            "header": list(header),
            "values": list(values),
        }
    )


def csv_aggregate_semantic_sha256(
    relative_path: str,
    natural_key_field: str,
    header: Sequence[str],
    rows: Iterable[tuple[str, Sequence[str]]],
) -> str:
    """忽略 CSV quoting，但精確保留 header、row order 與 raw string sentinel。"""
    semantic_rows = [
        {"ordinal": ordinal, "natural_key": natural_key, "values": list(values)}
        for ordinal, (natural_key, values) in enumerate(rows, 1)
    ]
    return canonical_json_sha256(
        {
            "serialization_version": TREE_SERIALIZATION_VERSION,
            "path": relative_path,
            "natural_key_field": natural_key_field,
            "header": list(header),
            "rows": semantic_rows,
        }
    )


def raw_tree_aggregate_sha256(file_contents: Mapping[str, bytes]) -> str:
    """以 path/content 長度 framing 聚合原始 bytes，不是 hash-of-hashes。"""
    _reject_path_collisions(file_contents, label="raw-tree")
    digest = hashlib.sha256()
    digest.update(b"PCR-RAW-TREE\x00")
    digest.update(TREE_SERIALIZATION_VERSION.to_bytes(4, "big"))
    digest.update(len(file_contents).to_bytes(8, "big"))
    for relative_path in sorted(file_contents):
        content = file_contents[relative_path]
        if not isinstance(content, bytes):
            raise TypeError(f"raw tree content must be bytes: {relative_path}")
        encoded_path = relative_path.encode("utf-8")
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def semantic_tree_aggregate_sha256(
    file_semantics: Mapping[str, tuple[str, str]],
) -> str:
    """依 canonical path 排序的 semantic tree digest。"""
    _reject_path_collisions(file_semantics, label="semantic-tree")
    return canonical_json_sha256(
        {
            "serialization_version": TREE_SERIALIZATION_VERSION,
            "files": [
                {
                    "path": relative_path,
                    "kind": file_semantics[relative_path][0],
                    "sha256": file_semantics[relative_path][1],
                }
                for relative_path in sorted(file_semantics)
            ],
        }
    )


def _validate_relative_path(relative_path: str) -> None:
    if not relative_path or "\x00" in relative_path:
        raise SnapshotValidationError("manifest path is empty or contains NUL")
    if "\\" in relative_path or relative_path.startswith("/") or "//" in relative_path:
        raise SnapshotValidationError(f"manifest path is not canonical POSIX: {relative_path!r}")
    if unicodedata.normalize("NFC", relative_path) != relative_path:
        raise SnapshotValidationError(f"manifest path is not NFC-normalized: {relative_path!r}")
    pure = PurePosixPath(relative_path)
    if any(part in {"", ".", ".."} for part in pure.parts) or ":" in relative_path:
        raise SnapshotValidationError(f"manifest path is unsafe: {relative_path!r}")
    if pure.as_posix() != relative_path:
        raise SnapshotValidationError(f"manifest path is not canonical: {relative_path!r}")


def _collision_key(relative_path: str) -> str:
    return unicodedata.normalize("NFC", relative_path).casefold()


def _reject_path_collisions(paths: Iterable[str], *, label: str) -> None:
    seen: dict[str, str] = {}
    for relative_path in paths:
        _validate_relative_path(relative_path)
        key = _collision_key(relative_path)
        previous = seen.get(key)
        if previous is not None and previous != relative_path:
            raise SnapshotValidationError(
                f"{label} path case/Unicode collision: {previous!r} vs {relative_path!r}"
            )
        if previous == relative_path:
            raise SnapshotValidationError(f"duplicate {label} path: {relative_path!r}")
        seen[key] = relative_path


def _is_symlink_or_reparse(metadata: os.stat_result) -> bool:
    if stat.S_ISLNK(metadata.st_mode):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    return bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)


def _assert_source_path_has_no_reparse(path: Path, *, label: str) -> Path:
    lexical_path = Path(os.path.abspath(os.fspath(path)))
    for candidate in (lexical_path, *lexical_path.parents):
        if not os.path.lexists(candidate):
            continue
        if _is_symlink_or_reparse(candidate.lstat()):
            raise SnapshotValidationError(
                f"{label} must not traverse a symlink or reparse point: {candidate}"
            )
    return lexical_path


def load_pinned_manifest(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
    expected_file_count: int = EXPECTED_FILE_COUNT,
) -> tuple[str, tuple[ManifestEntry, ...]]:
    lexical_manifest = _assert_source_path_has_no_reparse(
        manifest_path, label="manifest"
    )
    manifest = lexical_manifest.resolve(strict=True)
    if not stat.S_ISREG(manifest.lstat().st_mode):
        raise SnapshotValidationError(f"manifest is not a regular file: {manifest}")
    try:
        text = manifest.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SnapshotValidationError("manifest must be UTF-8") from exc
    lines = text.splitlines()
    manifest_sha256 = canonical_manifest_sha256(lines)
    if manifest_sha256 != expected_manifest_sha256:
        raise SnapshotValidationError(
            "manifest SHA-256 mismatch "
            f"(expected {expected_manifest_sha256}, got {manifest_sha256})"
        )

    entries: list[ManifestEntry] = []
    for line_number, line in enumerate(lines, 1):
        if len(line) < 67 or line[64:66] != "  ":
            raise SnapshotValidationError(f"invalid manifest line {line_number}: {line!r}")
        digest, relative_path = line[:64], line[66:]
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise SnapshotValidationError(f"invalid SHA-256 at manifest line {line_number}")
        entries.append(ManifestEntry(relative_path=relative_path, sha256=digest))

    if len(entries) != expected_file_count:
        raise SnapshotValidationError(
            f"manifest file count mismatch (expected {expected_file_count}, got {len(entries)})"
        )
    _reject_path_collisions((entry.relative_path for entry in entries), label="manifest")
    return manifest_sha256, tuple(sorted(entries, key=lambda entry: entry.relative_path))


def _walk_regular_files(root: Path) -> dict[str, Path]:
    root = _assert_source_path_has_no_reparse(root, label="research core root")
    if not root.is_dir():
        raise SnapshotValidationError(f"research core is not a directory: {root}")

    files: dict[str, Path] = {}
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in (*directory_names, *file_names):
            candidate = current_path / name
            metadata = candidate.lstat()
            if _is_symlink_or_reparse(metadata):
                relative = candidate.relative_to(root).as_posix()
                raise SnapshotValidationError(
                    f"research core contains symlink or reparse point: {relative}"
                )
        for name in file_names:
            candidate = current_path / name
            mode = candidate.lstat().st_mode
            if not stat.S_ISREG(mode):
                relative = candidate.relative_to(root).as_posix()
                raise SnapshotValidationError(f"research core contains non-regular file: {relative}")
            relative = candidate.relative_to(root).as_posix()
            if relative in VALIDATOR_RUNTIME_PATHS:
                continue
            files[relative] = candidate

    _reject_path_collisions(files, label="research-core")
    return files


def _load_csv(
    relative_path: str,
    content: bytes,
    *,
    natural_key_field: str,
) -> CsvFileSnapshot:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SnapshotValidationError(f"CSV must be UTF-8: {relative_path}") from exc
    try:
        records = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as exc:
        raise SnapshotValidationError(f"invalid CSV {relative_path}: {exc}") from exc
    if not records:
        raise SnapshotValidationError(f"CSV has no header: {relative_path}")

    header = tuple(records[0])
    if not header or any(not field for field in header) or len(set(header)) != len(header):
        raise SnapshotValidationError(f"CSV header is empty or duplicated: {relative_path}")
    if natural_key_field not in header:
        raise SnapshotValidationError(
            f"CSV {relative_path} is missing natural key column {natural_key_field}"
        )
    natural_key_index = header.index(natural_key_field)

    rows: list[CsvRowSnapshot] = []
    seen_keys: set[str] = set()
    for ordinal, raw_values in enumerate(records[1:], 1):
        values = tuple(raw_values)
        if len(values) != len(header):
            raise SnapshotValidationError(
                f"CSV {relative_path} row {ordinal} has {len(values)} values; "
                f"expected {len(header)}"
            )
        natural_key = values[natural_key_index]
        if not natural_key:
            raise SnapshotValidationError(
                f"CSV {relative_path} row {ordinal} has an empty natural key"
            )
        if natural_key in seen_keys:
            raise SnapshotValidationError(
                f"CSV {relative_path} has duplicate natural key {natural_key!r}"
            )
        seen_keys.add(natural_key)
        rows.append(
            CsvRowSnapshot(
                ordinal=ordinal,
                natural_key=natural_key,
                values=values,
                row_sha256=csv_row_payload_sha256(header, values),
            )
        )

    semantic_sha256 = csv_aggregate_semantic_sha256(
        relative_path,
        natural_key_field,
        header,
        ((row.natural_key, row.values) for row in rows),
    )
    return CsvFileSnapshot(
        relative_path=relative_path,
        natural_key_field=natural_key_field,
        header=header,
        rows=tuple(rows),
        semantic_sha256=semantic_sha256,
    )


def _split_ids(raw: str) -> tuple[str, ...]:
    values = tuple(value.strip() for value in raw.split(";") if value.strip())
    if len(values) != len(set(values)):
        raise SnapshotValidationError(f"duplicate ID in semicolon list: {raw!r}")
    return values


def _extract_claim_edges(
    csv_files: Mapping[str, CsvFileSnapshot],
) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    evidence_file = csv_files["92_EVIDENCE_LEDGER.csv"]
    claim_file = csv_files["93_CLAIM_REGISTER.csv"]
    evidence_rows = {
        row.natural_key: row.as_mapping(evidence_file.header) for row in evidence_file.rows
    }
    claim_rows = {row.natural_key: row.as_mapping(claim_file.header) for row in claim_file.rows}

    evidence_to_claim: list[tuple[str, str]] = []
    for evidence_id, row in evidence_rows.items():
        claim_id = row["claim_id"]
        if not claim_id:
            continue
        if claim_id not in claim_rows:
            raise SnapshotValidationError(
                f"evidence {evidence_id} references missing claim {claim_id}"
            )
        evidence_to_claim.append((evidence_id, claim_id))

    claim_to_evidence: list[tuple[str, str]] = []
    for claim_id, row in claim_rows.items():
        for evidence_id in _split_ids(row["evidence_ids"]):
            if evidence_id not in evidence_rows:
                raise SnapshotValidationError(
                    f"claim {claim_id} references missing evidence {evidence_id}"
                )
            claim_to_evidence.append((claim_id, evidence_id))

    return tuple(sorted(evidence_to_claim)), tuple(sorted(claim_to_evidence))


def snapshot_contract_for_manifest(manifest_sha256: str) -> SnapshotContract:
    """Resolve exact structural pins for a known manifest generation.

    Explicit, non-checkpoint manifests retain the current-generation contract so
    callers can validate a candidate with the same shape.  Synthetic tests or
    future migrations that intentionally change one pin must pass that override
    explicitly; historical checkpoint manifests never inherit newer counts.
    """

    return PINNED_SNAPSHOT_CONTRACTS.get(
        manifest_sha256,
        CURRENT_SNAPSHOT_CONTRACT,
    )


def load_research_core_snapshot(
    research_core: Path = DEFAULT_RESEARCH_CORE,
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
    expected_file_count: int | None = None,
    expected_csv_file_count: int | None = None,
    expected_csv_row_count: int | None = None,
    expected_evidence_to_claim_count: int | None = None,
    expected_claim_to_evidence_count: int | None = None,
) -> ResearchCoreSnapshot:
    contract = snapshot_contract_for_manifest(expected_manifest_sha256)
    expected_file_count = (
        contract.file_count if expected_file_count is None else expected_file_count
    )
    expected_csv_file_count = (
        contract.csv_file_count
        if expected_csv_file_count is None
        else expected_csv_file_count
    )
    expected_csv_row_count = (
        contract.csv_row_count
        if expected_csv_row_count is None
        else expected_csv_row_count
    )
    expected_evidence_to_claim_count = (
        contract.evidence_to_claim_count
        if expected_evidence_to_claim_count is None
        else expected_evidence_to_claim_count
    )
    expected_claim_to_evidence_count = (
        contract.claim_to_evidence_count
        if expected_claim_to_evidence_count is None
        else expected_claim_to_evidence_count
    )
    lexical_root = _assert_source_path_has_no_reparse(
        research_core, label="research core root"
    )
    root = lexical_root.resolve(strict=True)
    manifest_sha256, entries = load_pinned_manifest(
        manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_file_count=expected_file_count,
    )
    actual_files = _walk_regular_files(root)
    expected_paths = {entry.relative_path for entry in entries}
    actual_paths = set(actual_files)
    missing = sorted(expected_paths - actual_paths)
    extra = sorted(actual_paths - expected_paths)
    if missing or extra:
        raise SnapshotValidationError(
            f"research-core file set drift (missing={missing}, extra={extra})"
        )

    manifest_by_path = {entry.relative_path: entry for entry in entries}
    csv_paths = {path for path in expected_paths if path.endswith(".csv")}
    configured_csv_paths = set(CSV_NATURAL_KEYS)
    if csv_paths != configured_csv_paths:
        raise SnapshotValidationError(
            "CSV dataset set drift "
            f"(missing key specs={sorted(csv_paths - configured_csv_paths)}, "
            f"stale key specs={sorted(configured_csv_paths - csv_paths)})"
        )
    if len(csv_paths) != expected_csv_file_count:
        raise SnapshotValidationError(
            f"CSV file count mismatch (expected {expected_csv_file_count}, got {len(csv_paths)})"
        )

    files: list[CoreFileSnapshot] = []
    semantic_files: dict[str, tuple[str, str]] = {}
    for ordinal, relative_path in enumerate(sorted(expected_paths), 1):
        content = actual_files[relative_path].read_bytes()
        digest = sha256_bytes(content)
        expected_digest = manifest_by_path[relative_path].sha256
        if digest != expected_digest:
            raise SnapshotValidationError(
                f"file SHA-256 mismatch for {relative_path} "
                f"(expected {expected_digest}, got {digest})"
            )
        file_role, encoding_profile, newline_profile = derive_artifact_profiles(
            relative_path, content
        )
        csv_file = None
        if relative_path in CSV_NATURAL_KEYS:
            csv_file = _load_csv(
                relative_path,
                content,
                natural_key_field=CSV_NATURAL_KEYS[relative_path],
            )
            semantic_kind = "csv"
            semantic_sha256 = csv_file.semantic_sha256
        elif relative_path.endswith(".json"):
            semantic_kind = "json"
            semantic_sha256 = json_semantic_sha256(relative_path, content)
        else:
            semantic_kind = "raw"
            semantic_sha256 = digest
        semantic_files[relative_path] = (semantic_kind, semantic_sha256)
        files.append(
            CoreFileSnapshot(
                relative_path=relative_path,
                ordinal=ordinal,
                content=content,
                sha256=digest,
                semantic_kind=semantic_kind,
                semantic_sha256=semantic_sha256,
                file_role=file_role,
                encoding_profile=encoding_profile,
                newline_profile=newline_profile,
                csv=csv_file,
            )
        )

    raw_tree_sha256 = raw_tree_aggregate_sha256(
        {file.relative_path: file.content for file in files}
    )
    semantic_tree_sha256 = semantic_tree_aggregate_sha256(semantic_files)
    csv_files = {file.csv.relative_path: file.csv for file in files if file.csv is not None}
    csv_row_count = sum(len(csv_file.rows) for csv_file in csv_files.values())
    if csv_row_count != expected_csv_row_count:
        raise SnapshotValidationError(
            f"CSV row count mismatch (expected {expected_csv_row_count}, got {csv_row_count})"
        )

    evidence_to_claim, claim_to_evidence = _extract_claim_edges(csv_files)
    if len(evidence_to_claim) != expected_evidence_to_claim_count:
        raise SnapshotValidationError(
            "Evidence→Claim edge count mismatch "
            f"(expected {expected_evidence_to_claim_count}, got {len(evidence_to_claim)})"
        )
    if len(claim_to_evidence) != expected_claim_to_evidence_count:
        raise SnapshotValidationError(
            "Claim→Evidence edge count mismatch "
            f"(expected {expected_claim_to_evidence_count}, got {len(claim_to_evidence)})"
        )
    if ("ev053", "CLM-PVE-F810-STD") not in evidence_to_claim:
        raise SnapshotValidationError("ev053 declared Evidence→Claim edge is missing")
    if ("CLM-PVE-F810-STD", "ev053") in claim_to_evidence:
        raise SnapshotValidationError("ev053 asymmetry was incorrectly symmetrized")

    return ResearchCoreSnapshot(
        root=root,
        manifest_sha256=manifest_sha256,
        raw_tree_sha256=raw_tree_sha256,
        semantic_tree_sha256=semantic_tree_sha256,
        files=tuple(files),
        evidence_to_claim_edges=evidence_to_claim,
        claim_to_evidence_edges=claim_to_evidence,
    )


def _build_report(
    *,
    revision_id: str,
    manifest_sha256: str,
    raw_tree_sha256: str,
    semantic_tree_sha256: str,
    files: Sequence[CoreFileSnapshot],
    evidence_to_claim_edges: Sequence[tuple[str, str]],
    claim_to_evidence_edges: Sequence[tuple[str, str]],
) -> ParityReport:
    csv_files = [file.csv for file in files if file.csv is not None]
    evidence_edge_set = set(evidence_to_claim_edges)
    claim_edge_set = set(claim_to_evidence_edges)
    return ParityReport(
        revision_id=revision_id,
        manifest_sha256=manifest_sha256,
        raw_tree_sha256=raw_tree_sha256,
        semantic_tree_sha256=semantic_tree_sha256,
        file_count=len(files),
        csv_file_count=len(csv_files),
        csv_row_count=sum(len(csv_file.rows) for csv_file in csv_files),
        file_sha256={file.relative_path: file.sha256 for file in files},
        csv_row_counts={csv_file.relative_path: len(csv_file.rows) for csv_file in csv_files},
        csv_semantic_sha256={
            csv_file.relative_path: csv_file.semantic_sha256 for csv_file in csv_files
        },
        evidence_to_claim_count=len(evidence_to_claim_edges),
        evidence_to_claim_sha256=canonical_json_sha256(sorted(evidence_to_claim_edges)),
        claim_to_evidence_count=len(claim_to_evidence_edges),
        claim_to_evidence_sha256=canonical_json_sha256(sorted(claim_to_evidence_edges)),
        ev053_asymmetry_preserved=(
            ("ev053", "CLM-PVE-F810-STD") in evidence_edge_set
            and ("CLM-PVE-F810-STD", "ev053") not in claim_edge_set
        ),
    )


def _assert_new_external_destination(destination: Path, canonical_root: Path) -> tuple[Path, Path]:
    if any(part == ".." for part in destination.parts):
        raise ExportSafetyError("export destination must not contain path traversal")
    lexical_destination = Path(os.path.abspath(os.fspath(destination)))
    if os.path.lexists(lexical_destination):
        metadata = lexical_destination.lstat()
        if _is_symlink_or_reparse(metadata):
            state = "symlink or reparse point"
        elif stat.S_ISDIR(metadata.st_mode) and any(lexical_destination.iterdir()):
            state = "non-empty"
        else:
            state = "existing"
        raise ExportSafetyError(
            f"export destination must be new, not {state}: {lexical_destination}"
        )

    lexical_parent = lexical_destination.parent
    for ancestor in (lexical_parent, *lexical_parent.parents):
        if not os.path.lexists(ancestor):
            continue
        if _is_symlink_or_reparse(ancestor.lstat()):
            raise ExportSafetyError(
                f"export destination ancestor must not be a symlink or reparse point: {ancestor}"
            )

    canonical = canonical_root.resolve(strict=True)
    resolved = lexical_destination.resolve(strict=False)
    if resolved == canonical or resolved.is_relative_to(canonical):
        raise ExportSafetyError("export destination must be outside the canonical research core")
    if not lexical_parent.is_dir():
        raise ExportSafetyError(f"export parent directory does not exist: {lexical_parent}")
    return resolved, canonical


def export_exact_snapshot(
    snapshot: ResearchCoreSnapshot,
    destination: Path,
    *,
    canonical_root: Path | None = None,
    verify_manifest_path: Path = DEFAULT_MANIFEST,
) -> ParityReport:
    destination, _canonical = _assert_new_external_destination(
        destination,
        canonical_root or snapshot.root,
    )
    staging = destination.parent / f".{destination.name}.tmp-{uuid.uuid4().hex}"
    if staging.exists():
        raise ExportSafetyError(f"staging path unexpectedly exists: {staging}")

    try:
        staging.mkdir()
        for file in snapshot.files:
            target = staging.joinpath(*PurePosixPath(file.relative_path).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(file.content)

        exported = load_research_core_snapshot(
            staging,
            verify_manifest_path,
            expected_manifest_sha256=snapshot.manifest_sha256,
            expected_file_count=len(snapshot.files),
            expected_csv_file_count=len(snapshot.csv_files),
            expected_csv_row_count=snapshot.csv_row_count,
            expected_evidence_to_claim_count=len(snapshot.evidence_to_claim_edges),
            expected_claim_to_evidence_count=len(snapshot.claim_to_evidence_edges),
        )
        if exported.raw_tree_sha256 != snapshot.raw_tree_sha256:
            raise SnapshotDriftError(
                "core_files_drift", "export raw tree differs from source snapshot"
            )
        if exported.semantic_tree_sha256 != snapshot.semantic_tree_sha256:
            raise SnapshotDriftError(
                "core_csv_rows_drift", "export semantic tree differs from source snapshot"
            )
        staging.rename(destination)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return exported.report()


def core_materialization_manifest(snapshot: ResearchCoreSnapshot) -> dict[str, Any]:
    """建立 API readiness 可重算的完整 file／row／directed-edge manifest。"""
    files: dict[str, Any] = {}
    for file in snapshot.files:
        csv_file = file.csv
        files[file.relative_path] = {
            "ordinal": file.ordinal,
            "sha256": file.sha256,
            "semantic_kind": file.semantic_kind,
            "semantic_sha256": file.semantic_sha256,
            "byte_length": len(file.content),
            "file_role": file.file_role,
            "encoding_profile": file.encoding_profile,
            "newline_profile": file.newline_profile,
            "is_csv": csv_file is not None,
            "natural_key_field": csv_file.natural_key_field if csv_file else None,
            "header": list(csv_file.header) if csv_file else None,
            "row_count": len(csv_file.rows) if csv_file else 0,
            "row_sha256": (
                {row.natural_key: row.row_sha256 for row in csv_file.rows}
                if csv_file
                else {}
            ),
        }
    report = snapshot.report()
    return {
        "schema_version": 1,
        "files": files,
        "edges": {
            "evidence_declared": {
                "count": report.evidence_to_claim_count,
                "sha256": report.evidence_to_claim_sha256,
            },
            "claim_evidence": {
                "count": report.claim_to_evidence_count,
                "sha256": report.claim_to_evidence_sha256,
            },
        },
    }


def core_materialization_sha256(snapshot: ResearchCoreSnapshot) -> str:
    return canonical_json_sha256(core_materialization_manifest(snapshot))


def _snapshot_project_version(snapshot: ResearchCoreSnapshot) -> str:
    try:
        config = json.loads(snapshot.file("tools/validation_config.json").content)
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
        return "UNKNOWN"
    value = config.get("project_version") if isinstance(config, dict) else None
    return value if isinstance(value, str) and value else "UNKNOWN"


# ORM materialization functions are intentionally colocated with snapshot parity so both the
# importer and exporter consume one contract.  The model classes are imported lazily to keep
# this pure loader usable before a database engine is constructed.
def materialize_snapshot(
    session: Session,
    snapshot: ResearchCoreSnapshot,
    *,
    import_run_id: str | None = None,
) -> bool:
    from pcr_database.models import CoreCsvRow, CoreFile, CoreRevision

    existing = session.get(CoreRevision, snapshot.revision_id)
    if existing is not None:
        if import_run_id is not None and existing.import_run_id not in {None, import_run_id}:
            raise SnapshotDriftError(
                "revision_manifest_mismatch",
                "core revision is linked to a different import run",
            )
        assert_materialized_snapshot(session, snapshot, require_succeeded=False)
        return False

    report = snapshot.report()
    manifest = core_materialization_manifest(snapshot)
    revision = CoreRevision(
        revision_id=snapshot.revision_id,
        import_run_id=import_run_id,
        manifest_sha256=snapshot.manifest_sha256,
        raw_tree_sha256=snapshot.raw_tree_sha256,
        semantic_tree_sha256=snapshot.semantic_tree_sha256,
        file_count=len(snapshot.files),
        csv_file_count=len(snapshot.csv_files),
        csv_row_count=snapshot.csv_row_count,
        evidence_to_claim_count=len(snapshot.evidence_to_claim_edges),
        evidence_to_claim_sha256=report.evidence_to_claim_sha256,
        claim_to_evidence_count=len(snapshot.claim_to_evidence_edges),
        claim_to_evidence_sha256=report.claim_to_evidence_sha256,
        status="STAGING",
        manifest=manifest,
        # 此欄只屬 typed serving closure；artifact parity 留在 revision.manifest。
        materialization_sha256=None,
        project_version=_snapshot_project_version(snapshot),
        serialization_version=1,
    )
    session.add(revision)
    session.flush()
    pending_rows: list[CoreCsvRow] = []
    for file in snapshot.files:
        session.add(
            CoreFile(
                revision_id=snapshot.revision_id,
                relative_path=file.relative_path,
                ordinal=file.ordinal,
                sha256=file.sha256,
                size_bytes=len(file.content),
                content=file.content,
                is_csv=file.csv is not None,
                natural_key_field=file.csv.natural_key_field if file.csv else None,
                header=list(file.csv.header) if file.csv else None,
                semantic_sha256=file.semantic_sha256,
            )
        )
        if file.csv is None:
            continue
        for row in file.csv.rows:
            pending_rows.append(
                CoreCsvRow(
                    revision_id=snapshot.revision_id,
                    relative_path=file.relative_path,
                    ordinal=row.ordinal,
                    natural_key=row.natural_key,
                    values=list(row.values),
                    row_sha256=row.row_sha256,
                )
            )
    # Core* models故意不建立大型 ORM relationship；分階段 flush 明確守住複合 FK 順序。
    session.flush()
    session.add_all(pending_rows)
    session.flush()
    assert_materialized_snapshot(session, snapshot, require_succeeded=False)
    return True


def finalize_materialized_snapshot(
    session: Session,
    snapshot: ResearchCoreSnapshot,
    *,
    import_run_id: str,
    typed_materialization_sha256: str,
) -> None:
    """typed closure 與 parity 都完成後，在同一 transaction 將 STAGING 封存成功。"""
    from pcr_database.models import CoreRevision, ImportRun

    revision = session.get(CoreRevision, snapshot.revision_id)
    if revision is None:
        raise SnapshotDriftError(
            "revision_manifest_missing", "cannot finalize a missing core revision"
        )
    if revision.status == "FAILED":
        raise SnapshotDriftError(
            "revision_manifest_mismatch", "cannot finalize a FAILED core revision"
        )
    if len(typed_materialization_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in typed_materialization_sha256
    ):
        raise SnapshotDriftError(
            "revision_manifest_mismatch", "typed materialization SHA-256 is invalid"
        )
    import_run = session.get(ImportRun, import_run_id)
    if import_run is None:
        raise SnapshotDriftError(
            "revision_manifest_missing", "typed import run is missing"
        )
    try:
        run_materialization_sha256 = import_run.manifest["materialization"]["sha256"]
    except (KeyError, TypeError):
        run_materialization_sha256 = None
    if run_materialization_sha256 != typed_materialization_sha256:
        raise SnapshotDriftError(
            "revision_manifest_mismatch",
            "typed materialization hash differs from ImportRun manifest",
        )
    if revision.import_run_id not in {None, import_run_id}:
        raise SnapshotDriftError(
            "revision_manifest_mismatch",
            "core revision is linked to a different import run",
        )
    revision.import_run_id = import_run_id
    revision.materialization_sha256 = typed_materialization_sha256
    assert_materialized_snapshot(session, snapshot, require_succeeded=False)
    revision.status = "SUCCEEDED"
    session.flush()


def _snapshot_from_materialized_rows(
    session: Session,
    revision_id: str,
    *,
    root: Path,
    require_succeeded: bool,
) -> ResearchCoreSnapshot:
    from pcr_database.models import CoreCsvRow, CoreFile, CoreRevision

    revision = session.get(CoreRevision, revision_id)
    if revision is None:
        raise SnapshotDriftError(
            "revision_manifest_missing", f"core revision is missing: {revision_id}"
        )
    allowed_statuses = {"SUCCEEDED"} if require_succeeded else {"STAGING", "SUCCEEDED"}
    if revision.status not in allowed_statuses:
        raise SnapshotDriftError(
            "revision_manifest_missing",
            f"core revision is not SUCCEEDED: {revision.status}",
        )
    if revision.serialization_version != 1:
        raise SnapshotDriftError(
            "revision_manifest_version",
            f"unsupported core serialization version: {revision.serialization_version}",
        )
    if not isinstance(revision.manifest, dict):
        raise SnapshotDriftError("revision_manifest_missing", "core manifest is missing")
    if revision.manifest.get("schema_version") != 1:
        raise SnapshotDriftError("revision_manifest_version", "core manifest version drifted")
    stored_files = session.scalars(
        select(CoreFile)
        .where(CoreFile.revision_id == revision_id)
        .order_by(CoreFile.ordinal, CoreFile.relative_path)
    ).all()
    if len(stored_files) != revision.file_count:
        raise SnapshotDriftError(
            "core_files_drift",
            f"core file count drifted ({len(stored_files)} != {revision.file_count})",
        )
    expected_ordinals = list(range(1, len(stored_files) + 1))
    actual_ordinals = [file.ordinal for file in stored_files]
    if actual_ordinals != expected_ordinals:
        raise SnapshotDriftError("core_files_drift", "core file ordinals drifted")
    try:
        _reject_path_collisions(
            (file.relative_path for file in stored_files), label="materialized core"
        )
    except SnapshotValidationError as exc:
        raise SnapshotDriftError("core_files_drift", str(exc)) from exc

    all_stored_rows = session.scalars(
        select(CoreCsvRow)
        .where(CoreCsvRow.revision_id == revision_id)
        .order_by(CoreCsvRow.relative_path, CoreCsvRow.ordinal)
    ).all()
    rows_by_path: dict[str, list[Any]] = {}
    for row in all_stored_rows:
        rows_by_path.setdefault(row.relative_path, []).append(row)

    files: list[CoreFileSnapshot] = []
    file_sha256: dict[str, str] = {}
    file_contents: dict[str, bytes] = {}
    file_semantics: dict[str, tuple[str, str]] = {}
    for stored_file in stored_files:
        content = bytes(stored_file.content)
        actual_file_sha256 = sha256_bytes(content)
        if (
            actual_file_sha256 != stored_file.sha256
            or len(content) != stored_file.size_bytes
        ):
            raise SnapshotDriftError(
                "core_files_drift",
                f"core file bytes drifted: {stored_file.relative_path}",
            )
        file_sha256[stored_file.relative_path] = actual_file_sha256
        file_contents[stored_file.relative_path] = content
        file_role, encoding_profile, newline_profile = derive_artifact_profiles(
            stored_file.relative_path, content
        )
        csv_file = None
        if stored_file.is_csv:
            expected_key_field = CSV_NATURAL_KEYS.get(stored_file.relative_path)
            if expected_key_field is None or stored_file.natural_key_field != expected_key_field:
                raise SnapshotDriftError(
                    "core_csv_rows_drift",
                    f"CSV natural-key contract drifted: {stored_file.relative_path}",
                )
            if not isinstance(stored_file.header, list) or not all(
                isinstance(field, str) for field in stored_file.header
            ):
                raise SnapshotDriftError(
                    "core_csv_rows_drift",
                    f"CSV header shape drifted: {stored_file.relative_path}",
                )
            header = tuple(stored_file.header)
            if expected_key_field not in header or len(header) != len(set(header)):
                raise SnapshotDriftError(
                    "core_csv_rows_drift",
                    f"CSV header contract drifted: {stored_file.relative_path}",
                )
            natural_key_index = header.index(expected_key_field)
            stored_rows = rows_by_path.pop(stored_file.relative_path, [])
            if [row.ordinal for row in stored_rows] != list(range(1, len(stored_rows) + 1)):
                raise SnapshotDriftError(
                    "core_csv_rows_drift",
                    f"CSV row ordinals drifted: {stored_file.relative_path}",
                )
            rows: list[CsvRowSnapshot] = []
            natural_keys: set[str] = set()
            for row in stored_rows:
                if not isinstance(row.values, list) or not all(
                    isinstance(value, str) for value in row.values
                ):
                    raise SnapshotDriftError(
                        "core_csv_rows_drift",
                        f"CSV row contains non-string values: {stored_file.relative_path}",
                    )
                values = tuple(row.values)
                if len(values) != len(header):
                    raise SnapshotDriftError(
                        "core_csv_rows_drift",
                        f"CSV row width drifted: {stored_file.relative_path}",
                    )
                natural_key = values[natural_key_index]
                if row.natural_key != natural_key or not natural_key or natural_key in natural_keys:
                    raise SnapshotDriftError(
                        "core_csv_rows_drift",
                        f"CSV natural key drifted: {stored_file.relative_path}",
                    )
                natural_keys.add(natural_key)
                row_sha256 = csv_row_payload_sha256(header, values)
                if row.row_sha256 != row_sha256:
                    raise SnapshotDriftError(
                        "core_csv_rows_drift",
                        f"CSV row hash drifted: {stored_file.relative_path}/{natural_key}",
                    )
                rows.append(
                    CsvRowSnapshot(
                        ordinal=row.ordinal,
                        natural_key=natural_key,
                        values=values,
                        row_sha256=row_sha256,
                    )
                )
            semantic_sha256 = csv_aggregate_semantic_sha256(
                stored_file.relative_path,
                expected_key_field,
                header,
                ((row.natural_key, row.values) for row in rows),
            )
            if semantic_sha256 != stored_file.semantic_sha256:
                raise SnapshotDriftError(
                    "core_csv_rows_drift",
                    f"CSV semantic hash drifted: {stored_file.relative_path}",
                )
            csv_file = CsvFileSnapshot(
                relative_path=stored_file.relative_path,
                natural_key_field=expected_key_field,
                header=header,
                rows=tuple(rows),
                semantic_sha256=semantic_sha256,
            )
            try:
                raw_csv = _load_csv(
                    stored_file.relative_path,
                    content,
                    natural_key_field=expected_key_field,
                )
            except SnapshotValidationError as exc:
                raise SnapshotDriftError("core_files_drift", str(exc)) from exc
            if raw_csv != csv_file:
                raise SnapshotDriftError(
                    "core_csv_rows_drift",
                    f"CSV raw bytes and row projection disagree: {stored_file.relative_path}",
                )
            semantic_kind = "csv"
        else:
            if (
                stored_file.relative_path in CSV_NATURAL_KEYS
                or stored_file.natural_key_field is not None
                or stored_file.header is not None
                or rows_by_path.pop(stored_file.relative_path, [])
            ):
                raise SnapshotDriftError(
                    "core_csv_rows_drift",
                    f"non-CSV materialization shape drifted: {stored_file.relative_path}",
                )
            if stored_file.relative_path.endswith(".json"):
                try:
                    semantic_sha256 = json_semantic_sha256(stored_file.relative_path, content)
                except SnapshotValidationError as exc:
                    raise SnapshotDriftError("core_files_drift", str(exc)) from exc
                semantic_kind = "json"
            else:
                semantic_sha256 = actual_file_sha256
                semantic_kind = "raw"
            if stored_file.semantic_sha256 != semantic_sha256:
                raise SnapshotDriftError(
                    "core_files_drift",
                    f"non-CSV semantic hash drifted: {stored_file.relative_path}",
                )
        file_semantics[stored_file.relative_path] = (semantic_kind, semantic_sha256)
        files.append(
            CoreFileSnapshot(
                relative_path=stored_file.relative_path,
                ordinal=stored_file.ordinal,
                content=content,
                sha256=actual_file_sha256,
                semantic_kind=semantic_kind,
                semantic_sha256=semantic_sha256,
                file_role=file_role,
                encoding_profile=encoding_profile,
                newline_profile=newline_profile,
                csv=csv_file,
            )
        )
    if rows_by_path:
        raise SnapshotDriftError(
            "core_csv_rows_drift",
            f"CSV rows reference unknown files: {sorted(rows_by_path)}",
        )
    if len([file for file in files if file.csv is not None]) != revision.csv_file_count:
        raise SnapshotDriftError("core_csv_rows_drift", "CSV file count drifted")
    if len(all_stored_rows) != revision.csv_row_count:
        raise SnapshotDriftError("core_csv_rows_drift", "CSV row count drifted")
    if set(file_sha256) != set(file_semantics):
        raise SnapshotDriftError("core_files_drift", "core file semantic set drifted")

    csv_by_path = {file.csv.relative_path: file.csv for file in files if file.csv is not None}
    try:
        evidence_to_claim, claim_to_evidence = _extract_claim_edges(csv_by_path)
    except (KeyError, SnapshotValidationError) as exc:
        raise SnapshotDriftError("core_csv_rows_drift", str(exc)) from exc
    snapshot = ResearchCoreSnapshot(
        root=root,
        manifest_sha256=revision.manifest_sha256,
        raw_tree_sha256=raw_tree_aggregate_sha256(file_contents),
        semantic_tree_sha256=semantic_tree_aggregate_sha256(file_semantics),
        files=tuple(files),
        evidence_to_claim_edges=evidence_to_claim,
        claim_to_evidence_edges=claim_to_evidence,
    )
    if core_materialization_manifest(snapshot) != revision.manifest:
        raise SnapshotDriftError(
            "revision_manifest_mismatch",
            "materialized core manifest differs from values derived from CoreFile bytes",
        )
    return snapshot


def materialized_snapshot(
    session: Session,
    revision_id: str,
    *,
    canonical_root: Path = DEFAULT_RESEARCH_CORE,
    require_succeeded: bool = True,
) -> ResearchCoreSnapshot:
    return _snapshot_from_materialized_rows(
        session,
        revision_id,
        root=canonical_root.resolve(strict=True),
        require_succeeded=require_succeeded,
    )


def materialized_report(
    session: Session,
    revision_id: str,
    *,
    require_succeeded: bool = True,
) -> ParityReport:
    from pcr_database.models import CoreRevision

    revision = session.get(CoreRevision, revision_id)
    if revision is None:
        raise SnapshotDriftError(
            "revision_manifest_missing", f"core revision is missing: {revision_id}"
        )
    if not isinstance(revision.manifest, dict):
        raise SnapshotDriftError("revision_manifest_missing", "core manifest is missing")
    if revision.manifest.get("schema_version") != 1:
        raise SnapshotDriftError("revision_manifest_version", "core manifest version drifted")
    snapshot = materialized_snapshot(
        session,
        revision_id,
        require_succeeded=require_succeeded,
    )
    computed = snapshot.report()
    if computed.revision_id != revision_id:
        raise SnapshotDriftError("core_files_drift", "revision identity drifted")
    if computed.raw_tree_sha256 != revision.raw_tree_sha256:
        raise SnapshotDriftError("core_files_drift", "materialized raw tree hash drifted")
    if computed.semantic_tree_sha256 != revision.semantic_tree_sha256:
        raise SnapshotDriftError(
            "core_csv_rows_drift", "materialized semantic tree hash drifted"
        )
    if computed.file_count != revision.file_count:
        raise SnapshotDriftError("core_files_drift", "materialized file count drifted")
    if computed.csv_file_count != revision.csv_file_count:
        raise SnapshotDriftError("core_csv_rows_drift", "materialized CSV file count drifted")
    if computed.csv_row_count != revision.csv_row_count:
        raise SnapshotDriftError("core_csv_rows_drift", "materialized CSV row count drifted")
    if computed.evidence_to_claim_sha256 != revision.evidence_to_claim_sha256:
        raise SnapshotDriftError(
            "core_csv_rows_drift", "materialized Evidence→Claim edges drifted"
        )
    if computed.evidence_to_claim_count != revision.evidence_to_claim_count:
        raise SnapshotDriftError(
            "core_csv_rows_drift", "materialized Evidence→Claim edge count drifted"
        )
    if computed.claim_to_evidence_sha256 != revision.claim_to_evidence_sha256:
        raise SnapshotDriftError(
            "core_csv_rows_drift", "materialized Claim→Evidence edges drifted"
        )
    if computed.claim_to_evidence_count != revision.claim_to_evidence_count:
        raise SnapshotDriftError(
            "core_csv_rows_drift", "materialized Claim→Evidence edge count drifted"
        )
    recomputed_manifest = core_materialization_manifest(snapshot)
    if recomputed_manifest != revision.manifest:
        raise SnapshotDriftError(
            "core_csv_rows_drift", "materialized core manifest drifted"
        )
    return computed


def assert_materialized_snapshot(
    session: Session,
    expected: ResearchCoreSnapshot,
    *,
    require_succeeded: bool = True,
) -> None:
    actual = materialized_report(
        session,
        expected.revision_id,
        require_succeeded=require_succeeded,
    )
    if actual.as_dict() != expected.report().as_dict():
        raise SnapshotDriftError(
            "core_csv_rows_drift",
            "materialized parity report differs from source snapshot",
        )


def materialized_drift_reason(
    session: Session,
    revision_id: str,
    *,
    require_succeeded: bool = True,
) -> str | None:
    """API readiness 的穩定 reason；不要求呼叫端解析例外訊息。"""
    try:
        materialized_report(
            session,
            revision_id,
            require_succeeded=require_succeeded,
        )
    except SnapshotDriftError as exc:
        return exc.reason
    return None


def export_materialized_revision(
    session: Session,
    revision_id: str,
    destination: Path,
    *,
    canonical_root: Path = DEFAULT_RESEARCH_CORE,
    verify_manifest_path: Path = DEFAULT_MANIFEST,
    require_succeeded: bool = True,
) -> ParityReport:
    snapshot = materialized_snapshot(
        session,
        revision_id,
        canonical_root=canonical_root,
        require_succeeded=require_succeeded,
    )
    # Fail before writing if normalized rows, raw bytes, or directed edge sets drifted.
    materialized_report(
        session,
        revision_id,
        require_succeeded=require_succeeded,
    )
    return export_exact_snapshot(
        snapshot,
        destination,
        canonical_root=canonical_root,
        verify_manifest_path=verify_manifest_path,
    )
