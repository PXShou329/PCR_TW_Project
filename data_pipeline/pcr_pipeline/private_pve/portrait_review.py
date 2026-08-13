from __future__ import annotations

import copy
import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


REVIEW_QUEUE_SCHEMA_VERSION = "private-pve-portrait-review-queue/v1"
OVERRIDE_SCHEMA_VERSION = "private-pve-portrait-overrides/v1"
MATERIALIZATION_SCHEMA_VERSION = "private-pve-character-materialization/v1"
LOCAL_CATALOG_SCHEMA_VERSION = "private-pve-local-catalog/v1"
MAPPING_SCHEMA_VERSION = "private-pve-character-mapping/v1"

PENDING = "PENDING"
CONFIRMED = "CONFIRMED"
REVIEWED_UNKNOWN = "REVIEWED_UNKNOWN"
USER_CONFIRMED = "USER_CONFIRMED"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ICON_ID = re.compile(r"^[0-9]{6}$")
_UNIT_KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_UNKNOWN_REASONS = {
    "AMBIGUOUS_VARIANT",
    "INSUFFICIENT_EVIDENCE",
    "NOT_IDENTIFIED",
}
_SIX_STAR_STATUSES = {"AVAILABLE", "NOT_AVAILABLE", "UNVERIFIED"}
_EVIDENCE_KINDS = {
    "TW_OFFICIAL_NEWS_SNAPSHOT",
}
_EVIDENCE_CLAIMS = {"TW_SIX_STAR_RELEASE", "TW_UNIT_IDENTITY"}
_CATALOG_ROOT_FIELDS = {"assets", "builder", "schema_version", "sources", "summary"}
_CATALOG_ASSET_FIELDS = {
    "byte_length",
    "file_extension",
    "filename",
    "height_px",
    "mime_type",
    "occurrences",
    "sha256",
    "width_px",
}


class PortraitReviewError(ValueError):
    """Raised when reviewed portrait inputs fail closed validation."""


@dataclass(frozen=True)
class LoadedJson:
    document: dict[str, Any]
    sha256: str
    raw_bytes: bytes


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


