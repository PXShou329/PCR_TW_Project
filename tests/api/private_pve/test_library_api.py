from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Callable

import pytest
from fastapi.testclient import TestClient

from pcr_api.config import Settings
from pcr_api.main import create_app
from pcr_api.private_pve.runtime import media_for_url


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _catalog(asset_bytes: bytes) -> dict:
    asset_sha256 = _sha256(asset_bytes)
    source_ref = {
        "kind": "URL",
        "label_raw": "XOOOO demo",
        "origin_cell": "火屬性!I4",
        "resolution_status": "RESOLVED",
        "alias_id": None,
        "alias_label": None,
        "applies_to_cell": None,
        "url": "https://youtu.be/CnL5X4oPy_I?si=demo",
    }
    alias_ref = {
        "kind": "WORKBOOK_ALIAS",
        "label_raw": "#1",
        "origin_cell": "火屬性!I4",
        "resolution_status": "UNLOCATED",
        "alias_id": "1",
        "alias_label": "#1",
        "applies_to_cell": "I4",
        "url": None,
    }
    formation = [
        {
            "anchor_cell": f"{column}4",
            "display_position": position,
            "image_sha256": asset_sha256,
            "mapping_status": "UNMAPPED",
            "unit_key": None,
        }
        for position, column in enumerate("ABCDE", start=1)
    ]
    team = {
        "axes": [
            {
                "axis_source_id": "deep:fire:01-01:l:004:axis:f4",
                "notes_raw": "workbook note",
                "operation": {
                    "execution_hints": [],
                    "kind": "SET_CONFIGURATION",
                    "member_alignment": "UNRESOLVED",
                    "order_basis": "WORKBOOK_TEXT_LEFT_TO_RIGHT",
                    "variants": [
                        {
                            "kind": "POSITIONAL_SET",
                            "origin_cell": "F4",
                            "origin_field": "OPERATION_TEXT",
                            "raw": "XOOOO",
                            "source_order_states": [
                                "NOT_SET",
                                "SET",
                                "SET",
                                "SET",
                                "SET",
                            ],
                        }
                    ],
                },
                "operation_raw": "XOOOO",
                "source_cell": "F4",
                "source_refs": [source_ref],
            }
        ],
        "display_order": 1,
        "flags": [],
        "formation": formation,
        "notes_raw": "workbook note",
        "source_range": "A4:I4",
        "source_refs": [source_ref, alias_ref],
        "team_source_id": "deep:fire:01-01:l:004",
    }
    section = {
        "element": "FIRE",
        "era": {"kind": "UNKNOWN", "label_raw": None},
        "label_raw": "1-1",
        "mode": "DEEP",
        "section_id": "deep:fire:01-01",
        "source_range": "A3:I3",
        "stage_refs": [{"area": 1, "kind": "DEEP", "stage": 1}],
        "teams": [team],
    }
    return {
        "assets": [
            {
                "byte_length": len(asset_bytes),
                "file_extension": "jpg",
                "filename": f"{asset_sha256}.jpg",
                "height_px": 128,
                "mime_type": "image/jpeg",
                "occurrences": [],
                "sha256": asset_sha256,
                "width_px": 128,
            }
        ],
        "builder": {"name": "pcr-private-pve-catalog", "version": "1.0.0"},
        "schema_version": "private-pve-local-catalog/v1",
        "sources": [
            {
                "diagnostics": [],
                "parser": {"name": "test", "version": "1.0.0"},
                "sheets": [
                    {
                        "collection": "TEST",
                        "element": "FIRE",
                        "layout_id": "test/v1",
                        "sections": [section],
                        "sheet_name": "火屬性",
                        "sheet_state": "VISIBLE",
                        "source_refs": [],
                    }
                ],
                "source_workbook": {
                    "byte_length": 123,
                    "filename": "source.xlsx",
                    "sha256": "a" * 64,
                },
                "staging_catalog": {
                    "schema_version": "private-pve-xlsx-staging/v1",
                    "sha256": "b" * 64,
                },
                "summary": {},
            }
        ],
        "summary": {
            "asset_count": 1,
            "asset_occurrence_count": 0,
            "axis_count": 1,
            "diagnostic_count": 0,
            "section_count": 1,
            "sheet_count": 1,
            "source_workbook_count": 1,
            "team_count": 1,
        },
    }


