from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .estertion_index import EsterTionIndex


RESOLVED = "RESOLVED"
AMBIGUOUS = "AMBIGUOUS"
UNRESOLVED = "UNRESOLVED"
REVIEWED_UNKNOWN = "REVIEWED_UNKNOWN"

USER_CONFIRMED = "USER_CONFIRMED"
SIX_STAR_AVAILABLE = "AVAILABLE"
CONFIRMED = "CONFIRMED"


@dataclass(frozen=True)
class CharacterMapping:
    image_sha256: str
    mapping_status: str
    mapping_reason: str
    unit_key: str | None
    tw_name: str | None
    estertion_base_id: str | None
    icon_id: str | None
    icon_url: str | None
    display_source: str
    display_rarity: str | None
    candidate_base_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["candidate_base_ids"] = list(self.candidate_base_ids)
        return result


def resolve_character_mapping(
    *,
    image_sha256: str,
    asset_override: Mapping[str, Any] | None,
    unit_override: Mapping[str, Any] | None,
    index: EsterTionIndex,
    evidence_overrides: Mapping[str, Any] | None = None,
) -> CharacterMapping:
    """Resolve one workbook portrait conservatively from local-only inputs."""

    if not asset_override:
        return _fallback(image_sha256, reason="NO_ASSET_OVERRIDE")

    review_status = _text(asset_override.get("review_status"))
    if review_status == REVIEWED_UNKNOWN:
        reviewed_reason = _text(asset_override.get("reason")) or "REVIEWED_UNKNOWN"
        return _fallback(
            image_sha256,
            reason=reviewed_reason,
            status=REVIEWED_UNKNOWN,
        )
    if review_status != CONFIRMED:
        return _fallback(image_sha256, reason="INVALID_ASSET_REVIEW_STATUS")

    unit_key = _text(asset_override.get("unit_key"))
    identity_status = _text(asset_override.get("identity_status"))
    if unit_key is None:
        return _fallback(image_sha256, reason="MISSING_UNIT_KEY")
    if identity_status != USER_CONFIRMED:
        return _fallback(
            image_sha256,
            reason="ASSET_IDENTITY_NOT_USER_CONFIRMED",
            unit_key=unit_key,
        )

    unit = unit_override or {}
    tw_name = _text(unit.get("tw_name"))
    if tw_name is None:
        return _fallback(
            image_sha256,
            reason="MISSING_OFFICIAL_TW_NAME",
            unit_key=unit_key,
        )
    if _text(unit.get("exact_variant_status")) != USER_CONFIRMED:
        return _fallback(
            image_sha256,
            reason="UNIT_VARIANT_NOT_USER_CONFIRMED",
            unit_key=unit_key,
            tw_name=tw_name,
        )
    if not _has_confirmed_unit_evidence(
        unit_key=unit_key,
        evidence_ids=unit.get("identity_evidence_ids"),
        evidence_overrides=evidence_overrides,
        expected_claim="TW_UNIT_IDENTITY",
    ):
        return _fallback(
            image_sha256,
            reason="OFFICIAL_TW_IDENTITY_EVIDENCE_NOT_CONFIRMED",
            unit_key=unit_key,
            tw_name=tw_name,
        )

    jp_name = _text(unit.get("estertion_jp_name")) or _text(unit.get("jp_name"))
    if jp_name is None:
        return _fallback(
            image_sha256,
            reason="MISSING_ESTERTION_JP_NAME",
            unit_key=unit_key,
            tw_name=tw_name,
        )
    explicit_base = _text(asset_override.get("estertion_base_id"))
    if explicit_base is None:
        explicit_base = _text(unit.get("estertion_base_id"))

    candidates = index.bases_for_name(jp_name)
    base_id, status, reason = _resolve_base(
        explicit_base=explicit_base,
        candidates=candidates,
        index=index,
    )
    if status != RESOLVED or base_id is None:
        return _fallback(
            image_sha256,
            reason=reason,
            status=status,
            unit_key=unit_key,
            tw_name=tw_name,
            base_id=explicit_base,
            candidates=candidates,
        )

    tw_unit_id = unit.get("tw_unit_id")
    if (
        not isinstance(tw_unit_id, int)
        or isinstance(tw_unit_id, bool)
        or tw_unit_id != int(f"{base_id}01")
    ):
        return _fallback(
            image_sha256,
            reason="EXACT_VARIANT_ID_MISMATCH",
            unit_key=unit_key,
            tw_name=tw_name,
            base_id=base_id,
            candidates=candidates,
        )

    default_icon_id = index.icon_id(base_id, 3)
    if default_icon_id is None:
        return CharacterMapping(
            image_sha256=image_sha256,
            mapping_status=RESOLVED,
            mapping_reason="THREE_STAR_ICON_MISSING",
            unit_key=unit_key,
            tw_name=tw_name,
            estertion_base_id=base_id,
            icon_id=None,
            icon_url=None,
            display_source="WORKBOOK_EMBEDDED",
            display_rarity=None,
            candidate_base_ids=candidates,
        )

    selected_icon_id = default_icon_id
    display_rarity = "THREE_STAR"
    mapping_reason = "EXACT_VARIANT"
    if _text(unit.get("six_star_tw_status")) == SIX_STAR_AVAILABLE:
        if _has_confirmed_six_star_evidence(
            unit_key=unit_key,
            unit=unit,
            evidence_overrides=evidence_overrides,
        ):
            six_star_icon_id = index.icon_id(base_id, 6)
            if six_star_icon_id is not None:
                selected_icon_id = six_star_icon_id
                display_rarity = "SIX_STAR"
            else:
                mapping_reason = "EXACT_SIX_STAR_ICON_MISSING"
        else:
            mapping_reason = "SIX_STAR_TW_EVIDENCE_NOT_CONFIRMED"

    return CharacterMapping(
        image_sha256=image_sha256,
        mapping_status=RESOLVED,
        mapping_reason=mapping_reason,
        unit_key=unit_key,
        tw_name=tw_name,
        estertion_base_id=base_id,
        icon_id=selected_icon_id,
        icon_url=index.icon_url(selected_icon_id),
        display_source="ESTERTION",
        display_rarity=display_rarity,
        candidate_base_ids=candidates,
    )


