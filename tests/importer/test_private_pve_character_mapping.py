from __future__ import annotations

from pcr_pipeline.xlsx_ingest.character_mapping import (
    AMBIGUOUS,
    REVIEWED_UNKNOWN,
    RESOLVED,
    UNRESOLVED,
    map_catalog_characters,
    resolve_character_mapping,
)
from pcr_pipeline.xlsx_ingest.estertion_index import parse_estertion_index


SNAPSHOT = r"""
<span class="item" data-search="100131.webp"></span>
<span class="item" data-search="100161.webp"></span>
<span class="item" data-search="100131_20230411_2211.webp"></span>
<span class="item" data-search="138831.webp"></span>
<span class="item" data-search="132831.webp"></span>
<span class="item" data-search="134231.webp"></span>
<span class="item" data-search="999961.webp"></span>
<script>
names={"100131":"ヒヨリ","138831":"シオリ（ウィンター）","132831":"ライラエル（クリスマス）","134231":"ライラエル（クリスマス）","999961":"フィクスチャ"};
Object.keys(names).forEach(function (i) {});
</script>
"""


def _confirmed(unit_key: str, base_id: str | None = None) -> dict[str, str]:
    override = {
        "unit_key": unit_key,
        "identity_status": "USER_CONFIRMED",
        "review_status": "CONFIRMED",
    }
    if base_id is not None:
        override["estertion_base_id"] = base_id
    return override


def test_resolver_requires_explicit_confirmed_asset_review() -> None:
    override = _confirmed("hiyori_orig", "1001")
    override.pop("review_status")
    mapping = resolve_character_mapping(
        image_sha256="0" * 64,
        asset_override=override,
        unit_override=_unit(
            "hiyori_orig",
            tw_unit_id=100101,
            tw_name="日和",
            jp_name="ヒヨリ",
        ),
        index=parse_estertion_index(SNAPSHOT),
        evidence_overrides=_evidence("hiyori_orig"),
    )

    assert mapping.mapping_status == UNRESOLVED
    assert mapping.mapping_reason == "INVALID_ASSET_REVIEW_STATUS"


def test_resolver_rejects_icon_id_masquerading_as_tw_unit_id() -> None:
    mapping = resolve_character_mapping(
        image_sha256="2" * 64,
        asset_override=_confirmed("hiyori_orig", "1001"),
        unit_override=_unit(
            "hiyori_orig",
            tw_unit_id=100161,
            tw_name="日和",
            jp_name="ヒヨリ",
        ),
        index=parse_estertion_index(SNAPSHOT),
        evidence_overrides=_evidence("hiyori_orig"),
    )

    assert mapping.mapping_status == UNRESOLVED
    assert mapping.mapping_reason == "EXACT_VARIANT_ID_MISMATCH"


def test_resolver_rejects_unparsed_database_evidence_kind() -> None:
    evidence = _evidence("hiyori_orig")
    evidence["identity"]["kind"] = "TW_OFFICIAL_DATABASE_SNAPSHOT"
    mapping = resolve_character_mapping(
        image_sha256="3" * 64,
        asset_override=_confirmed("hiyori_orig", "1001"),
        unit_override=_unit(
            "hiyori_orig",
            tw_unit_id=100101,
            tw_name="日和",
            jp_name="ヒヨリ",
            six_star_tw_status="AVAILABLE",
        ),
        index=parse_estertion_index(SNAPSHOT),
        evidence_overrides=evidence,
    )

    assert mapping.mapping_status == UNRESOLVED
    assert mapping.mapping_reason == "OFFICIAL_TW_IDENTITY_EVIDENCE_NOT_CONFIRMED"


def _evidence(unit_key: str, *, key: str = "identity") -> dict[str, dict[str, str]]:
    return {
        key: {
            "claims": ["TW_UNIT_IDENTITY", "TW_SIX_STAR_RELEASE"],
            "kind": "TW_OFFICIAL_NEWS_SNAPSHOT",
            "locator": f"article:{key}",
            "review_status": "USER_CONFIRMED",
            "source_sha256": "7" * 64,
            "unit_key": unit_key,
        }
    }


