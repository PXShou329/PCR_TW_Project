from __future__ import annotations

import copy
import hashlib
import json

import pytest

from pcr_pipeline.private_pve.character_mapping import map_catalog_characters
from pcr_pipeline.private_pve.cli import main
from pcr_pipeline.private_pve.estertion_index import parse_estertion_index
from pcr_pipeline.private_pve.portrait_review import (
    CONFIRMED,
    PENDING,
    REVIEWED_UNKNOWN,
    PortraitReviewError,
    build_materialization_manifest,
    build_portrait_review_queue,
    canonical_json_bytes,
    formation_asset_sha256s,
    load_strict_json,
    materialize_character_catalog,
    validate_override_registry,
    verify_evidence_files,
)


ASSET_A = "a" * 64
ASSET_B = "b" * 64
WORKBOOK_SHA = "c" * 64
IDENTITY_BYTES = "official identity 「日和」 snapshot".encode()
SIX_STAR_BYTES = "official 「日和」的★6才能開花 snapshot".encode()
INDEX_SNAPSHOT = r"""
<span class="item" data-search="100131.webp"></span>
<span class="item" data-search="100161.webp"></span>
<script>
names={"100131":"ヒヨリ","100161":"ヒヨリ"};
Object.keys(names).forEach(function (i) {});
</script>
"""


def _asset(sha256: str) -> dict[str, object]:
    return {
        "byte_length": 123,
        "file_extension": "png",
        "filename": f"{sha256}.png",
        "height_px": 112,
        "mime_type": "image/png",
        "occurrences": [],
        "sha256": sha256,
        "width_px": 112,
    }


def _formation(shas: list[str], *, row: int) -> list[dict[str, object]]:
    return [
        {
            "anchor_cell": f"{chr(64 + position)}{row}",
            "display_position": position,
            "image_sha256": sha256,
            "mapping_status": "UNMAPPED",
            "unit_key": None,
        }
        for position, sha256 in enumerate(shas, start=1)
    ]


def _catalog() -> dict[str, object]:
    return {
        "assets": [_asset(ASSET_B), _asset(ASSET_A)],
        "builder": {"name": "pcr-private-pve-catalog", "version": "1.0.0"},
        "schema_version": "private-pve-local-catalog/v1",
        "sources": [
            {
                "sheets": [
                    {
                        "sections": [
                            {
                                "section_id": "deep:fire:01-01",
                                "teams": [
                                    {
                                        "formation": _formation([ASSET_A] * 5, row=1),
                                        "team_source_id": "team:1",
                                    },
                                    {
                                        "formation": _formation(
                                            [ASSET_A, ASSET_B, ASSET_B, ASSET_B, ASSET_B],
                                            row=2,
                                        ),
                                        "team_source_id": "team:2",
                                    },
                                ],
                            }
                        ],
                        "sheet_name": "火",
                    }
                ],
                "source_workbook": {
                    "byte_length": 999,
                    "filename": "source.xlsx",
                    "sha256": WORKBOOK_SHA,
                },
            }
        ],
        "summary": {
            "asset_count": 2,
            "axis_count": 0,
            "section_count": 1,
            "team_count": 2,
        },
    }


def _evidence_item(
    *,
    filename: str,
    payload: bytes,
    locator: str,
    claim: str,
) -> dict[str, object]:
    return {
        "claims": [claim],
        "filename": filename,
        "kind": "TW_OFFICIAL_NEWS_SNAPSHOT",
        "locator": locator,
        "review_status": "USER_CONFIRMED",
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "tw_name": "日和",
        "unit_key": "hiyori_orig",
    }