def _set_exact_mapping(catalog: dict, *, rarity: str) -> dict:
    member = catalog["sources"][0]["sheets"][0]["sections"][0]["teams"][0][
        "formation"
    ][0]
    member.update(
        {
            "mapping_status": "RESOLVED",
            "mapping_reason": "EXACT_VARIANT",
            "unit_key": "hiyori_orig",
            "tw_name": "日和",
            "display_source": "ESTERTION",
            "display_rarity": rarity,
            "estertion_base_id": "1001",
            "icon_id": "100161" if rarity == "SIX_STAR" else "100131",
        }
    )
    return member


def _write_library(tmp_path: Path, catalog: dict | None = None) -> tuple[Path, Path, dict]:
    asset_bytes = b"fake-jpeg-portrait"
    resolved_catalog = catalog or _catalog(asset_bytes)
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    for asset in resolved_catalog["assets"]:
        (asset_dir / asset["filename"]).write_bytes(asset_bytes)
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(resolved_catalog, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return catalog_path, asset_dir, resolved_catalog


def _client(
    catalog_path: Path | None,
    asset_dir: Path | None,
    *,
    external_icons_enabled: bool = False,
) -> TestClient:
    def database_must_not_be_opened() -> None:
        raise AssertionError("PVE library endpoints must not open a database session")

    return TestClient(
        create_app(
            settings=Settings(
                database_url="sqlite://",
                pve_library_catalog_path=catalog_path,
                pve_library_asset_dir=asset_dir,
                pve_library_external_icons_enabled=external_icons_enabled,
            ),
            session_factory=database_must_not_be_opened,
        )
    )


def test_settings_require_catalog_and_assets_as_one_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="must be configured together"):
        Settings(database_url="sqlite://", pve_library_catalog_path=Path("catalog.json"))

    monkeypatch.setenv("PCR_DATABASE_URL", "sqlite://")
    monkeypatch.setenv("PCR_PVE_LIBRARY_CATALOG_PATH", "catalog.json")
    monkeypatch.delenv("PCR_PVE_LIBRARY_ASSET_DIR", raising=False)
    with pytest.raises(ValueError, match="must be configured together"):
        Settings.from_environment()

    monkeypatch.setenv("PCR_PVE_LIBRARY_CATALOG_PATH", "  ")
    monkeypatch.setenv("PCR_PVE_LIBRARY_ASSET_DIR", "\t")
    disabled = Settings.from_environment()
    assert disabled.pve_library_catalog_path is None
    assert disabled.pve_library_asset_dir is None

    monkeypatch.setenv("PCR_PVE_LIBRARY_CATALOG_PATH", "catalog.json")
    monkeypatch.setenv("PCR_PVE_LIBRARY_ASSET_DIR", "assets")
    configured = Settings.from_environment()
    assert configured.pve_library_catalog_path == Path("catalog.json")
    assert configured.pve_library_asset_dir == Path("assets")


def test_external_icon_setting_is_default_off_and_requires_a_boolean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PCR_DATABASE_URL", "sqlite://")
    monkeypatch.delenv("PCR_PVE_LIBRARY_EXTERNAL_ICONS_ENABLED", raising=False)
    assert Settings.from_environment().pve_library_external_icons_enabled is False

    monkeypatch.setenv("PCR_PVE_LIBRARY_EXTERNAL_ICONS_ENABLED", "true")
    assert Settings.from_environment().pve_library_external_icons_enabled is True

    monkeypatch.setenv("PCR_PVE_LIBRARY_EXTERNAL_ICONS_ENABLED", "OFF")
    assert Settings.from_environment().pve_library_external_icons_enabled is False

    monkeypatch.setenv("PCR_PVE_LIBRARY_EXTERNAL_ICONS_ENABLED", "sometimes")
    with pytest.raises(ValueError, match="must be an explicit boolean"):
        Settings.from_environment()