def _unit(
    unit_key: str,
    *,
    tw_unit_id: int,
    tw_name: str,
    jp_name: str | None = None,
    six_star_tw_status: str = "UNVERIFIED",
    evidence_key: str = "identity",
) -> dict[str, object]:
    unit: dict[str, object] = {
        "exact_variant_status": "USER_CONFIRMED",
        "identity_evidence_ids": [evidence_key],
        "six_star_evidence_ids": (
            [evidence_key] if six_star_tw_status == "AVAILABLE" else []
        ),
        "six_star_tw_status": six_star_tw_status,
        "tw_name": tw_name,
        "tw_unit_id": tw_unit_id,
    }
    if jp_name is not None:
        unit["estertion_jp_name"] = jp_name
    return unit


def test_index_parses_only_current_exact_six_digit_ids_and_names() -> None:
    index = parse_estertion_index(SNAPSHOT)

    assert "100131" in index.icon_ids
    assert "100161" in index.icon_ids
    assert "100131_20230411_2211" not in index.icon_ids
    assert index.bases_for_name("ヒヨリ") == ("1001",)
    assert index.icon_id("1001", 6) == "100161"
    assert index.icon_url("100161") == (
        "https://redive.estertion.win/icon/unit/100161.webp"
    )


def test_six_star_requires_exact_base_tw_available_and_user_confirmation() -> None:
    index = parse_estertion_index(SNAPSHOT)

    six_star = resolve_character_mapping(
        image_sha256="a" * 64,
        asset_override=_confirmed("hiyori_orig", "1001"),
        unit_override=_unit(
            "hiyori_orig",
            tw_unit_id=100101,
            tw_name="日和",
            jp_name="ヒヨリ",
            six_star_tw_status="AVAILABLE",
        ),
        index=index,
        evidence_overrides=_evidence("hiyori_orig"),
    )
    unverified = resolve_character_mapping(
        image_sha256="b" * 64,
        asset_override=_confirmed("hiyori_orig", "1001"),
        unit_override=_unit(
            "hiyori_orig",
            tw_unit_id=100101,
            tw_name="日和",
            jp_name="ヒヨリ",
        ),
        index=index,
        evidence_overrides=_evidence("hiyori_orig"),
    )
    unconfirmed = resolve_character_mapping(
        image_sha256="c" * 64,
        asset_override={
            "unit_key": "hiyori_orig",
            "identity_status": "INFERRED",
            "estertion_base_id": "1001",
        },
        unit_override=_unit(
            "hiyori_orig",
            tw_unit_id=100101,
            tw_name="日和",
            jp_name="ヒヨリ",
            six_star_tw_status="AVAILABLE",
        ),
        index=index,
        evidence_overrides=_evidence("hiyori_orig"),
    )

    assert six_star.mapping_status == RESOLVED
    assert six_star.icon_id == "100161"
    assert six_star.display_rarity == "SIX_STAR"
    assert unverified.icon_id == "100131"
    assert unverified.display_rarity == "THREE_STAR"
    assert unconfirmed.mapping_status == UNRESOLVED
    assert unconfirmed.display_source == "WORKBOOK_EMBEDDED"


def test_missing_exact_six_star_falls_back_to_same_variant_three_star() -> None:
    mapping = resolve_character_mapping(
        image_sha256="d" * 64,
        asset_override=_confirmed("shiori_win", "1388"),
        unit_override=_unit(
            "shiori_win",
            tw_unit_id=138801,
            tw_name="栞（冬日）",
            jp_name="シオリ（ウィンター）",
            six_star_tw_status="AVAILABLE",
        ),
        index=parse_estertion_index(SNAPSHOT),
        evidence_overrides=_evidence("shiori_win"),
    )

    assert mapping.mapping_status == RESOLVED
    assert mapping.icon_id == "138831"
    assert mapping.display_rarity == "THREE_STAR"


def test_six_star_never_bypasses_missing_same_variant_three_star() -> None:
    mapping = resolve_character_mapping(
        image_sha256="9" * 64,
        asset_override=_confirmed("fixture_only_six", "9999"),
        unit_override=_unit(
            "fixture_only_six",
            tw_unit_id=999901,
            tw_name="測試角色",
            jp_name="フィクスチャ",
            six_star_tw_status="AVAILABLE",
        ),
        index=parse_estertion_index(SNAPSHOT),
        evidence_overrides=_evidence("fixture_only_six"),
    )

    assert mapping.mapping_status == RESOLVED
    assert mapping.mapping_reason == "THREE_STAR_ICON_MISSING"
    assert mapping.icon_id is None
    assert mapping.display_source == "WORKBOOK_EMBEDDED"