def _overrides(catalog_sha256: str) -> dict[str, object]:
    return {
        "assets": {
            ASSET_A: {
                "identity_status": "USER_CONFIRMED",
                "review_status": "CONFIRMED",
                "unit_key": "hiyori_orig",
            },
            ASSET_B: {
                "reason": "NOT_IDENTIFIED",
                "review_status": "REVIEWED_UNKNOWN",
            },
        },
        "base_catalog_sha256": catalog_sha256,
        "evidence": {
            "hiyori-identity": _evidence_item(
                filename="identity.html",
                payload=IDENTITY_BYTES,
                locator="article:character-name",
                claim="TW_UNIT_IDENTITY",
            ),
            "hiyori-six-star": _evidence_item(
                filename="six-star.html",
                payload=SIX_STAR_BYTES,
                locator="article:six-star-release",
                claim="TW_SIX_STAR_RELEASE",
            ),
        },
        "schema_version": "private-pve-portrait-overrides/v1",
        "units": {
            "hiyori_orig": {
                "estertion_base_id": "1001",
                "estertion_jp_name": "ヒヨリ",
                "exact_variant_status": "USER_CONFIRMED",
                "identity_evidence_ids": ["hiyori-identity"],
                "six_star_evidence_ids": ["hiyori-six-star"],
                "six_star_tw_status": "AVAILABLE",
                "tw_name": "日和",
                "tw_unit_id": 100101,
            }
        },
    }


def _catalog_sha(catalog: dict[str, object]) -> str:
    return hashlib.sha256(canonical_json_bytes(catalog)).hexdigest()


def _validated_inputs():
    catalog = _catalog()
    catalog_sha256 = _catalog_sha(catalog)
    overrides = _overrides(catalog_sha256)
    validated = validate_override_registry(
        overrides,
        formation_sha256s=formation_asset_sha256s(catalog),
        base_catalog_sha256=catalog_sha256,
    )
    return catalog, catalog_sha256, validated


def _named_evidence_inputs(tmp_path, *, tw_name: str, six_star_payload: bytes):
    catalog = _catalog()
    catalog_sha256 = _catalog_sha(catalog)
    overrides = _overrides(catalog_sha256)
    overrides["units"]["hiyori_orig"]["tw_name"] = tw_name
    identity_payload = f"official identity 「{tw_name}」 snapshot".encode()
    for evidence in overrides["evidence"].values():
        evidence["tw_name"] = tw_name
    overrides["evidence"]["hiyori-identity"]["source_sha256"] = hashlib.sha256(
        identity_payload
    ).hexdigest()
    overrides["evidence"]["hiyori-six-star"]["source_sha256"] = hashlib.sha256(
        six_star_payload
    ).hexdigest()
    validated = validate_override_registry(
        overrides,
        formation_sha256s=formation_asset_sha256s(catalog),
        base_catalog_sha256=catalog_sha256,
    )
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "identity.html").write_bytes(identity_payload)
    (evidence_dir / "six-star.html").write_bytes(six_star_payload)
    return validated, evidence_dir


def test_review_queue_prioritizes_reuse_and_is_byte_deterministic() -> None:
    catalog, catalog_sha256, overrides = _validated_inputs()
    queue = build_portrait_review_queue(
        catalog,
        catalog_sha256=catalog_sha256,
        overrides=overrides,
        override_registry_sha256="d" * 64,
    )

    assert [item["image_sha256"] for item in queue["items"]] == [ASSET_A, ASSET_B]
    assert [item["formation_occurrence_count"] for item in queue["items"]] == [6, 4]
    assert [item["review_order"] for item in queue["items"]] == [1, 2]
    assert [item["review_state"] for item in queue["items"]] == [
        CONFIRMED,
        REVIEWED_UNKNOWN,
    ]
    assert queue["summary"] == {
        "formation_asset_count": 2,
        "formation_occurrence_count": 10,
        "state_counts": {PENDING: 0, REVIEWED_UNKNOWN: 1, CONFIRMED: 1},
    }
    assert canonical_json_bytes(queue) == canonical_json_bytes(
        build_portrait_review_queue(
            copy.deepcopy(catalog),
            catalog_sha256=catalog_sha256,
            overrides=copy.deepcopy(overrides),
            override_registry_sha256="d" * 64,
        )
    )