@pytest.mark.parametrize(
    ("rarity", "icon_id"),
    [("THREE_STAR", "100131"), ("SIX_STAR", "100161")],
)
def test_exact_estertion_icon_is_additive_and_default_off(
    tmp_path: Path,
    rarity: str,
    icon_id: str,
) -> None:
    catalog = _catalog(b"fake-jpeg-portrait")
    _set_exact_mapping(catalog, rarity=rarity)
    catalog_path, asset_dir, written_catalog = _write_library(tmp_path, catalog)
    asset_sha256 = written_catalog["assets"][0]["sha256"]

    with _client(catalog_path, asset_dir) as client:
        disabled = client.get("/api/v1/pve-library/stages/deep:fire:01-01")
    with _client(
        catalog_path,
        asset_dir,
        external_icons_enabled=True,
    ) as client:
        enabled = client.get("/api/v1/pve-library/stages/deep:fire:01-01")

    assert disabled.status_code == 200
    disabled_portrait = disabled.json()["data"]["teams"][0]["portraits"][0]
    assert disabled_portrait["asset_url"] == (
        f"/api/v1/pve-library/assets/{asset_sha256}"
    )
    assert disabled_portrait["icon_url"] is None
    assert disabled_portrait["display_source"] == "WORKBOOK_EMBEDDED"
    assert disabled_portrait["display_rarity"] is None

    assert enabled.status_code == 200
    enabled_portrait = enabled.json()["data"]["teams"][0]["portraits"][0]
    assert enabled_portrait["asset_url"] == disabled_portrait["asset_url"]
    assert enabled_portrait["icon_url"] == (
        f"https://redive.estertion.win/icon/unit/{icon_id}.webp"
    )
    assert enabled_portrait["unit_key"] == "hiyori_orig"
    assert enabled_portrait["tw_name"] == "日和"
    assert enabled_portrait["display_source"] == "ESTERTION"
    assert enabled_portrait["display_rarity"] == rarity


def test_confirmed_six_star_with_missing_asset_may_use_exact_three_star_icon(
    tmp_path: Path,
) -> None:
    catalog = _catalog(b"fake-jpeg-portrait")
    member = _set_exact_mapping(catalog, rarity="THREE_STAR")
    member["mapping_reason"] = "EXACT_SIX_STAR_ICON_MISSING"
    catalog_path, asset_dir, _written_catalog = _write_library(tmp_path, catalog)

    with _client(
        catalog_path,
        asset_dir,
        external_icons_enabled=True,
    ) as client:
        response = client.get("/api/v1/pve-library/stages/deep:fire:01-01")

    assert response.status_code == 200
    portrait = response.json()["data"]["teams"][0]["portraits"][0]
    assert portrait["icon_url"] == (
        "https://redive.estertion.win/icon/unit/100131.webp"
    )
    assert portrait["display_rarity"] == "THREE_STAR"
    assert portrait["display_source"] == "ESTERTION"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mapping_status", "AMBIGUOUS"),
        ("mapping_reason", "CROSS_VARIANT_NAME_MISMATCH"),
        ("mapping_reason", "SIX_STAR_TW_EVIDENCE_NOT_CONFIRMED"),
        ("mapping_reason", "EXACT_SIX_STAR_ICON_MISSING"),
        ("unit_key", None),
        ("tw_name", None),
        ("display_source", "WORKBOOK_EMBEDDED"),
        ("display_rarity", "THREE_STAR"),
        ("estertion_base_id", "1002"),
        ("icon_id", "100162"),
        ("icon_id", "100161?redirect=https://example.invalid"),
    ],
)
def test_inconsistent_estertion_metadata_falls_back_to_workbook(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    catalog = _catalog(b"fake-jpeg-portrait")
    member = _set_exact_mapping(catalog, rarity="SIX_STAR")
    member[field] = value
    catalog_path, asset_dir, _written_catalog = _write_library(tmp_path, catalog)

    with _client(
        catalog_path,
        asset_dir,
        external_icons_enabled=True,
    ) as client:
        response = client.get("/api/v1/pve-library/stages/deep:fire:01-01")

    assert response.status_code == 200
    portrait = response.json()["data"]["teams"][0]["portraits"][0]
    assert portrait["icon_url"] is None
    assert portrait["display_source"] == "WORKBOOK_EMBEDDED"
    assert portrait["display_rarity"] is None


def test_catalog_icon_url_cannot_override_the_fixed_estertion_origin(tmp_path: Path) -> None:
    catalog = _catalog(b"fake-jpeg-portrait")
    member = _set_exact_mapping(catalog, rarity="SIX_STAR")
    member["icon_url"] = "https://redive.estertion.win.example/icon/unit/100161.webp"
    catalog_path, asset_dir, _written_catalog = _write_library(tmp_path, catalog)

    with _client(
        catalog_path,
        asset_dir,
        external_icons_enabled=True,
    ) as client:
        response = client.get("/api/v1/pve-library/stages/deep:fire:01-01")

    assert response.status_code == 200
    portrait = response.json()["data"]["teams"][0]["portraits"][0]
    assert portrait["icon_url"] == (
        "https://redive.estertion.win/icon/unit/100161.webp"
    )


def test_mapping_metadata_is_optional_and_absence_uses_workbook_fallback(
    tmp_path: Path,
) -> None:
    catalog = _catalog(b"fake-jpeg-portrait")
    formation = catalog["sources"][0]["sheets"][0]["sections"][0]["teams"][0][
        "formation"
    ]
    optional_fields = {
        "mapping_status",
        "mapping_reason",
        "unit_key",
        "tw_name",
        "estertion_base_id",
        "icon_id",
        "display_source",
        "display_rarity",
    }
    for member in formation:
        for field in optional_fields:
            member.pop(field, None)
    catalog_path, asset_dir, _written_catalog = _write_library(tmp_path, catalog)

    with _client(
        catalog_path,
        asset_dir,
        external_icons_enabled=True,
    ) as client:
        response = client.get("/api/v1/pve-library/stages/deep:fire:01-01")

    assert response.status_code == 200
    portraits = response.json()["data"]["teams"][0]["portraits"]
    assert len(portraits) == 5
    assert all(portrait["mapping_status"] == "UNMAPPED" for portrait in portraits)
    assert all(portrait["icon_url"] is None for portrait in portraits)
    assert all(portrait["display_source"] == "WORKBOOK_EMBEDDED" for portrait in portraits)


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/pve-library/stages",
        "/api/v1/pve-library/stages/deep:fire:01-01",
        "/api/v1/pve-library/assets/" + "a" * 64,
    ],
)
def test_unconfigured_library_is_a_structured_503_without_database_access(
    path: str,
) -> None:
    with _client(None, None) as client:
        response = client.get(path)

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "PVE_LIBRARY_NOT_CONFIGURED",
            "message": "The local PVE library is not configured.",
        }
    }