def test_duplicate_name_is_ambiguous_until_exact_base_is_explicit() -> None:
    index = parse_estertion_index(SNAPSHOT)
    unit = _unit(
        "lailael_xmas",
        tw_unit_id=134201,
        tw_name="萊拉耶爾（聖誕節）",
        jp_name="ライラエル（クリスマス）",
    )
    evidence = _evidence("lailael_xmas")

    ambiguous = resolve_character_mapping(
        image_sha256="e" * 64,
        asset_override=_confirmed("lailael_xmas"),
        unit_override=unit,
        index=index,
        evidence_overrides=evidence,
    )
    exact = resolve_character_mapping(
        image_sha256="f" * 64,
        asset_override=_confirmed("lailael_xmas", "1342"),
        unit_override=unit,
        index=index,
        evidence_overrides=evidence,
    )

    assert ambiguous.mapping_status == AMBIGUOUS
    assert ambiguous.candidate_base_ids == ("1328", "1342")
    assert ambiguous.display_source == "WORKBOOK_EMBEDDED"
    assert exact.mapping_status == RESOLVED
    assert exact.icon_id == "134231"


def test_cross_variant_and_unknown_fail_closed_to_embedded_portrait() -> None:
    index = parse_estertion_index(SNAPSHOT)

    cross_variant = resolve_character_mapping(
        image_sha256="1" * 64,
        asset_override=_confirmed("shiori_win", "1001"),
        unit_override=_unit(
            "shiori_win",
            tw_unit_id=138801,
            tw_name="栞（冬日）",
            jp_name="シオリ（ウィンター）",
        ),
        index=index,
        evidence_overrides=_evidence("shiori_win"),
    )
    unknown = resolve_character_mapping(
        image_sha256="2" * 64,
        asset_override=None,
        unit_override=None,
        index=index,
    )

    assert cross_variant.mapping_status == UNRESOLVED
    assert cross_variant.mapping_reason == "CROSS_VARIANT_NAME_MISMATCH"
    assert cross_variant.icon_url is None
    assert unknown.mapping_status == UNRESOLVED
    assert unknown.mapping_reason == "NO_ASSET_OVERRIDE"
    assert unknown.display_source == "WORKBOOK_EMBEDDED"


def test_explicit_base_cannot_bypass_missing_exact_estertion_name() -> None:
    mapping = resolve_character_mapping(
        image_sha256="8" * 64,
        asset_override=_confirmed("hiyori_orig", "1001"),
        unit_override=_unit(
            "hiyori_orig",
            tw_unit_id=100101,
            tw_name="日和",
            jp_name="不存在於索引的名稱",
        ),
        index=parse_estertion_index(SNAPSHOT),
        evidence_overrides=_evidence("hiyori_orig"),
    )

    assert mapping.mapping_status == UNRESOLVED
    assert mapping.mapping_reason == "NO_EXACT_BASE_CANDIDATE"
    assert mapping.display_source == "WORKBOOK_EMBEDDED"


def test_catalog_manifest_is_deterministic_and_counts_statuses() -> None:
    catalog = {
        "assets": [
            {"sha256": "b" * 64},
            {"sha256": "a" * 64},
            {"sha256": "c" * 64},
        ]
    }
    overrides = {
        "assets": {
            "a" * 64: _confirmed("hiyori_orig", "1001"),
            "b" * 64: _confirmed("lailael_xmas"),
        },
        "units": {
            "hiyori_orig": {
                **_unit(
                    "hiyori_orig",
                    tw_unit_id=100101,
                    tw_name="日和",
                    jp_name="ヒヨリ",
                    six_star_tw_status="AVAILABLE",
                    evidence_key="hiyori",
                ),
            },
            "lailael_xmas": {
                **_unit(
                    "lailael_xmas",
                    tw_unit_id=134201,
                    tw_name="萊拉耶爾（聖誕節）",
                    jp_name="ライラエル（クリスマス）",
                    evidence_key="lailael",
                ),
            },
        },
        "evidence": {
            **_evidence("hiyori_orig", key="hiyori"),
            **_evidence("lailael_xmas", key="lailael"),
        },
    }

    manifest = map_catalog_characters(
        catalog,
        overrides,
        parse_estertion_index(SNAPSHOT),
    )

    assert [row["image_sha256"] for row in manifest["mappings"]] == [
        "a" * 64,
        "b" * 64,
        "c" * 64,
    ]
    assert manifest["summary"]["mapping_counts"] == {
        RESOLVED: 1,
        REVIEWED_UNKNOWN: 0,
        AMBIGUOUS: 1,
        UNRESOLVED: 1,
    }