def test_queue_without_registry_marks_every_formation_asset_pending() -> None:
    catalog = _catalog()
    queue = build_portrait_review_queue(
        catalog,
        catalog_sha256=_catalog_sha(catalog),
    )

    assert [item["review_state"] for item in queue["items"]] == [PENDING, PENDING]
    assert queue["inputs"]["override_registry_sha256"] is None


def test_registry_fails_closed_on_unproven_six_star_and_extra_asset() -> None:
    catalog = _catalog()
    catalog_sha256 = _catalog_sha(catalog)
    formation_shas = formation_asset_sha256s(catalog)
    missing_evidence = _overrides(catalog_sha256)
    missing_evidence["units"]["hiyori_orig"]["six_star_evidence_ids"] = []
    with pytest.raises(PortraitReviewError, match="without official evidence"):
        validate_override_registry(
            missing_evidence,
            formation_sha256s=formation_shas,
            base_catalog_sha256=catalog_sha256,
        )

    extraneous = _overrides(catalog_sha256)
    extraneous["assets"]["f" * 64] = {
        "reason": "NOT_IDENTIFIED",
        "review_status": "REVIEWED_UNKNOWN",
    }
    with pytest.raises(PortraitReviewError, match="not referenced by a formation"):
        validate_override_registry(
            extraneous,
            formation_sha256s=formation_shas,
            base_catalog_sha256=catalog_sha256,
        )


def test_registry_rejects_evidence_for_a_different_tw_name() -> None:
    catalog = _catalog()
    catalog_sha256 = _catalog_sha(catalog)
    overrides = _overrides(catalog_sha256)
    overrides["evidence"]["hiyori-identity"]["tw_name"] = "優衣"

    with pytest.raises(PortraitReviewError, match="tw_name does not match"):
        validate_override_registry(
            overrides,
            formation_sha256s=formation_asset_sha256s(catalog),
            base_catalog_sha256=catalog_sha256,
        )

    wrong_claim = _overrides(catalog_sha256)
    wrong_claim["evidence"]["hiyori-six-star"]["claims"] = ["TW_UNIT_IDENTITY"]
    with pytest.raises(PortraitReviewError, match="does not confirm a TW six-star"):
        validate_override_registry(
            wrong_claim,
            formation_sha256s=formation_asset_sha256s(catalog),
            base_catalog_sha256=catalog_sha256,
        )

    icon_id_as_unit_id = _overrides(catalog_sha256)
    icon_id_as_unit_id["units"]["hiyori_orig"]["tw_unit_id"] = 100161
    with pytest.raises(PortraitReviewError, match="exact playable-unit ID 100101"):
        validate_override_registry(
            icon_id_as_unit_id,
            formation_sha256s=formation_asset_sha256s(catalog),
            base_catalog_sha256=catalog_sha256,
        )

    unparsed_database = _overrides(catalog_sha256)
    unparsed_database["evidence"]["hiyori-identity"]["kind"] = (
        "TW_OFFICIAL_DATABASE_SNAPSHOT"
    )
    with pytest.raises(PortraitReviewError, match="kind is unsupported"):
        validate_override_registry(
            unparsed_database,
            formation_sha256s=formation_asset_sha256s(catalog),
            base_catalog_sha256=catalog_sha256,
        )


def test_evidence_files_are_verified_by_exact_bytes(tmp_path) -> None:
    _catalog_value, _catalog_sha256, overrides = _validated_inputs()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "identity.html").write_bytes(IDENTITY_BYTES)
    (evidence_dir / "six-star.html").write_bytes(SIX_STAR_BYTES)

    verified = verify_evidence_files(overrides, evidence_dir)
    assert verified == {
        key: item["source_sha256"] for key, item in overrides["evidence"].items()
    }

    (evidence_dir / "six-star.html").write_bytes(b"tampered")
    with pytest.raises(PortraitReviewError, match="does not match registry"):
        verify_evidence_files(overrides, evidence_dir)