def test_openapi_documents_local_library_success_and_error_contracts() -> None:
    with _client(None, None) as client:
        document = client.app.openapi()

    paths = document["paths"]
    assert set(paths["/api/v1/pve-library/stages"]) == {"get"}
    assert set(paths["/api/v1/pve-library/stages/{stage_id}"]) == {"get"}
    assert set(paths["/api/v1/pve-library/assets/{sha256}"]) == {"get"}
    assert set(paths["/api/v1/pve-library/stages"]["get"]["responses"]) >= {
        "200",
        "422",
        "503",
    }
    assert set(paths["/api/v1/pve-library/stages/{stage_id}"]["get"]["responses"]) >= {
        "200",
        "404",
        "422",
        "503",
    }
    error_schema = document["components"]["schemas"]["PveLibraryErrorResponse"]
    assert error_schema["required"] == ["error"]


def test_library_list_detail_asset_and_provenance_contract(tmp_path: Path) -> None:
    catalog_path, asset_dir, catalog = _write_library(tmp_path)
    expected_catalog_sha256 = _sha256(catalog_path.read_bytes())
    asset = catalog["assets"][0]

    with _client(catalog_path, asset_dir) as client:
        listed = client.get(
            "/api/v1/pve-library/stages",
            params={"mode": "deep", "element": "fire", "area": 1, "stage": 1},
        )
        detail = client.get("/api/v1/pve-library/stages/deep:fire:01-01")
        portrait = client.get(f"/api/v1/pve-library/assets/{asset['sha256']}")

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["data"]["total"] == 1
    assert payload["data"]["filters"] == {
        "mode": "DEEP",
        "element": "FIRE",
        "area": 1,
        "stage": 1,
    }
    assert payload["data"]["available_filters"] == {
        "modes": ["DEEP"],
        "elements": ["FIRE"],
        "areas": [1],
        "stages": [1],
    }
    item = payload["data"]["items"][0]
    assert item["stage_id"] == "deep:fire:01-01"
    assert item["team_count"] == 1
    assert item["provenance"] == {
        "source_workbook_sha256": "a" * 64,
        "source_workbook_filename": "source.xlsx",
        "staging_catalog_sha256": "b" * 64,
        "sheet_name": "火屬性",
        "source_range": "A3:I3",
    }
    assert payload["meta"] == {
        "api_version": "v1",
        "schema_version": "private-pve-local-catalog/v1",
        "dataset_sha256": expected_catalog_sha256,
        "source_status": "SOURCE_PROVIDED",
        "independent_clear_verification": "NOT_PERFORMED",
        "source_workbooks": [
            {
                "filename": "source.xlsx",
                "sha256": "a" * 64,
                "byte_length": 123,
                "staging_catalog_sha256": "b" * 64,
            }
        ],
    }
    assert "generated_at" not in payload["meta"]
    assert "import_run_id" not in json.dumps(payload)

    assert detail.status_code == 200
    team = detail.json()["data"]["teams"][0]
    assert len(team["portraits"]) == 5
    assert team["portraits"][0]["asset_url"] == (
        f"/api/v1/pve-library/assets/{asset['sha256']}"
    )
    assert team["portraits"][0]["icon_url"] is None
    assert team["portraits"][0]["tw_name"] is None
    assert team["portraits"][0]["display_rarity"] is None
    assert team["portraits"][0]["display_source"] == "WORKBOOK_EMBEDDED"
    variant = team["axes"][0]["operation"]["variants"][0]
    assert variant["raw"] == "XOOOO"
    assert variant["source_order_states"] == [
        "NOT_SET",
        "SET",
        "SET",
        "SET",
        "SET",
    ]
    youtube = team["source_links"][0]
    assert youtube["origin_cell"] == "火屬性!I4"
    assert youtube["media"] == {
        "kind": "YOUTUBE",
        "external_url": "https://youtu.be/CnL5X4oPy_I?si=demo",
        "embed_url": "https://www.youtube-nocookie.com/embed/CnL5X4oPy_I",
        "video_id": "CnL5X4oPy_I",
    }
    alias = team["source_links"][1]
    assert alias["alias_id"] == "1"
    assert alias["url"] is None
    assert alias["media"] is None
    assert team["provenance"]["source_range"] == "A4:I4"

    assert portrait.status_code == 200
    assert portrait.content == b"fake-jpeg-portrait"
    assert portrait.headers["content-type"] == "image/jpeg"
    assert portrait.headers["etag"] == f'"{asset["sha256"]}"'
    assert portrait.headers["x-content-type-options"] == "nosniff"