def map_catalog_characters(
    catalog: Mapping[str, Any],
    overrides: Mapping[str, Any],
    index: EsterTionIndex,
    asset_sha256s: frozenset[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Build a deterministic derived mapping manifest for catalog assets."""

    asset_overrides = _mapping(overrides.get("assets"))
    unit_overrides = _mapping(overrides.get("units"))
    evidence_overrides = _mapping(overrides.get("evidence"))
    raw_assets = catalog.get("assets", [])
    assets = raw_assets if isinstance(raw_assets, list) else []

    mappings: list[dict[str, Any]] = []
    for asset in assets:
        if not isinstance(asset, Mapping):
            continue
        image_sha256 = _text(asset.get("sha256"))
        if image_sha256 is None:
            continue
        if asset_sha256s is not None and image_sha256 not in asset_sha256s:
            continue
        asset_override = _mapping_or_none(asset_overrides.get(image_sha256))
        unit_key = (
            _text(asset_override.get("unit_key"))
            if asset_override is not None
            else None
        )
        unit_override = _mapping_or_none(unit_overrides.get(unit_key or ""))
        mappings.append(
            resolve_character_mapping(
                image_sha256=image_sha256,
                asset_override=asset_override,
                unit_override=unit_override,
                index=index,
                evidence_overrides=evidence_overrides,
            ).to_dict()
        )

    mappings.sort(key=lambda row: row["image_sha256"])
    counts = {
        status: 0
        for status in (RESOLVED, REVIEWED_UNKNOWN, AMBIGUOUS, UNRESOLVED)
    }
    for mapping in mappings:
        counts[mapping["mapping_status"]] += 1

    return {
        "schema_version": "private-pve-character-mapping/v1",
        "mappings": mappings,
        "summary": {
            "asset_count": len(mappings),
            "mapping_counts": counts,
        },
    }


def _resolve_base(
    *,
    explicit_base: str | None,
    candidates: tuple[str, ...],
    index: EsterTionIndex,
) -> tuple[str | None, str, str]:
    if explicit_base is not None:
        if len(explicit_base) != 4 or not explicit_base.isascii() or not explicit_base.isdigit():
            return None, UNRESOLVED, "INVALID_EXPLICIT_BASE_ID"
        if not index.has_base(explicit_base):
            return None, UNRESOLVED, "EXPLICIT_BASE_NOT_IN_INDEX"
        if not candidates:
            return None, UNRESOLVED, "NO_EXACT_BASE_CANDIDATE"
        if explicit_base not in candidates:
            return None, UNRESOLVED, "CROSS_VARIANT_NAME_MISMATCH"
        return explicit_base, RESOLVED, "EXPLICIT_EXACT_BASE"

    if len(candidates) > 1:
        return None, AMBIGUOUS, "EXACT_NAME_HAS_MULTIPLE_BASES"
    if len(candidates) == 1:
        return candidates[0], RESOLVED, "UNIQUE_EXACT_NAME"
    return None, UNRESOLVED, "NO_EXACT_BASE_CANDIDATE"


def _fallback(
    image_sha256: str,
    *,
    reason: str,
    status: str = UNRESOLVED,
    unit_key: str | None = None,
    tw_name: str | None = None,
    base_id: str | None = None,
    candidates: tuple[str, ...] = (),
) -> CharacterMapping:
    return CharacterMapping(
        image_sha256=image_sha256,
        mapping_status=status,
        mapping_reason=reason,
        unit_key=unit_key,
        tw_name=tw_name,
        estertion_base_id=base_id,
        icon_id=None,
        icon_url=None,
        display_source="WORKBOOK_EMBEDDED",
        display_rarity=None,
        candidate_base_ids=candidates,
    )


def _has_confirmed_six_star_evidence(
    *,
    unit_key: str,
    unit: Mapping[str, Any],
    evidence_overrides: Mapping[str, Any] | None,
) -> bool:
    return _has_confirmed_unit_evidence(
        unit_key=unit_key,
        evidence_ids=unit.get("six_star_evidence_ids"),
        evidence_overrides=evidence_overrides,
        expected_claim="TW_SIX_STAR_RELEASE",
    )


def _has_confirmed_unit_evidence(
    *,
    unit_key: str,
    evidence_ids: Any,
    evidence_overrides: Mapping[str, Any] | None,
    expected_claim: str,
) -> bool:
    if not isinstance(evidence_ids, list) or not evidence_ids:
        return False
    if not isinstance(evidence_overrides, Mapping):
        return False

    for evidence_id in evidence_ids:
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            return False
        evidence = evidence_overrides.get(evidence_id)
        if not isinstance(evidence, Mapping):
            return False
        if _text(evidence.get("unit_key")) != unit_key:
            return False
        if _text(evidence.get("review_status")) != USER_CONFIRMED:
            return False
        claims = evidence.get("claims")
        if not isinstance(claims, list) or expected_claim not in claims:
            return False
        if _text(evidence.get("kind")) != "TW_OFFICIAL_NEWS_SNAPSHOT":
            return False
        source_sha256 = _text(evidence.get("source_sha256"))
        if (
            source_sha256 is None
            or len(source_sha256) != 64
            or not source_sha256.isascii()
            or any(character not in "0123456789abcdef" for character in source_sha256)
        ):
            return False
        if _text(evidence.get("locator")) is None:
            return False
    return True


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_or_none(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None
