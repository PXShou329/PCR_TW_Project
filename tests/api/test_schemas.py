from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from pcr_api.schemas import (
    ArenaSourceRecordData,
    GachaCommunitySourceData,
    GachaTimelineEventData,
    ResponseMeta,
    SourceMeta,
)


VALID_SOURCE = {
    "canonical_source": "research_core_file_ssot",
    "fixture_sha256": "a" * 64,
    "import_run_id": "00000000-0000-4000-8000-000000000001",
    "revision_id": "a" * 64,
    "imported_at": "2026-08-08T00:00:00Z",
    "research_core_version": "v1.5",
    "raw_tree_sha256": "a" * 64,
    "semantic_tree_sha256": "b" * 64,
    "materialization_sha256": "c" * 64,
}


def test_source_meta_requires_uuid_and_lowercase_sha256_provenance() -> None:
    source = SourceMeta.model_validate(VALID_SOURCE)
    assert str(source.import_run_id) == VALID_SOURCE["import_run_id"]

    for field, invalid in (
        ("fixture_sha256", "short"),
        ("revision_id", "A" * 64),
        ("raw_tree_sha256", "g" * 64),
        ("semantic_tree_sha256", "0" * 63),
        ("materialization_sha256", "0" * 65),
        ("import_run_id", "not-a-uuid"),
    ):
        payload = deepcopy(VALID_SOURCE)
        payload[field] = invalid
        with pytest.raises(ValidationError):
            SourceMeta.model_validate(payload)


def test_response_meta_requires_conservative_gate_d_fields() -> None:
    payload = {
        "api_version": "v1",
        "generated_at": "2026-08-09T00:00:00Z",
        "server": "UNKNOWN",
        "environment_version": "UNKNOWN",
        "verified_at": None,
        "stale_status": "UNKNOWN",
        "confidence": "UNKNOWN",
        "evidence_ids": [],
        "claim_ids": [],
        "data_revision": "a" * 64,
        "source": VALID_SOURCE,
        "warnings": [],
    }

    meta = ResponseMeta.model_validate(payload)
    assert meta.data_revision == VALID_SOURCE["revision_id"]
    assert meta.verified_at is None

    for field, invalid in (
        ("server", "CN"),
        ("stale_status", "FRESH_ENOUGH"),
        ("confidence", "Z"),
        ("data_revision", "short"),
    ):
        candidate = deepcopy(payload)
        candidate[field] = invalid
        with pytest.raises(ValidationError):
            ResponseMeta.model_validate(candidate)

    mismatched_revision = deepcopy(payload)
    mismatched_revision["data_revision"] = "d" * 64
    with pytest.raises(
        ValidationError,
        match="data_revision must equal source.revision_id",
    ):
        ResponseMeta.model_validate(mismatched_revision)


def test_gacha_community_confidence_cap_rejects_official_or_unknown_levels() -> None:
    payload = {
        "source_id": "GACHA-COMM-TEST",
        "title": "reviewed community timeline",
        "platform": "forum",
        "author": "author",
        "source_type": "FORUM_TIMELINE",
        "url": "https://forum.gamer.com.tw/example",
        "last_seen_update": "2026-08-09",
        "coverage_start": "2026-01",
        "coverage_end": "2026-12",
        "update_status": "CHECKED",
        "confidence_cap": "D",
        "usage": "timeline cross-check only",
        "last_checked": "2026-08-09",
        "notes": "never official evidence",
    }

    assert GachaCommunitySourceData.model_validate(payload).confidence_cap == "D"
    for invalid in ("A", "B", "UNKNOWN"):
        candidate = deepcopy(payload)
        candidate["confidence_cap"] = invalid
        with pytest.raises(ValidationError):
            GachaCommunitySourceData.model_validate(candidate)


def test_arena_source_response_confidence_cap_matches_file46() -> None:
    payload = {
        "source_id": "ARENA-SRC-TEST",
        "title": "reviewed Arena source",
        "platform": "forum",
        "source_type": "FORUM_THREAD",
        "server": "TW",
        "url": "https://forum.gamer.com.tw/example",
        "last_checked": "2026-08-09",
        "freshness_window": "90d",
        "access_status": "ACTIVE",
        "confidence_cap": "D",
        "extraction_method": "manual review",
        "notes": "community evidence only",
    }

    for allowed in ("C", "D", "E"):
        candidate = deepcopy(payload)
        candidate["confidence_cap"] = allowed
        assert ArenaSourceRecordData.model_validate(candidate).confidence_cap == allowed
    for invalid in ("A", "B", "UNKNOWN"):
        candidate = deepcopy(payload)
        candidate["confidence_cap"] = invalid
        with pytest.raises(ValidationError):
            ArenaSourceRecordData.model_validate(candidate)


def test_gacha_limited_status_requires_explicit_nullable_claim_provenance() -> None:
    payload = {
        "event_id": "JP_20260731_fubuki_summer",
        "source_server": "JP",
        "target_server": "TW",
        "jp_date": "2026-07-31",
        "model_estimate_start": "2026-11-30",
        "model_estimate_end": "2026-12-02",
        "tw_estimate_start": "2026-11-30",
        "tw_estimate_end": "2026-12-02",
        "forecast_method": "MODEL_ONLY",
        "confidence": "LOW",
        "character_name_jp": "フブキ（サマー）",
        "tw_name": None,
        "pool_type": "LIMITED",
        "limited_status": "YES",
        "limited_claim_id": "CLM-JP-FUBUKI-DATE",
        "arena_value": "NOT_EVALUATED",
        "p_arena_value": "NOT_EVALUATED",
        "pve_value": "NOT_EVALUATED",
        "clan_value": "NOT_EVALUATED",
        "future_upgrade": "UNKNOWN",
        "relative_priority": "NOT_EVALUATED",
        "anchor_track": "LIMITED",
        "anchor_count": 5,
        "forecast_basis": "canonical anchors",
        "last_verified": "2026-08-09",
        "status": "ACTIVE",
        "maturity": "RESEARCH",
        "last_review_due": "2026-08-31",
        "community_estimate_start": None,
        "community_estimate_end": None,
        "community_order_consensus": "",
        "community_source_count": 0,
        "community_last_checked": None,
        "community_disagreement": "",
        "forecast_notes": "",
        "evidence_ids": ["ev048"],
        "claim_ids": ["CLM-JP-FUBUKI-DATE"],
        "community_source_ids": [],
    }

    known = GachaTimelineEventData.model_validate(payload)
    assert known.limited_claim_id == "CLM-JP-FUBUKI-DATE"

    unknown_payload = deepcopy(payload)
    unknown_payload["limited_status"] = "UNKNOWN"
    unknown_payload["limited_claim_id"] = None
    assert GachaTimelineEventData.model_validate(unknown_payload).limited_claim_id is None

    missing = deepcopy(payload)
    missing.pop("limited_claim_id")
    with pytest.raises(ValidationError, match="limited_claim_id"):
        GachaTimelineEventData.model_validate(missing)

    for status, claim_id in (("YES", None), ("NO", None), ("UNKNOWN", "CLM-X")):
        invalid = deepcopy(payload)
        invalid["limited_status"] = status
        invalid["limited_claim_id"] = claim_id
        with pytest.raises(ValidationError, match="limited_claim_id"):
            GachaTimelineEventData.model_validate(invalid)