def test_list_filters_share_one_stage_ref_and_future_empty_results_are_200(
    tmp_path: Path,
) -> None:
    catalog_path, asset_dir, _catalog_data = _write_library(tmp_path)
    with _client(catalog_path, asset_dir) as client:
        response = client.get(
            "/api/v1/pve-library/stages",
            params={"area": 11, "stage": 12},
        )
    assert response.status_code == 200
    assert response.json()["data"]["items"] == []
    assert response.json()["data"]["total"] == 0


def test_available_filters_expose_current_deep_values_and_ignore_area_stage(
    tmp_path: Path,
) -> None:
    catalog = _catalog(b"fake-jpeg-portrait")
    section = catalog["sources"][0]["sheets"][0]["sections"][0]
    section["stage_refs"] = [
        {"area": area, "kind": "DEEP", "stage": stage}
        for area in range(1, 11)
        for stage in range(1, 11)
    ]
    catalog_path, asset_dir, _catalog_data = _write_library(tmp_path, catalog)

    with _client(catalog_path, asset_dir) as client:
        response = client.get(
            "/api/v1/pve-library/stages",
            params={
                "mode": "deep",
                "element": "fire",
                "area": 99,
                "stage": 99,
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["items"] == []
    assert data["available_filters"] == {
        "modes": ["DEEP"],
        "elements": ["FIRE"],
        "areas": list(range(1, 11)),
        "stages": list(range(1, 11)),
    }


def test_available_filters_are_scoped_sorted_and_data_driven(tmp_path: Path) -> None:
    catalog = _catalog(b"fake-jpeg-portrait")
    sections = catalog["sources"][0]["sheets"][0]["sections"]
    base = sections[0]
    base["section_id"] = "deep:fire:11-12"
    base["stage_refs"] = [
        {"area": 11, "kind": "DEEP", "stage": 12},
        {"area": 2, "kind": "DEEP", "stage": 3},
        {"area": 11, "kind": "DEEP", "stage": 3},
    ]

    water = deepcopy(base)
    water.update(section_id="deep:water:01-01", element="WATER", teams=[])
    water["stage_refs"] = [{"area": 1, "kind": "DEEP", "stage": 1}]
    luna = deepcopy(base)
    luna.update(section_id="luna:tower:01-01", mode="LUNA_TOWER", element="LUNA", teams=[])
    luna["stage_refs"] = [{"area": 1, "kind": "LUNA_TOWER", "stage": 1}]
    sections.extend([water, luna])
    catalog["summary"]["section_count"] = 3
    catalog_path, asset_dir, _catalog_data = _write_library(tmp_path, catalog)

    with _client(catalog_path, asset_dir) as client:
        response = client.get(
            "/api/v1/pve-library/stages",
            params={"mode": "deep", "element": "fire", "area": 11, "stage": 12},
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["available_filters"] == {
        "modes": ["DEEP", "LUNA_TOWER"],
        "elements": ["FIRE", "WATER"],
        "areas": [2, 11],
        "stages": [3, 12],
    }


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"area": 0}, "area"),
        ({"stage": 0}, "stage"),
        ({"mode": "   "}, "mode"),
        ({"element": "\t"}, "element"),
    ],
)
def test_invalid_or_blank_filters_are_422(
    tmp_path: Path,
    params: dict[str, str | int],
    field: str,
) -> None:
    catalog_path, asset_dir, _catalog_data = _write_library(tmp_path)
    with _client(catalog_path, asset_dir) as client:
        response = client.get("/api/v1/pve-library/stages", params=params)
    assert response.status_code == 422
    assert any(error["loc"][-1] == field for error in response.json()["detail"])