def load_strict_json(path: str | Path) -> LoadedJson:
    source = Path(path)
    if source.suffix.lower() != ".json" or not source.is_file():
        raise PortraitReviewError(f"JSON input must be an existing .json file: {source}")
    try:
        raw_bytes = source.read_bytes()
        document = json.loads(
            raw_bytes.decode("utf-8"),
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PortraitReviewError(f"cannot read strict UTF-8 JSON: {source}") from exc
    if not isinstance(document, dict):
        raise PortraitReviewError(f"JSON root must be an object: {source}")
    return LoadedJson(
        document=document,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        raw_bytes=raw_bytes,
    )


def formation_asset_sha256s(catalog: Mapping[str, Any]) -> frozenset[str]:
    _assets, occurrences = _catalog_review_inputs(catalog)
    return frozenset(occurrences)


def validate_override_registry(
    registry: Mapping[str, Any],
    *,
    formation_sha256s: frozenset[str] | set[str],
    base_catalog_sha256: str,
) -> dict[str, Any]:
    """Validate a partial, human-authored override registry.

    A registry may omit pending portraits.  Every entry it does contain is strict:
    reviewed-unknown records cannot carry an identity, and confirmed records must
    close over one exact unit and all referenced six-star evidence.
    """

    _require_sha256(base_catalog_sha256, "base_catalog_sha256")
    root = _require_mapping(registry, "override registry")
    _require_exact_fields(
        root,
        {"assets", "base_catalog_sha256", "evidence", "schema_version", "units"},
        "override registry",
    )
    if root["schema_version"] != OVERRIDE_SCHEMA_VERSION:
        raise PortraitReviewError("override registry has an unsupported schema_version")
    if root["base_catalog_sha256"] != base_catalog_sha256:
        raise PortraitReviewError("override registry base_catalog_sha256 does not match")

    assets = _require_mapping(root["assets"], "override registry.assets")
    units = _require_mapping(root["units"], "override registry.units")
    evidence = _require_mapping(root["evidence"], "override registry.evidence")

    referenced_units: set[str] = set()
    for image_sha256, raw_override in assets.items():
        _require_sha256(image_sha256, "override registry.assets key")
        if image_sha256 not in formation_sha256s:
            raise PortraitReviewError(
                f"override asset is not referenced by a formation: {image_sha256}"
            )
        override = _require_mapping(
            raw_override,
            f"override registry.assets[{image_sha256!r}]",
        )
        review_status = override.get("review_status")
        if review_status == REVIEWED_UNKNOWN:
            _require_fields(
                override,
                required={"reason", "review_status"},
                optional={"note"},
                path=f"override registry.assets[{image_sha256!r}]",
            )
            if override["reason"] not in _UNKNOWN_REASONS:
                raise PortraitReviewError(
                    f"reviewed-unknown asset has an unsupported reason: {image_sha256}"
                )
            _validate_optional_note(override, image_sha256)
            continue
        if review_status != CONFIRMED:
            raise PortraitReviewError(
                f"asset review_status must be CONFIRMED or REVIEWED_UNKNOWN: {image_sha256}"
            )
        _require_fields(
            override,
            required={"identity_status", "review_status", "unit_key"},
            optional={"note"},
            path=f"override registry.assets[{image_sha256!r}]",
        )
        if override["identity_status"] != USER_CONFIRMED:
            raise PortraitReviewError(
                f"confirmed asset identity must be USER_CONFIRMED: {image_sha256}"
            )
        unit_key = _require_unit_key(override["unit_key"], f"asset {image_sha256}")
        referenced_units.add(unit_key)
        _validate_optional_note(override, image_sha256)

    referenced_evidence: set[str] = set()
    bases: dict[str, str] = {}
    for unit_key, raw_unit in units.items():
        _require_unit_key(unit_key, "override registry.units key")
        unit = _require_mapping(raw_unit, f"override registry.units[{unit_key!r}]")
        _require_fields(
            unit,
            required={
                "estertion_base_id",
                "exact_variant_status",
                "identity_evidence_ids",
                "six_star_evidence_ids",
                "six_star_tw_status",
                "tw_name",
                "tw_unit_id",
            },
            optional={"estertion_jp_name", "note"},
            path=f"override registry.units[{unit_key!r}]",
        )
        if unit_key not in referenced_units:
            raise PortraitReviewError(f"override registry contains unused unit: {unit_key}")
        tw_name = _require_text(unit["tw_name"], f"unit {unit_key}.tw_name")
        if len(tw_name) > 128:
            raise PortraitReviewError(f"unit {unit_key}.tw_name is too long")
        base_id = unit["estertion_base_id"]
        if not isinstance(base_id, str) or not re.fullmatch(r"[0-9]{4}", base_id):
            raise PortraitReviewError(
                f"unit {unit_key}.estertion_base_id must be four digits"
            )
        previous = bases.get(base_id)
        if previous is not None and previous != unit_key:
            raise PortraitReviewError(
                f"EsterTion base {base_id} is assigned to multiple unit keys"
            )
        bases[base_id] = unit_key
        tw_unit_id = _require_int(unit["tw_unit_id"], f"unit {unit_key}.tw_unit_id")
        if tw_unit_id != int(f"{base_id}01"):
            raise PortraitReviewError(
                f"unit {unit_key}.tw_unit_id must be the exact playable-unit ID "
                f"{base_id}01"
            )
        if unit["exact_variant_status"] != USER_CONFIRMED:
            raise PortraitReviewError(
                f"unit {unit_key}.exact_variant_status must be USER_CONFIRMED"
            )
        if "estertion_jp_name" in unit:
            _require_text(
                unit["estertion_jp_name"],
                f"unit {unit_key}.estertion_jp_name",
            )
        _validate_optional_note(unit, unit_key)

        six_star_status = unit["six_star_tw_status"]
        if six_star_status not in _SIX_STAR_STATUSES:
            raise PortraitReviewError(
                f"unit {unit_key}.six_star_tw_status is unsupported"
            )
        identity_evidence_ids = _require_list(
            unit["identity_evidence_ids"],
            f"unit {unit_key}.identity_evidence_ids",
        )
        if (
            not identity_evidence_ids
            or not all(
                isinstance(value, str) and value.strip()
                for value in identity_evidence_ids
            )
            or len(identity_evidence_ids) != len(set(identity_evidence_ids))
        ):
            raise PortraitReviewError(
                f"unit {unit_key}.identity_evidence_ids must be a non-empty unique string list"
            )
        referenced_evidence.update(identity_evidence_ids)

        evidence_ids = _require_list(
            unit["six_star_evidence_ids"],
            f"unit {unit_key}.six_star_evidence_ids",
        )
        if not all(isinstance(value, str) and value.strip() for value in evidence_ids):
            raise PortraitReviewError(
                f"unit {unit_key}.six_star_evidence_ids must contain non-empty strings"
            )
        if len(evidence_ids) != len(set(evidence_ids)):
            raise PortraitReviewError(
                f"unit {unit_key}.six_star_evidence_ids contains duplicates"
            )
        if six_star_status == "AVAILABLE" and not evidence_ids:
            raise PortraitReviewError(
                f"unit {unit_key} marks six-star AVAILABLE without official evidence"
            )
        if six_star_status != "AVAILABLE" and evidence_ids:
            raise PortraitReviewError(
                f"unit {unit_key} may reference six-star evidence only when AVAILABLE"
            )
        referenced_evidence.update(evidence_ids)

    missing_units = referenced_units - set(units)
    if missing_units:
        raise PortraitReviewError(
            "confirmed assets reference missing units: " + ", ".join(sorted(missing_units))
        )

    for evidence_id, raw_evidence in evidence.items():
        evidence_key = _require_text(evidence_id, "override registry.evidence key")
        item = _require_mapping(
            raw_evidence,
            f"override registry.evidence[{evidence_key!r}]",
        )
        _require_fields(
            item,
            required={
                "claims",
                "filename",
                "kind",
                "locator",
                "review_status",
                "source_sha256",
                "tw_name",
                "unit_key",
            },
            optional={"note"},
            path=f"override registry.evidence[{evidence_key!r}]",
        )
        if evidence_key not in referenced_evidence:
            raise PortraitReviewError(
                f"override registry contains unused evidence: {evidence_key}"
            )
        if item["kind"] not in _EVIDENCE_KINDS:
            raise PortraitReviewError(f"evidence {evidence_key}.kind is unsupported")
        claims = _require_list(item["claims"], f"evidence {evidence_key}.claims")
        if (
            not claims
            or len(claims) != len(set(claims))
            or not all(claim in _EVIDENCE_CLAIMS for claim in claims)
        ):
            raise PortraitReviewError(
                f"evidence {evidence_key}.claims must be a non-empty unique supported list"
            )
        if item["review_status"] != USER_CONFIRMED:
            raise PortraitReviewError(
                f"evidence {evidence_key}.review_status must be USER_CONFIRMED"
            )
        evidence_unit = _require_unit_key(
            item["unit_key"],
            f"evidence {evidence_key}.unit_key",
        )
        if evidence_unit not in units:
            raise PortraitReviewError(
                f"evidence {evidence_key} references a missing unit"
            )
        filename = _require_text(item["filename"], f"evidence {evidence_key}.filename")
        if Path(filename).name != filename or "/" in filename or "\\" in filename:
            raise PortraitReviewError(
                f"evidence {evidence_key}.filename must be a basename"
            )
        if item["tw_name"] != units[evidence_unit]["tw_name"]:
            raise PortraitReviewError(
                f"evidence {evidence_key}.tw_name does not match its exact unit"
            )
        _require_sha256(item["source_sha256"], f"evidence {evidence_key}.source_sha256")
        _require_text(item["locator"], f"evidence {evidence_key}.locator")
        _validate_optional_note(item, evidence_key)

    missing_evidence = referenced_evidence - set(evidence)
    if missing_evidence:
        raise PortraitReviewError(
            "six-star units reference missing evidence: "
            + ", ".join(sorted(missing_evidence))
        )
    for unit_key, raw_unit in units.items():
        for evidence_id in raw_unit["identity_evidence_ids"]:
            if evidence[evidence_id]["unit_key"] != unit_key:
                raise PortraitReviewError(
                    f"evidence {evidence_id} is bound to a different exact unit"
                )
            if "TW_UNIT_IDENTITY" not in evidence[evidence_id]["claims"]:
                raise PortraitReviewError(
                    f"evidence {evidence_id} does not confirm TW unit identity"
                )
        for evidence_id in raw_unit["six_star_evidence_ids"]:
            if evidence[evidence_id]["unit_key"] != unit_key:
                raise PortraitReviewError(
                    f"evidence {evidence_id} is bound to a different exact unit"
                )
            if "TW_SIX_STAR_RELEASE" not in evidence[evidence_id]["claims"]:
                raise PortraitReviewError(
                    f"evidence {evidence_id} does not confirm a TW six-star release"
                )

    return copy.deepcopy(dict(root))


def build_portrait_review_queue(
    catalog: Mapping[str, Any],
    *,
    catalog_sha256: str,
    overrides: Mapping[str, Any] | None = None,
    override_registry_sha256: str | None = None,
) -> dict[str, Any]:
    _require_sha256(catalog_sha256, "catalog_sha256")
    assets, occurrences = _catalog_review_inputs(catalog)
    formation_shas = frozenset(occurrences)
    if overrides is None:
        if override_registry_sha256 is not None:
            raise PortraitReviewError(
                "override_registry_sha256 requires an override registry"
            )
        asset_overrides: Mapping[str, Any] = {}
    else:
        if override_registry_sha256 is None:
            raise PortraitReviewError(
                "an override registry requires override_registry_sha256 provenance"
            )
        _require_sha256(override_registry_sha256, "override_registry_sha256")
        validated = validate_override_registry(
            overrides,
            formation_sha256s=formation_shas,
            base_catalog_sha256=catalog_sha256,
        )
        asset_overrides = validated["assets"]

    state_counts = {PENDING: 0, REVIEWED_UNKNOWN: 0, CONFIRMED: 0}
    items: list[dict[str, Any]] = []
    for image_sha256 in sorted(formation_shas):
        override = asset_overrides.get(image_sha256)
        if isinstance(override, Mapping):
            review_state = override["review_status"]
            review_reason = override.get("reason")
            unit_key = override.get("unit_key")
        else:
            review_state = PENDING
            review_reason = None
            unit_key = None
        state_counts[review_state] += 1
        asset = assets[image_sha256]
        item_occurrences = sorted(
            occurrences[image_sha256],
            key=lambda value: (
                value["source_workbook_sha256"],
                value["sheet_name"],
                value["section_id"],
                value["team_source_id"],
                value["display_position"],
                value["anchor_cell"],
            ),
        )
        items.append(
            {
                "byte_length": asset["byte_length"],
                "filename": asset["filename"],
                "formation_occurrence_count": len(item_occurrences),
                "image_sha256": image_sha256,
                "mime_type": asset["mime_type"],
                "occurrences": item_occurrences,
                "review_reason": review_reason,
                "review_state": review_state,
                "unit_key": unit_key,
            }
        )
    items.sort(
        key=lambda item: (-item["formation_occurrence_count"], item["image_sha256"])
    )
    for review_order, item in enumerate(items, start=1):
        item["review_order"] = review_order

    return {
        "inputs": {
            "catalog_sha256": catalog_sha256,
            "override_registry_sha256": override_registry_sha256,
        },
        "items": items,
        "schema_version": REVIEW_QUEUE_SCHEMA_VERSION,
        "summary": {
            "formation_asset_count": len(items),
            "formation_occurrence_count": sum(
                item["formation_occurrence_count"] for item in items
            ),
            "state_counts": state_counts,
        },
    }


def materialize_character_catalog(
    base_catalog: Mapping[str, Any],
    mapping_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a mapped catalog without mutating the immutable base catalog."""

    _assets, occurrences = _catalog_review_inputs(base_catalog)
    manifest = _require_mapping(mapping_manifest, "character mapping manifest")
    _require_exact_fields(
        manifest,
        {"mappings", "schema_version", "summary"},
        "character mapping manifest",
    )
    if manifest["schema_version"] != MAPPING_SCHEMA_VERSION:
        raise PortraitReviewError("character mapping manifest schema is unsupported")
    raw_mappings = _require_list(manifest["mappings"], "character mapping mappings")
    mappings: dict[str, Mapping[str, Any]] = {}
    for index, raw_mapping in enumerate(raw_mappings):
        mapping = _require_mapping(raw_mapping, f"character mapping mappings[{index}]")
        required = {
            "candidate_base_ids",
            "display_rarity",
            "display_source",
            "estertion_base_id",
            "icon_id",
            "icon_url",
            "image_sha256",
            "mapping_reason",
            "mapping_status",
            "tw_name",
            "unit_key",
        }
        _require_exact_fields(mapping, required, f"character mapping mappings[{index}]")
        image_sha256 = _require_sha256(
            mapping["image_sha256"],
            f"character mapping mappings[{index}].image_sha256",
        )
        if image_sha256 in mappings:
            raise PortraitReviewError(f"duplicate character mapping: {image_sha256}")
        _validate_mapping_row(mapping, index)
        mappings[image_sha256] = mapping

    missing = set(occurrences) - set(mappings)
    if missing:
        raise PortraitReviewError(
            "character mapping manifest is missing formation assets: "
            + ", ".join(sorted(missing))
        )
    extra = set(mappings) - set(occurrences)
    if extra:
        raise PortraitReviewError(
            "character mapping manifest contains non-formation assets: "
            + ", ".join(sorted(extra))
        )

    result = copy.deepcopy(dict(base_catalog))
    for source in result["sources"]:
        for sheet in source["sheets"]:
            for section in sheet["sections"]:
                for team in section["teams"]:
                    for member in team["formation"]:
                        mapping = mappings[member["image_sha256"]]
                        member.update(
                            {
                                "display_rarity": mapping["display_rarity"],
                                "display_source": mapping["display_source"],
                                "estertion_base_id": mapping["estertion_base_id"],
                                "icon_id": mapping["icon_id"],
                                "mapping_reason": mapping["mapping_reason"],
                                "mapping_status": mapping["mapping_status"],
                                "tw_name": mapping["tw_name"],
                                "unit_key": mapping["unit_key"],
                            }
                        )
    return result


def verify_evidence_files(
    overrides: Mapping[str, Any],
    evidence_directory: str | Path,
) -> dict[str, str]:
    """Verify every pinned evidence snapshot by exact bytes, without network I/O."""

    directory = Path(evidence_directory)
    if not directory.is_dir() or directory.is_symlink():
        raise PortraitReviewError(
            f"evidence directory must be a real local directory: {directory}"
        )
    evidence = _require_mapping(overrides.get("evidence"), "overrides.evidence")
    verified: dict[str, str] = {}
    for evidence_id, raw_item in sorted(evidence.items()):
        item = _require_mapping(raw_item, f"overrides.evidence[{evidence_id!r}]")
        filename = _require_text(
            item.get("filename"),
            f"overrides.evidence[{evidence_id!r}].filename",
        )
        if Path(filename).name != filename or "/" in filename or "\\" in filename:
            raise PortraitReviewError(
                f"evidence {evidence_id} filename must be a basename"
            )
        source = directory / filename
        if source.is_symlink() or not source.is_file():
            raise PortraitReviewError(
                f"evidence snapshot is missing or is a symlink: {filename}"
            )
        try:
            payload = source.read_bytes()
            actual = hashlib.sha256(payload).hexdigest()
        except OSError as exc:
            raise PortraitReviewError(
                f"cannot read evidence snapshot: {filename}"
            ) from exc
        if actual != item["source_sha256"]:
            raise PortraitReviewError(
                f"evidence snapshot SHA-256 does not match registry: {filename}"
            )
        if item.get("kind") == "TW_OFFICIAL_NEWS_SNAPSHOT":
            try:
                snapshot_text = html.unescape(payload.decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise PortraitReviewError(
                    f"official news evidence snapshot must be UTF-8: {filename}"
                ) from exc
            tw_name = _require_text(
                item.get("tw_name"),
                f"overrides.evidence[{evidence_id!r}].tw_name",
            )
            if not _contains_exact_tw_name(snapshot_text, tw_name):
                raise PortraitReviewError(
                    f"official news evidence does not contain its exact TW name: {filename}"
                )
            claims = _require_list(
                item.get("claims"),
                f"overrides.evidence[{evidence_id!r}].claims",
            )
            direct_six_star = re.compile(
                rf"「\s*{re.escape(tw_name)}\s*」\s*的\s*★6\s*才能開花"
            )
            if (
                "TW_SIX_STAR_RELEASE" in claims
                and direct_six_star.search(snapshot_text) is None
                and not _contains_grouped_six_star_release(snapshot_text, tw_name)
                and not _contains_six_star_package_roster(snapshot_text, tw_name)
            ):
                raise PortraitReviewError(
                    f"official news evidence does not contain a direct six-star claim "
                    f"or a fail-closed official six-star roster: "
                    f"{filename}"
                )
        verified[evidence_id] = actual
    return verified


def _contains_exact_tw_name(snapshot_text: str, tw_name: str) -> bool:
    """Match one complete name in a known official-news text/list shape."""

    escaped = re.escape(tw_name)
    patterns = (
        rf"「\s*{escaped}\s*」",
        rf"「\s*{escaped}\s*的記憶碎片(?:[×xX]\s*[0-9]+)?\s*」",
        rf"■\s*{escaped}\s*(?:<br\s*/?>|\r?\n)",
        rf"[‧・]\s*{escaped}\s*<br\s*/?>",
        rf"<br\s*/?>\s*{escaped}\s*<br\s*/?>",
        rf"※\s*{escaped}\s*無法使用「\s*{escaped}的",
    )
    return any(re.search(pattern, snapshot_text) is not None for pattern in patterns)


_HTML_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_GROUPED_SIX_STAR_HEADING = "■能夠以★6才能開花之姿登場的角色"
_PACKAGE_PRODUCT_HEADING = "■商品名稱"
_PACKAGE_CONTENTS_HEADING = "■販售內容"
_PACKAGE_ROSTER_HEADING = "■關於「交換券的目標角色」"
_SIX_STAR_PACKAGE_NAME = "★6角色養成禮包"
_PURE_MEMORY_TICKET = "純淨記憶碎片交換券"
_PURE_MEMORY_ROSTER = "純淨記憶碎片的目標角色"


def _contains_grouped_six_star_release(
    snapshot_text: str,
    tw_name: str,
) -> bool:
    """Accept an exact character only from the official grouped release roster."""

    lines = _official_news_br_lines(snapshot_text)
    return _section_has_exact_list_item(
        lines,
        heading=_GROUPED_SIX_STAR_HEADING,
        tw_name=tw_name,
    )


def _contains_six_star_package_roster(
    snapshot_text: str,
    tw_name: str,
) -> bool:
    """Accept a package roster only when every availability signal is explicit."""

    title_match = re.search(
        r"<title(?:\s[^>]*)?>(.*?)</title\s*>",
        snapshot_text,
        re.IGNORECASE | re.DOTALL,
    )
    if title_match is None or _SIX_STAR_PACKAGE_NAME not in title_match.group(1):
        return False

    lines = _official_news_br_lines(snapshot_text)
    product_sections = _official_news_sections(lines, _PACKAGE_PRODUCT_HEADING)
    if not any(
        any(_SIX_STAR_PACKAGE_NAME in line for line in section)
        for section in product_sections
    ):
        return False

    contents_sections = _official_news_sections(lines, _PACKAGE_CONTENTS_HEADING)
    if not any(
        any(
            _is_list_item(line) and _PURE_MEMORY_TICKET in line
            for line in section
        )
        for section in contents_sections
    ):
        return False

    for section in _official_news_sections(lines, _PACKAGE_ROSTER_HEADING):
        has_pure_memory_roster_preamble = any(
            _PURE_MEMORY_TICKET in line and _PURE_MEMORY_ROSTER in line
            for line in section
        )
        if has_pure_memory_roster_preamble and _lines_have_exact_list_item(
            section,
            tw_name,
        ):
            return True
    return False


def _official_news_br_lines(snapshot_text: str) -> tuple[str, ...]:
    """Split only at explicit HTML line breaks used by pinned So-net snapshots."""

    return tuple(part.strip() for part in _HTML_BR.split(snapshot_text))


def _official_news_sections(
    lines: tuple[str, ...],
    heading: str,
) -> tuple[tuple[str, ...], ...]:
    """Return exact-heading sections, ending before the next official heading."""

    sections: list[tuple[str, ...]] = []
    for index, line in enumerate(lines):
        if line != heading:
            continue
        section: list[str] = []
        for candidate in lines[index + 1 :]:
            if candidate.startswith("■"):
                break
            section.append(candidate)
        sections.append(tuple(section))
    return tuple(sections)


def _section_has_exact_list_item(
    lines: tuple[str, ...],
    *,
    heading: str,
    tw_name: str,
) -> bool:
    return any(
        _lines_have_exact_list_item(section, tw_name)
        for section in _official_news_sections(lines, heading)
    )


def _lines_have_exact_list_item(lines: tuple[str, ...], tw_name: str) -> bool:
    exact_item = re.compile(rf"[‧・]\s*{re.escape(tw_name)}")
    return any(exact_item.fullmatch(line) is not None for line in lines)


def _is_list_item(line: str) -> bool:
    return re.match(r"[‧・]", line) is not None


def build_materialization_manifest(
    *,
    base_catalog_sha256: str,
    override_registry_sha256: str,
    estertion_index_sha256: str,
    overrides: Mapping[str, Any],
    verified_evidence_sha256s: Mapping[str, str],
    mapping_manifest: Mapping[str, Any],
    mapped_catalog: Mapping[str, Any],
) -> dict[str, Any]:
    for field, value in (
        ("base_catalog_sha256", base_catalog_sha256),
        ("override_registry_sha256", override_registry_sha256),
        ("estertion_index_sha256", estertion_index_sha256),
    ):
        _require_sha256(value, field)
    evidence = _require_mapping(overrides.get("evidence"), "overrides.evidence")
    expected_evidence_sources = {
        evidence_id: item["source_sha256"]
        for evidence_id, item in sorted(evidence.items())
    }
    evidence_sources = dict(sorted(verified_evidence_sha256s.items()))
    if evidence_sources != expected_evidence_sources:
        raise PortraitReviewError(
            "verified evidence SHA-256 values do not close over the override registry"
        )
    mapping_bytes = canonical_json_bytes(mapping_manifest)
    catalog_bytes = canonical_json_bytes(mapped_catalog)
    summary = _require_mapping(mapping_manifest.get("summary"), "mapping summary")
    return {
        "inputs": {
            "base_catalog_sha256": base_catalog_sha256,
            "estertion_index_sha256": estertion_index_sha256,
            "evidence_source_sha256s": evidence_sources,
            "override_registry_sha256": override_registry_sha256,
        },
        "outputs": {
            "character_mapping_sha256": hashlib.sha256(mapping_bytes).hexdigest(),
            "mapped_catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
        },
        "schema_version": MATERIALIZATION_SCHEMA_VERSION,
        "summary": copy.deepcopy(dict(summary)),
    }


def _catalog_review_inputs(
    catalog: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, list[dict[str, Any]]]]:
    root = _require_mapping(catalog, "catalog")
    _require_exact_fields(root, _CATALOG_ROOT_FIELDS, "catalog")
    if root["schema_version"] != LOCAL_CATALOG_SCHEMA_VERSION:
        raise PortraitReviewError("catalog has an unsupported schema_version")

    raw_assets = _require_list(root["assets"], "catalog.assets")
    assets: dict[str, Mapping[str, Any]] = {}
    for index, raw_asset in enumerate(raw_assets):
        asset = _require_mapping(raw_asset, f"catalog.assets[{index}]")
        _require_exact_fields(asset, _CATALOG_ASSET_FIELDS, f"catalog.assets[{index}]")
        image_sha256 = _require_sha256(
            asset["sha256"],
            f"catalog.assets[{index}].sha256",
        )
        if image_sha256 in assets:
            raise PortraitReviewError(f"catalog contains duplicate asset: {image_sha256}")
        filename = _require_text(asset["filename"], f"catalog.assets[{index}].filename")
        extension = _require_text(
            asset["file_extension"],
            f"catalog.assets[{index}].file_extension",
        )
        if filename != f"{image_sha256}.{extension}" or Path(filename).name != filename:
            raise PortraitReviewError(f"catalog asset has a non-canonical filename: {filename}")
        _require_text(asset["mime_type"], f"catalog.assets[{index}].mime_type")
        if _require_int(asset["byte_length"], f"catalog.assets[{index}].byte_length") < 1:
            raise PortraitReviewError("catalog asset byte_length must be positive")
        assets[image_sha256] = asset

    occurrences: dict[str, list[dict[str, Any]]] = {}
    sources = _require_list(root["sources"], "catalog.sources")
    for source_index, raw_source in enumerate(sources):
        source = _require_mapping(raw_source, f"catalog.sources[{source_index}]")
        workbook = _require_mapping(
            source.get("source_workbook"),
            f"catalog.sources[{source_index}].source_workbook",
        )
        workbook_sha256 = _require_sha256(
            workbook.get("sha256"),
            f"catalog.sources[{source_index}].source_workbook.sha256",
        )
        sheets = _require_list(
            source.get("sheets"),
            f"catalog.sources[{source_index}].sheets",
        )
        for sheet_index, raw_sheet in enumerate(sheets):
            sheet = _require_mapping(
                raw_sheet,
                f"catalog.sources[{source_index}].sheets[{sheet_index}]",
            )
            sheet_name = _require_text(
                sheet.get("sheet_name"),
                f"catalog.sources[{source_index}].sheets[{sheet_index}].sheet_name",
            )
            sections = _require_list(
                sheet.get("sections"),
                f"catalog sheet {sheet_name}.sections",
            )
            for section_index, raw_section in enumerate(sections):
                section = _require_mapping(
                    raw_section,
                    f"catalog sheet {sheet_name}.sections[{section_index}]",
                )
                section_id = _require_text(
                    section.get("section_id"),
                    f"catalog sheet {sheet_name}.sections[{section_index}].section_id",
                )
                teams = _require_list(
                    section.get("teams"),
                    f"catalog section {section_id}.teams",
                )
                for team_index, raw_team in enumerate(teams):
                    team = _require_mapping(
                        raw_team,
                        f"catalog section {section_id}.teams[{team_index}]",
                    )
                    team_id = _require_text(
                        team.get("team_source_id"),
                        f"catalog section {section_id}.teams[{team_index}].team_source_id",
                    )
                    formation = _require_list(
                        team.get("formation"),
                        f"catalog team {team_id}.formation",
                    )
                    if len(formation) != 5:
                        raise PortraitReviewError(
                            f"catalog team {team_id} must have exactly five portraits"
                        )
                    positions: list[int] = []
                    for member_index, raw_member in enumerate(formation):
                        member = _require_mapping(
                            raw_member,
                            f"catalog team {team_id}.formation[{member_index}]",
                        )
                        position = _require_int(
                            member.get("display_position"),
                            f"catalog team {team_id}.formation[{member_index}].display_position",
                        )
                        positions.append(position)
                        image_sha256 = _require_sha256(
                            member.get("image_sha256"),
                            f"catalog team {team_id}.formation[{member_index}].image_sha256",
                        )
                        if image_sha256 not in assets:
                            raise PortraitReviewError(
                                f"catalog team {team_id} references an undeclared asset"
                            )
                        anchor_cell = _require_text(
                            member.get("anchor_cell"),
                            f"catalog team {team_id}.formation[{member_index}].anchor_cell",
                        )
                        occurrences.setdefault(image_sha256, []).append(
                            {
                                "anchor_cell": anchor_cell,
                                "display_position": position,
                                "section_id": section_id,
                                "sheet_name": sheet_name,
                                "source_workbook_sha256": workbook_sha256,
                                "team_source_id": team_id,
                            }
                        )
                    if positions != [1, 2, 3, 4, 5]:
                        raise PortraitReviewError(
                            f"catalog team {team_id} portrait positions must be exactly 1..5"
                        )
    return assets, occurrences


def _validate_mapping_row(mapping: Mapping[str, Any], index: int) -> None:
    path = f"character mapping mappings[{index}]"
    status = mapping["mapping_status"]
    if status not in {"AMBIGUOUS", "RESOLVED", "REVIEWED_UNKNOWN", "UNRESOLVED"}:
        raise PortraitReviewError(f"{path}.mapping_status is unsupported")
    _require_text(mapping["mapping_reason"], f"{path}.mapping_reason")
    for field in ("unit_key", "tw_name", "estertion_base_id", "icon_id"):
        value = mapping[field]
        if value is not None:
            _require_text(value, f"{path}.{field}")
    if mapping["icon_id"] is not None and not _ICON_ID.fullmatch(mapping["icon_id"]):
        raise PortraitReviewError(f"{path}.icon_id must be six digits")
    if mapping["display_source"] not in {"ESTERTION", "WORKBOOK_EMBEDDED"}:
        raise PortraitReviewError(f"{path}.display_source is unsupported")
    if mapping["display_rarity"] not in {None, "THREE_STAR", "SIX_STAR"}:
        raise PortraitReviewError(f"{path}.display_rarity is unsupported")
    if mapping["display_source"] == "ESTERTION":
        if (
            status != "RESOLVED"
            or mapping["icon_id"] is None
            or mapping["estertion_base_id"] is None
            or mapping["unit_key"] is None
            or mapping["tw_name"] is None
        ):
            raise PortraitReviewError(f"{path} has inconsistent external icon metadata")
        expected_suffix = "61" if mapping["display_rarity"] == "SIX_STAR" else "31"
        if (
            mapping["icon_id"][:4] != mapping["estertion_base_id"]
            or not mapping["icon_id"].endswith(expected_suffix)
        ):
            raise PortraitReviewError(f"{path} icon does not match exact base and rarity")
        expected_url = (
            "https://redive.estertion.win/icon/unit/"
            + mapping["icon_id"]
            + ".webp"
        )
        if mapping["icon_url"] != expected_url:
            raise PortraitReviewError(
                f"{path}.icon_url is not the derived fixed origin URL"
            )
    elif (
        mapping["icon_id"] is not None
        or mapping["icon_url"] is not None
        or mapping["display_rarity"] is not None
    ):
        raise PortraitReviewError(f"{path} embedded fallback must not select a rarity")
    if mapping["icon_url"] is not None:
        _require_text(mapping["icon_url"], f"{path}.icon_url")
    candidates = _require_list(mapping["candidate_base_ids"], f"{path}.candidate_base_ids")
    if not all(isinstance(value, str) and re.fullmatch(r"[0-9]{4}", value) for value in candidates):
        raise PortraitReviewError(f"{path}.candidate_base_ids is invalid")


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PortraitReviewError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise PortraitReviewError(f"non-finite JSON number is not allowed: {value}")


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PortraitReviewError(f"{path} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise PortraitReviewError(f"{path} keys must be strings")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise PortraitReviewError(f"{path} must be a list")
    return value


def _require_exact_fields(value: Mapping[str, Any], fields: set[str], path: str) -> None:
    if set(value) != fields:
        raise PortraitReviewError(f"{path} has unsupported fields")


def _require_fields(
    value: Mapping[str, Any],
    *,
    required: set[str],
    optional: set[str],
    path: str,
) -> None:
    if not required.issubset(value) or not set(value).issubset(required | optional):
        raise PortraitReviewError(f"{path} has unsupported or missing fields")


def _require_sha256(value: Any, path: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise PortraitReviewError(f"{path} must be a lowercase SHA-256 digest")
    return value


def _require_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise PortraitReviewError(f"{path} must be non-empty trimmed text")
    return value


def _require_int(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise PortraitReviewError(f"{path} must be an integer")
    return value


def _require_unit_key(value: Any, path: str) -> str:
    if not isinstance(value, str) or _UNIT_KEY.fullmatch(value) is None:
        raise PortraitReviewError(f"{path} must contain a canonical unit_key")
    return value


def _validate_optional_note(value: Mapping[str, Any], path: str) -> None:
    if "note" in value:
        note = _require_text(value["note"], f"{path}.note")
        if len(note) > 1000:
            raise PortraitReviewError(f"{path}.note is too long")