def test_official_news_evidence_must_contain_its_declared_claim(tmp_path) -> None:
    _catalog_value, _catalog_sha256, overrides = _validated_inputs()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "identity.html").write_bytes(IDENTITY_BYTES)
    unrelated = "官方公告：「日和（新年）」登場".encode()
    (evidence_dir / "six-star.html").write_bytes(unrelated)
    overrides["evidence"]["hiyori-six-star"]["source_sha256"] = hashlib.sha256(
        unrelated
    ).hexdigest()

    with pytest.raises(PortraitReviewError, match="exact TW name"):
        verify_evidence_files(overrides, evidence_dir)


def test_identity_evidence_accepts_exact_quoted_memory_fragment_name(tmp_path) -> None:
    _catalog_value, _catalog_sha256, overrides = _validated_inputs()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    exact_identity = "大師商店追加了「日和的記憶碎片」".encode()
    (evidence_dir / "identity.html").write_bytes(exact_identity)
    (evidence_dir / "six-star.html").write_bytes(SIX_STAR_BYTES)
    overrides["evidence"]["hiyori-identity"]["source_sha256"] = hashlib.sha256(
        exact_identity
    ).hexdigest()

    verified = verify_evidence_files(overrides, evidence_dir)

    assert verified["hiyori-identity"] == hashlib.sha256(exact_identity).hexdigest()


def test_identity_evidence_rejects_different_variant_memory_fragment(tmp_path) -> None:
    _catalog_value, _catalog_sha256, overrides = _validated_inputs()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    wrong_variant = "大師商店追加了「日和（新年）的記憶碎片」".encode()
    (evidence_dir / "identity.html").write_bytes(wrong_variant)
    (evidence_dir / "six-star.html").write_bytes(SIX_STAR_BYTES)
    overrides["evidence"]["hiyori-identity"]["source_sha256"] = hashlib.sha256(
        wrong_variant
    ).hexdigest()

    with pytest.raises(PortraitReviewError, match="exact TW name"):
        verify_evidence_files(overrides, evidence_dir)


def test_identity_evidence_accepts_exact_official_section_heading(tmp_path) -> None:
    _catalog_value, _catalog_sha256, overrides = _validated_inputs()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    exact_identity = "■日和<br />〖日和的拳套〗".encode()
    (evidence_dir / "identity.html").write_bytes(exact_identity)
    (evidence_dir / "six-star.html").write_bytes(SIX_STAR_BYTES)
    overrides["evidence"]["hiyori-identity"]["source_sha256"] = hashlib.sha256(
        exact_identity
    ).hexdigest()

    verified = verify_evidence_files(overrides, evidence_dir)

    assert verified["hiyori-identity"] == hashlib.sha256(exact_identity).hexdigest()


def test_identity_evidence_rejects_different_variant_section_heading(tmp_path) -> None:
    _catalog_value, _catalog_sha256, overrides = _validated_inputs()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    wrong_variant = "■日和（新年）<br />〖日和的拳套〗".encode()
    (evidence_dir / "identity.html").write_bytes(wrong_variant)
    (evidence_dir / "six-star.html").write_bytes(SIX_STAR_BYTES)
    overrides["evidence"]["hiyori-identity"]["source_sha256"] = hashlib.sha256(
        wrong_variant
    ).hexdigest()

    with pytest.raises(PortraitReviewError, match="exact TW name"):
        verify_evidence_files(overrides, evidence_dir)


def test_six_star_evidence_cannot_use_a_different_name_variant(tmp_path) -> None:
    _catalog_value, _catalog_sha256, overrides = _validated_inputs()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "identity.html").write_bytes(IDENTITY_BYTES)
    wrong_variant = (
        "對象角色<br />・日和<br />公告：「日和（新年）」的★6才能開花登場"
    ).encode()
    (evidence_dir / "six-star.html").write_bytes(wrong_variant)
    overrides["evidence"]["hiyori-six-star"]["source_sha256"] = hashlib.sha256(
        wrong_variant
    ).hexdigest()

    with pytest.raises(PortraitReviewError, match="direct six-star claim"):
        verify_evidence_files(overrides, evidence_dir)