def test_unknown_stage_and_asset_are_structured_404s(tmp_path: Path) -> None:
    catalog_path, asset_dir, _catalog_data = _write_library(tmp_path)
    with _client(catalog_path, asset_dir) as client:
        stage = client.get("/api/v1/pve-library/stages/not-a-stage")
        asset = client.get("/api/v1/pve-library/assets/not-a-sha")

    assert stage.status_code == 404
    assert stage.json()["error"]["details"] == {
        "resource": "pve_stage",
        "id": "not-a-stage",
    }
    assert asset.status_code == 404
    assert asset.json()["error"]["details"] == {
        "resource": "pve_asset",
        "id": "not-a-sha",
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda catalog: catalog.update(schema_version="future-schema/v2"),
        lambda catalog: catalog["sources"][0]["sheets"][0]["sections"].append(
            deepcopy(catalog["sources"][0]["sheets"][0]["sections"][0])
        ),
        lambda catalog: catalog["sources"][0]["sheets"][0]["sections"][0][
            "teams"
        ][0]["formation"][0].update(image_sha256="c" * 64),
        lambda catalog: catalog.update(unexpected=True),
        lambda catalog: catalog["sources"][0]["sheets"][0]["sections"][0][
            "teams"
        ][0]["formation"].reverse(),
        lambda catalog: catalog["sources"][0]["sheets"][0]["sections"][0][
            "teams"
        ][0]["axes"][0]["operation"]["variants"][0].update(
            source_order_states=["NOT_SET", "SET"]
        ),
        lambda catalog: (
            catalog["sources"][0]["sheets"][0]["sections"][0]["teams"][0].update(
                axes=[]
            ),
            catalog["summary"].update(axis_count=0),
        ),
        lambda catalog: catalog["sources"][0]["sheets"][0]["sections"][0][
            "stage_refs"
        ][0].update(unexpected=True),
        lambda catalog: catalog["sources"][0]["sheets"][0]["sections"][0][
            "teams"
        ][0]["axes"][0]["operation"].update(unexpected=True),
        lambda catalog: catalog["sources"][0]["sheets"][0]["sections"][0][
            "teams"
        ][0]["axes"][0]["operation"]["variants"][0].update(unexpected=True),
    ],
    ids=[
        "schema",
        "duplicate-stage",
        "missing-member-asset",
        "extra-top-field",
        "formation-order",
        "short-set-variant",
        "non-allowlisted-zero-axis",
        "extra-stage-ref-field",
        "extra-operation-field",
        "extra-operation-variant-field",
    ],
)
def test_invalid_catalog_fails_closed_as_structured_503(
    tmp_path: Path,
    mutate: Callable[[dict], None],
) -> None:
    catalog = _catalog(b"fake-jpeg-portrait")
    mutate(catalog)
    catalog_path, asset_dir, _catalog_data = _write_library(tmp_path, catalog)

    with _client(catalog_path, asset_dir) as client:
        response = client.get("/api/v1/pve-library/stages")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PVE_LIBRARY_INVALID"


def test_allowlisted_source_gap_team_can_have_zero_axes(tmp_path: Path) -> None:
    catalog = _catalog(b"fake-jpeg-portrait")
    team = catalog["sources"][0]["sheets"][0]["sections"][0]["teams"][0]
    team["team_source_id"] = "deep:water:09-02:r:016"
    team["axes"] = []
    catalog["summary"]["axis_count"] = 0
    catalog_path, asset_dir, _catalog_data = _write_library(tmp_path, catalog)

    with _client(catalog_path, asset_dir) as client:
        response = client.get("/api/v1/pve-library/stages/deep:fire:01-01")

    assert response.status_code == 200
    returned_team = response.json()["data"]["teams"][0]
    assert returned_team["team_id"] == "deep:water:09-02:r:016"
    assert returned_team["axes"] == []


@pytest.mark.parametrize(
    "raw_json",
    [
        '{"schema_version":"private-pve-local-catalog/v1",'
        '"schema_version":"private-pve-local-catalog/v1"}',
        '{"assets":[],"builder":{"name":"pcr-private-pve-catalog",'
        '"version":"1.0.0"},"schema_version":"private-pve-local-catalog/v1",'
        '"sources":[],"summary":{"source_workbook_count":NaN}}',
        '{"assets":[],"builder":{"name":"pcr-private-pve-catalog",'
        '"version":"1.0.0"},"schema_version":"private-pve-local-catalog/v1",'
        '"sources":[],"summary":{"source_workbook_count":Infinity}}',
    ],
    ids=["duplicate-key", "nan", "infinity"],
)
def test_non_strict_json_forms_are_rejected(tmp_path: Path, raw_json: str) -> None:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(raw_json, encoding="utf-8")

    with _client(catalog_path, asset_dir) as client:
        response = client.get("/api/v1/pve-library/stages")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PVE_LIBRARY_INVALID"


def test_asset_occurrence_must_match_known_sheet_and_anchor(tmp_path: Path) -> None:
    catalog = _catalog(b"fake-jpeg-portrait")
    catalog["assets"][0]["occurrences"] = [
        {
            "anchor_cell": "B1",
            "column": 1,
            "height_px": 128,
            "row": 1,
            "sheet_name": "火屬性",
            "source_workbook_sha256": "a" * 64,
            "width_px": 128,
        }
    ]
    catalog["summary"]["asset_occurrence_count"] = 1
    catalog_path, asset_dir, _catalog_data = _write_library(tmp_path, catalog)

    with _client(catalog_path, asset_dir) as client:
        response = client.get("/api/v1/pve-library/stages")

    assert response.status_code == 503
    assert "anchor_cell" in response.json()["error"]["details"]["reason"]


def test_asset_directory_must_exactly_match_catalog_filenames(tmp_path: Path) -> None:
    catalog_path, asset_dir, _catalog_data = _write_library(tmp_path)
    (asset_dir / "unexpected.jpg").write_bytes(b"unexpected")

    with _client(catalog_path, asset_dir) as client:
        response = client.get("/api/v1/pve-library/stages")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PVE_LIBRARY_INVALID"


def test_missing_configured_files_are_structured_503s(tmp_path: Path) -> None:
    missing_catalog = tmp_path / "missing.json"
    missing_assets = tmp_path / "missing-assets"
    with _client(missing_catalog, missing_assets) as client:
        response = client.get("/api/v1/pve-library/stages")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PVE_LIBRARY_UNAVAILABLE"