def test_grouped_six_star_release_accepts_exact_variant_list_item(tmp_path) -> None:
    grouped_release = (
        "<html><head><title>「破曉之星（新年）」的★6才能開花登場！</title>"
        "</head><body><p>以下角色的★6才能開花之姿將會登場。<br />"
        "■能夠以★6才能開花之姿登場的角色<br />"
        "・優衣（新年）<br />・怜（新年）<br />・日和（新年）<br />"
        "※角色名無特定排序<br /><br />■能夠純淨記憶碎片的冒險<br />"
        "・怜（新年）<br /></p></body></html>"
    ).encode()
    overrides, evidence_dir = _named_evidence_inputs(
        tmp_path,
        tw_name="怜（新年）",
        six_star_payload=grouped_release,
    )

    verified = verify_evidence_files(overrides, evidence_dir)

    assert verified["hiyori-six-star"] == hashlib.sha256(grouped_release).hexdigest()


def test_grouped_six_star_release_rejects_a_different_variant(tmp_path) -> None:
    wrong_variant = (
        "<p>以下角色登場。<br />■能夠以★6才能開花之姿登場的角色<br />"
        "・怜<br />・日和（新年）<br /><br />"
        "■其他角色資訊<br />・怜（新年）<br /></p>"
    ).encode()
    overrides, evidence_dir = _named_evidence_inputs(
        tmp_path,
        tw_name="怜（新年）",
        six_star_payload=wrong_variant,
    )

    with pytest.raises(PortraitReviewError, match="direct six-star claim"):
        verify_evidence_files(overrides, evidence_dir)


def test_grouped_six_star_release_rejects_name_from_another_section(tmp_path) -> None:
    wrong_section = (
        "<p>以下角色登場。<br />■能夠以★6才能開花之姿登場的角色<br />"
        "・優衣（新年）<br />・日和（新年）<br /><br />"
        "■能夠純淨記憶碎片的冒險<br />・怜（新年）<br /></p>"
    ).encode()
    overrides, evidence_dir = _named_evidence_inputs(
        tmp_path,
        tw_name="怜（新年）",
        six_star_payload=wrong_section,
    )

    with pytest.raises(PortraitReviewError, match="direct six-star claim"):
        verify_evidence_files(overrides, evidence_dir)


def test_six_star_package_accepts_exact_pure_memory_roster_item(tmp_path) -> None:
    package_roster = (
        "<html><head><title>「春夏特賣 ★6角色養成禮包」期間限定販售！"
        "</title></head><body><p>販售資訊。<br />■商品名稱<br />"
        "春夏特賣 ★6角色養成禮包<br /><br />■販售內容<br />"
        "‧春夏特賣 純淨記憶碎片交換券 × 1<br />"
        "‧春夏特賣 記憶碎片交換券 × 1<br /><br />"
        "■關於「交換券的目標角色」<br />"
        "透過 春夏特賣 純淨記憶碎片交換券，可以交換"
        "純淨記憶碎片的目標角色如下所述。<br />"
        "‧鈴<br />‧深月<br /><br />■注意事項<br />內容<br /></p></body></html>"
    ).encode()
    overrides, evidence_dir = _named_evidence_inputs(
        tmp_path,
        tw_name="深月",
        six_star_payload=package_roster,
    )

    verified = verify_evidence_files(overrides, evidence_dir)

    assert verified["hiyori-six-star"] == hashlib.sha256(package_roster).hexdigest()