def test_asset_digest_mismatch_fails_initial_load_closed(tmp_path: Path) -> None:
    catalog_path, asset_dir, catalog = _write_library(tmp_path)
    (asset_dir / catalog["assets"][0]["filename"]).write_bytes(b"tampered")

    with _client(catalog_path, asset_dir) as client:
        response = client.get("/api/v1/pve-library/stages")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PVE_LIBRARY_INVALID"
    assert "digest mismatch" in response.json()["error"]["details"]["reason"]


def test_unsafe_raw_source_url_is_not_exposed_as_clickable_url(tmp_path: Path) -> None:
    catalog = _catalog(b"fake-jpeg-portrait")
    team = catalog["sources"][0]["sheets"][0]["sections"][0]["teams"][0]
    team["source_refs"][0]["url"] = "javascript:alert(1)"
    team["axes"][0]["source_refs"][0]["url"] = "javascript:alert(1)"
    catalog_path, asset_dir, _catalog_data = _write_library(tmp_path, catalog)

    with _client(catalog_path, asset_dir) as client:
        response = client.get("/api/v1/pve-library/stages/deep:fire:01-01")

    assert response.status_code == 200
    returned_team = response.json()["data"]["teams"][0]
    assert returned_team["source_links"][0]["url"] is None
    assert returned_team["source_links"][0]["media"] is None
    assert returned_team["axes"][0]["source_links"][0]["url"] is None


def test_loaded_snapshot_becomes_unavailable_after_file_drift(tmp_path: Path) -> None:
    catalog_path, asset_dir, catalog = _write_library(tmp_path)
    with _client(catalog_path, asset_dir) as client:
        assert client.get("/api/v1/pve-library/stages").status_code == 200
        (asset_dir / catalog["assets"][0]["filename"]).write_bytes(b"changed-size")
        drift = client.get("/api/v1/pve-library/stages")
        (asset_dir / catalog["assets"][0]["filename"]).write_bytes(
            b"fake-jpeg-portrait"
        )
        still_drifted = client.get("/api/v1/pve-library/stages")

    assert drift.status_code == 503
    assert drift.json()["error"]["code"] == "PVE_LIBRARY_DRIFT"
    assert still_drifted.status_code == 503
    assert still_drifted.json()["error"]["code"] == "PVE_LIBRARY_DRIFT"


def test_loaded_snapshot_rejects_catalog_revision_drift(tmp_path: Path) -> None:
    catalog_path, asset_dir, _catalog_data = _write_library(tmp_path)
    with _client(catalog_path, asset_dir) as client:
        assert client.get("/api/v1/pve-library/stages").status_code == 200
        catalog_path.write_bytes(catalog_path.read_bytes() + b" ")
        drift = client.get("/api/v1/pve-library/stages")

    assert drift.status_code == 503
    assert drift.json()["error"]["code"] == "PVE_LIBRARY_DRIFT"


@pytest.mark.parametrize(
    ("url", "kind", "video_id"),
    [
        ("https://youtu.be/CnL5X4oPy_I?si=x", "YOUTUBE", "CnL5X4oPy_I"),
        (
            "https://www.youtube.com/watch?v=CnL5X4oPy_I",
            "YOUTUBE",
            "CnL5X4oPy_I",
        ),
        (
            "https://www.youtube.com/shorts/CnL5X4oPy_I",
            "YOUTUBE",
            "CnL5X4oPy_I",
        ),
        (
            "https://www.youtube.com/playlist?list=PL-safe-list",
            "EXTERNAL",
            None,
        ),
        (
            "https://www.youtube.com.evil.example/watch?v=CnL5X4oPy_I",
            "EXTERNAL",
            None,
        ),
        ("http://youtube.com/watch?v=CnL5X4oPy_I", "EXTERNAL", None),
    ],
)
def test_youtube_embed_metadata_is_allowlist_parsed(
    url: str,
    kind: str,
    video_id: str | None,
) -> None:
    media = media_for_url(url)
    assert media is not None
    assert media["kind"] == kind
    assert media["video_id"] == video_id
    if video_id is not None:
        assert media["embed_url"] == (
            f"https://www.youtube-nocookie.com/embed/{video_id}"
        )
    else:
        assert media["embed_url"] is None


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://user@example.com/watch?v=CnL5X4oPy_I",
        "not a url",
        None,
    ],
)
def test_unsafe_or_missing_source_url_has_no_clickable_media(url: str | None) -> None:
    assert media_for_url(url) is None