def test_six_star_package_rejects_a_different_variant(tmp_path) -> None:
    wrong_variant = (
        "<html><head><title>★6角色養成禮包</title></head><body><p>公告。<br />"
        "■商品名稱<br />★6角色養成禮包<br />■販售內容<br />"
        "‧純淨記憶碎片交換券 × 1<br />"
        "■關於「交換券的目標角色」<br />"
        "純淨記憶碎片交換券，可以交換純淨記憶碎片的目標角色。<br />"
        "‧鈴（新年）<br />■其他資訊<br />‧鈴<br /></p></body></html>"
    ).encode()
    overrides, evidence_dir = _named_evidence_inputs(
        tmp_path,
        tw_name="鈴",
        six_star_payload=wrong_variant,
    )

    with pytest.raises(PortraitReviewError, match="direct six-star claim"):
        verify_evidence_files(overrides, evidence_dir)


def test_six_star_package_rejects_name_from_another_section(tmp_path) -> None:
    wrong_section = (
        "<html><head><title>★6角色養成禮包</title></head><body><p>公告。<br />"
        "■商品名稱<br />★6角色養成禮包<br />■販售內容<br />"
        "‧純淨記憶碎片交換券 × 1<br />"
        "■關於「交換券的目標角色」<br />"
        "純淨記憶碎片交換券，可以交換純淨記憶碎片的目標角色。<br />"
        "‧鈴<br />■注意事項<br />‧深月<br /></p></body></html>"
    ).encode()
    overrides, evidence_dir = _named_evidence_inputs(
        tmp_path,
        tw_name="深月",
        six_star_payload=wrong_section,
    )

    with pytest.raises(PortraitReviewError, match="direct six-star claim"):
        verify_evidence_files(overrides, evidence_dir)


@pytest.mark.parametrize(
    ("title", "product_name", "ticket_item"),
    [
        ("期間限定禮包", "★6角色養成禮包", "‧純淨記憶碎片交換券 × 1"),
        ("★6角色養成禮包", "一般養成禮包", "‧純淨記憶碎片交換券 × 1"),
        ("★6角色養成禮包", "★6角色養成禮包", "‧記憶碎片交換券 × 1"),
    ],
)
def test_six_star_package_requires_title_product_and_pure_memory_ticket(
    tmp_path,
    title,
    product_name,
    ticket_item,
) -> None:
    incomplete_package = (
        f"<html><head><title>{title}</title></head><body><p>公告。<br />"
        f"■商品名稱<br />{product_name}<br />■販售內容<br />{ticket_item}<br />"
        "■關於「交換券的目標角色」<br />"
        "純淨記憶碎片交換券，可以交換純淨記憶碎片的目標角色。<br />"
        "‧深月<br />■注意事項<br /></p></body></html>"
    ).encode()
    overrides, evidence_dir = _named_evidence_inputs(
        tmp_path,
        tw_name="深月",
        six_star_payload=incomplete_package,
    )

    with pytest.raises(PortraitReviewError, match="direct six-star claim"):
        verify_evidence_files(overrides, evidence_dir)


def test_materialization_is_derived_exact_and_preserves_excel_fallback() -> None:
    catalog, catalog_sha256, overrides = _validated_inputs()
    original = copy.deepcopy(catalog)
    mapping = map_catalog_characters(
        catalog,
        overrides,
        parse_estertion_index(INDEX_SNAPSHOT),
        asset_sha256s=formation_asset_sha256s(catalog),
    )
    mapped = materialize_character_catalog(catalog, mapping)

    assert catalog == original
    assert mapped["assets"] == catalog["assets"]
    assert mapped["summary"] == catalog["summary"]
    first = mapped["sources"][0]["sheets"][0]["sections"][0]["teams"][0]
    assert {member["mapping_status"] for member in first["formation"]} == {"RESOLVED"}
    assert {member["tw_name"] for member in first["formation"]} == {"日和"}
    assert {member["estertion_base_id"] for member in first["formation"]} == {"1001"}
    assert {member["icon_id"] for member in first["formation"]} == {"100161"}
    # image_sha256 always remains the exact workbook-embedded fallback.
    assert {member["image_sha256"] for member in first["formation"]} == {ASSET_A}
    second = mapped["sources"][0]["sheets"][0]["sections"][0]["teams"][1]
    unknown = [member for member in second["formation"] if member["image_sha256"] == ASSET_B]
    assert {member["mapping_status"] for member in unknown} == {REVIEWED_UNKNOWN}
    assert {member["display_source"] for member in unknown} == {"WORKBOOK_EMBEDDED"}
    assert {member["icon_id"] for member in unknown} == {None}

    manifest = build_materialization_manifest(
        base_catalog_sha256=catalog_sha256,
        override_registry_sha256="d" * 64,
        estertion_index_sha256="e" * 64,
        overrides=overrides,
        verified_evidence_sha256s={
            key: item["source_sha256"] for key, item in overrides["evidence"].items()
        },
        mapping_manifest=mapping,
        mapped_catalog=mapped,
    )
    assert manifest["outputs"]["mapped_catalog_sha256"] == hashlib.sha256(
        canonical_json_bytes(mapped)
    ).hexdigest()
    assert manifest["outputs"]["character_mapping_sha256"] == hashlib.sha256(
        canonical_json_bytes(mapping)
    ).hexdigest()


def test_strict_json_rejects_duplicate_keys(tmp_path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":"one","schema_version":"two"}\n', encoding="utf-8")

    with pytest.raises(PortraitReviewError, match="duplicate JSON object key"):
        load_strict_json(path)


def test_review_and_materialize_cli_write_distinct_derived_artifacts(
    tmp_path,
    capsys,
) -> None:
    catalog = _catalog()
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_bytes(canonical_json_bytes(catalog))
    catalog_sha256 = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    overrides = _overrides(catalog_sha256)
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_bytes(canonical_json_bytes(overrides))
    index_path = tmp_path / "estertion.html"
    index_path.write_text(INDEX_SNAPSHOT, encoding="utf-8")
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "identity.html").write_bytes(IDENTITY_BYTES)
    (evidence_dir / "six-star.html").write_bytes(SIX_STAR_BYTES)

    queue_path = tmp_path / "review-queue.json"
    assert main(
        [
            "build-review-queue",
            "--catalog",
            str(catalog_path),
            "--overrides",
            str(overrides_path),
            "--output",
            str(queue_path),
        ]
    ) == 0
    assert json.loads(queue_path.read_text(encoding="utf-8"))["items"][0][
        "review_order"
    ] == 1

    mapped_path = tmp_path / "mapped-catalog.json"
    mapping_path = tmp_path / "mapping.json"
    manifest_path = tmp_path / "materialization.json"
    (evidence_dir / "six-star.html").write_bytes(b"tampered")
    with pytest.raises(PortraitReviewError, match="does not match registry"):
        main(
            [
                "materialize-character-catalog",
                "--catalog",
                str(catalog_path),
                "--overrides",
                str(overrides_path),
                "--estertion-index",
                str(index_path),
                "--evidence-dir",
                str(evidence_dir),
                "--output",
                str(mapped_path),
                "--mapping-output",
                str(mapping_path),
                "--manifest-output",
                str(manifest_path),
            ]
        )
    assert not any(path.exists() for path in (mapped_path, mapping_path, manifest_path))
    (evidence_dir / "six-star.html").write_bytes(SIX_STAR_BYTES)
    assert main(
        [
            "materialize-character-catalog",
            "--catalog",
            str(catalog_path),
            "--overrides",
            str(overrides_path),
            "--estertion-index",
            str(index_path),
            "--evidence-dir",
            str(evidence_dir),
            "--output",
            str(mapped_path),
            "--mapping-output",
            str(mapping_path),
            "--manifest-output",
            str(manifest_path),
        ]
    ) == 0

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["inputs"]["base_catalog_sha256"] == catalog_sha256
    assert manifest["outputs"]["mapped_catalog_sha256"] == hashlib.sha256(
        mapped_path.read_bytes()
    ).hexdigest()
    assert capsys.readouterr().out.isascii()
