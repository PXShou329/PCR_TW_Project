from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.sax.saxutils import escape

import pytest
from fastapi.testclient import TestClient

from pcr_api.config import Settings
from pcr_api.main import create_app


VALID_JPEG = b"\xff\xd8\xff\xe0private-gacha-image\xff\xd9"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_CANDIDATE_PATH = REPO_ROOT / ".runtime/gacha_forecast/docx-candidates.json"
REAL_DOCX_PATH = Path(
    os.getenv(
        "PCR_GACHA_REAL_DOCX_PATH",
        str(Path.home() / "Downloads" / "卡池未來視.docx"),
    )
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
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


def _docx_bytes(asset_bytes: bytes, *, relationship_target: str = "media/image1.jpeg") -> bytes:
    description = "限定UP角色「雪菲（瓦德拉赫）」"
    forecast = "台服預測2026/10/31～11/3"
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{W_NS}" xmlns:a="{A_NS}" xmlns:r="{R_NS}">'
        "<w:body>"
        f"<w:p><w:r><w:t>{escape(description)}</w:t></w:r></w:p>"
        f"<w:p><w:r><w:t>{escape(forecast)}</w:t></w:r></w:p>"
        '<w:p><w:r><w:drawing><a:blip r:embed="rId1"/>'
        "</w:drawing></w:r></w:p>"
        "<w:sectPr/>"
        "</w:body></w:document>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="{REL_NS}">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        f'Target="{escape(relationship_target)}"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Types xmlns="{CT_NS}">'
        '<Default Extension="jpeg" ContentType="image/jpeg"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/_rels/document.xml.rels", relationships)
        archive.writestr("word/media/image1.jpeg", asset_bytes)
    return output.getvalue()


def _rewrite_docx(
    payload: bytes,
    *,
    replacements: dict[str, bytes] | None = None,
    additions: dict[str, bytes] | None = None,
) -> bytes:
    with zipfile.ZipFile(io.BytesIO(payload)) as source:
        parts = {info.filename: source.read(info.filename) for info in source.infolist()}
    parts.update(replacements or {})
    parts.update(additions or {})
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for package_path, part in parts.items():
            archive.writestr(package_path, part)
    return output.getvalue()


def _write_content_addressed_docx(tmp_path: Path, payload: bytes) -> Path:
    result = tmp_path / f"{_sha256(payload)}.docx"
    result.write_bytes(payload)
    return result


def _catalog(document_bytes: bytes, asset_bytes: bytes) -> dict:
    document_sha256 = _sha256(document_bytes)
    image_sha256 = _sha256(asset_bytes)
    description_lines = ["限定UP角色「雪菲（瓦德拉赫）」"]
    identity_payload = {
        "description_lines": description_lines,
        "document_sha256": document_sha256,
        "forecast_end": "2026-11-03",
        "forecast_start": "2026-10-31",
        "image_sha256": image_sha256,
        "source_id": "GACHA-COMM-002",
        "source_locator": "word/document.xml#paragraph=2",
    }
    candidate_id = "GACHA-DOCX-" + _sha256(
        _canonical_json_bytes(identity_payload)
    )[:24]
    return {
        "candidates": [
            {
                "candidate_id": candidate_id,
                "date_boundary_semantics": "SOURCE_UNSPECIFIED",
                "description_locators": ["word/document.xml#paragraph=1"],
                "forecast_end": "2026-11-03",
                "forecast_start": "2026-10-31",
                "identity_status": "UNVERIFIED_COMMUNITY_NAME",
                "image": {
                    "byte_length": len(asset_bytes),
                    "filename": "image1.jpeg",
                    "mime_type": "image/jpeg",
                    "package_path": "word/media/image1.jpeg",
                    "relationship_id": "rId1",
                    "sha256": image_sha256,
                },
                "image_locator": "word/document.xml#paragraph=3;image=1",
                "parser_warnings": [],
                "precision": "DAY",
                "promotion_eligible": False,
                "proposed_event_id": None,
                "raw_character_names": ["雪菲（瓦德拉赫）"],
                "raw_description_lines": description_lines,
                "raw_forecast_text": "台服預測2026/10/31～11/3",
                "raw_sequence_label": None,
                "review_order": 1,
                "review_reason": "EXACT_EVENT_LINK_NOT_REVIEWED",
                "review_status": "PENDING",
                "source_declared_pool_kind": "LIMITED_PICKUP",
                "source_locator": "word/document.xml#paragraph=2",
            }
        ],
        "document": {
            "body_paragraph_count": 3,
            "comments_present": False,
            "referenced_image_count": 1,
            "table_count": 0,
            "tracked_changes_present": False,
        },
        "schema_version": "gacha-community-docx-candidates/v1",
        "source": {
            "authority": "COMMUNITY_FORECAST",
            "capture_method": "USER_SUPPLIED_DOCX",
            "document_byte_length": len(document_bytes),
            "document_sha256": document_sha256,
            "embedded_image_policy": "PROVENANCE_ONLY_NOT_TW_DATE_EVIDENCE",
            "independence_group": "GACHA-COMM-002",
            "source_id": "GACHA-COMM-002",
            "source_id_origin": "CALLER_DECLARED_NOT_DOCUMENT_CONTENT",
        },
        "summary": {
            "candidate_count": 1,
            "canonical_write_count": 0,
            "character_label_count": 1,
            "coverage_end": "2026-11-03",
            "coverage_start": "2026-10-31",
            "pool_kind_counts": {"LIMITED_PICKUP": 1},
            "review_status_counts": {"PENDING": 1},
            "unique_date_window_count": 1,
            "warning_counts": {},
        },
    }


def _write_library(
    tmp_path: Path,
    *,
    asset_bytes: bytes = VALID_JPEG,
    catalog: dict | None = None,
) -> tuple[Path, Path, dict]:
    document_bytes = _docx_bytes(asset_bytes)
    resolved_catalog = catalog or _catalog(document_bytes, asset_bytes)
    document_sha256 = _sha256(document_bytes)
    docx_path = tmp_path / f"{document_sha256}.docx"
    docx_path.write_bytes(document_bytes)
    catalog_path = tmp_path / "docx-candidates.json"
    catalog_path.write_bytes(_canonical_json_bytes(resolved_catalog))
    return catalog_path, docx_path, resolved_catalog


def _rewrite_catalog(path: Path, catalog: dict) -> None:
    path.write_bytes(_canonical_json_bytes(catalog))


def _client(catalog_path: Path | None, docx_path: Path | None) -> TestClient:
    def database_must_not_be_opened() -> None:
        raise AssertionError("Gacha library endpoints must not open a database session")

    return TestClient(
        create_app(
            settings=Settings(
                database_url="sqlite://",
                gacha_library_catalog_path=catalog_path,
                gacha_library_docx_path=docx_path,
            ),
            session_factory=database_must_not_be_opened,
        )
    )


def test_settings_require_catalog_and_docx_as_one_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="must be configured together"):
        Settings(
            database_url="sqlite://",
            gacha_library_catalog_path=Path("catalog.json"),
        )

    monkeypatch.setenv("PCR_DATABASE_URL", "sqlite://")
    monkeypatch.setenv("PCR_GACHA_LIBRARY_CATALOG_PATH", "catalog.json")
    monkeypatch.delenv("PCR_GACHA_LIBRARY_DOCX_PATH", raising=False)
    with pytest.raises(ValueError, match="must be configured together"):
        Settings.from_environment()

    monkeypatch.setenv("PCR_GACHA_LIBRARY_CATALOG_PATH", "  ")
    monkeypatch.setenv("PCR_GACHA_LIBRARY_DOCX_PATH", "\t")
    disabled = Settings.from_environment()
    assert disabled.gacha_library_catalog_path is None
    assert disabled.gacha_library_docx_path is None

    monkeypatch.setenv("PCR_GACHA_LIBRARY_CATALOG_PATH", "catalog.json")
    monkeypatch.setenv("PCR_GACHA_LIBRARY_DOCX_PATH", "a.docx")
    configured = Settings.from_environment()
    assert configured.gacha_library_catalog_path == Path("catalog.json")
    assert configured.gacha_library_docx_path == Path("a.docx")


def test_forecast_list_and_content_addressed_asset_are_read_only(
    tmp_path: Path,
) -> None:
    catalog_path, docx_path, catalog = _write_library(tmp_path)
    catalog_before = catalog_path.read_bytes()
    docx_before = docx_path.read_bytes()
    image_sha256 = catalog["candidates"][0]["image"]["sha256"]

    with _client(catalog_path, docx_path) as client:
        forecast_response = client.get("/api/v1/gacha-library/forecasts")
        asset_response = client.get(
            f"/api/v1/gacha-library/assets/{image_sha256}"
        )

    assert forecast_response.status_code == 200
    payload = forecast_response.json()
    assert payload["data"]["total"] == 1
    candidate = payload["data"]["items"][0]
    assert candidate["source_declared_pool_kind"] == "LIMITED_PICKUP"
    assert candidate["identity_status"] == "UNVERIFIED_COMMUNITY_NAME"
    assert candidate["promotion_eligible"] is False
    assert candidate["proposed_event_id"] is None
    assert candidate["image"]["asset_url"] == (
        f"/api/v1/gacha-library/assets/{image_sha256}"
    )
    assert payload["meta"]["source_id"] == "GACHA-COMM-002"
    assert payload["meta"]["independence_group"] == "GACHA-COMM-002"
    assert payload["meta"]["canonical_write_count"] == 0
    assert payload["meta"]["source_document"]["content_addressed_filename"] == (
        f"{catalog['source']['document_sha256']}.docx"
    )

    assert asset_response.status_code == 200
    assert asset_response.content == VALID_JPEG
    assert asset_response.headers["content-type"] == "image/jpeg"
    assert asset_response.headers["etag"] == f'"{image_sha256}"'
    assert asset_response.headers["cache-control"] == (
        "private, max-age=31536000, immutable"
    )
    assert catalog_path.read_bytes() == catalog_before
    assert docx_path.read_bytes() == docx_before


@pytest.mark.skipif(
    not REAL_CANDIDATE_PATH.is_file() or not REAL_DOCX_PATH.is_file(),
    reason="private real Gacha candidate inputs are not available",
)
def test_real_candidate_catalog_closes_over_content_addressed_docx(
    tmp_path: Path,
) -> None:
    document_bytes = REAL_DOCX_PATH.read_bytes()
    document_sha256 = _sha256(document_bytes)
    content_addressed_docx = tmp_path / f"{document_sha256}.docx"
    content_addressed_docx.write_bytes(document_bytes)

    with _client(REAL_CANDIDATE_PATH, content_addressed_docx) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["total"] == 17
    assert payload["meta"]["source_document"]["sha256"] == document_sha256
    assert payload["meta"]["source_id"] == "GACHA-COMM-002"
    assert all(
        item["review_status"] == "PENDING"
        and item["promotion_eligible"] is False
        and item["proposed_event_id"] is None
        for item in payload["data"]["items"]
    )


def test_unconfigured_library_is_structured_503_without_database_access() -> None:
    with _client(None, None) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GACHA_LIBRARY_NOT_CONFIGURED"


def test_unknown_or_malformed_asset_is_structured_404(tmp_path: Path) -> None:
    catalog_path, docx_path, _catalog_value = _write_library(tmp_path)
    with _client(catalog_path, docx_path) as client:
        unknown = client.get(f"/api/v1/gacha-library/assets/{'f' * 64}")
        malformed = client.get("/api/v1/gacha-library/assets/not-a-sha")

    assert unknown.status_code == 404
    assert malformed.status_code == 404
    assert unknown.json()["error"]["code"] == "GACHA_LIBRARY_NOT_FOUND"
    assert unknown.json()["error"]["details"]["resource"] == "gacha_asset"


@pytest.mark.parametrize(
    "case",
    [
        "extra_root_field",
        "summary_drift",
        "source_rebound",
        "candidate_extra_field",
        "pool_kind_drift",
        "raw_name_drift",
        "promotion_enabled",
        "candidate_id_drift",
    ],
)
def test_strict_catalog_and_cross_field_drift_fail_closed(
    tmp_path: Path,
    case: str,
) -> None:
    catalog_path, docx_path, catalog = _write_library(tmp_path)
    broken = deepcopy(catalog)
    candidate = broken["candidates"][0]
    if case == "extra_root_field":
        broken["unexpected"] = True
    elif case == "summary_drift":
        broken["summary"]["candidate_count"] = 2
    elif case == "source_rebound":
        broken["source"]["source_id"] = "GACHA-COMM-999"
        broken["source"]["independence_group"] = "GACHA-COMM-999"
    elif case == "candidate_extra_field":
        candidate["pool_kind"] = "LIMITED_PICKUP"
    elif case == "pool_kind_drift":
        candidate["source_declared_pool_kind"] = "RERUN"
        broken["summary"]["pool_kind_counts"] = {"RERUN": 1}
    elif case == "raw_name_drift":
        candidate["raw_character_names"] = ["猜測名稱"]
    elif case == "promotion_enabled":
        candidate["promotion_eligible"] = True
    elif case == "candidate_id_drift":
        candidate["candidate_id"] = "GACHA-DOCX-" + "0" * 24
    _rewrite_catalog(catalog_path, broken)

    with _client(catalog_path, docx_path) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GACHA_LIBRARY_INVALID"


def test_source_rebind_is_rejected_even_with_recomputed_candidate_id(
    tmp_path: Path,
) -> None:
    catalog_path, docx_path, catalog = _write_library(tmp_path)
    broken = deepcopy(catalog)
    rebound_source_id = "GACHA-COMM-999"
    broken["source"]["source_id"] = rebound_source_id
    broken["source"]["independence_group"] = rebound_source_id
    candidate = broken["candidates"][0]
    rebound_identity = {
        "description_lines": candidate["raw_description_lines"],
        "document_sha256": broken["source"]["document_sha256"],
        "forecast_end": candidate["forecast_end"],
        "forecast_start": candidate["forecast_start"],
        "image_sha256": candidate["image"]["sha256"],
        "source_id": rebound_source_id,
        "source_locator": candidate["source_locator"],
    }
    candidate["candidate_id"] = "GACHA-DOCX-" + _sha256(
        _canonical_json_bytes(rebound_identity)
    )[:24]
    _rewrite_catalog(catalog_path, broken)

    with _client(catalog_path, docx_path) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GACHA_LIBRARY_INVALID"
    assert "deterministic source DOCX replay" in (
        response.json()["error"]["details"]["reason"]
    )


def test_docx_must_use_its_lowercase_content_address(tmp_path: Path) -> None:
    catalog_path, docx_path, _catalog_value = _write_library(tmp_path)
    unsafe_name = tmp_path / "source.docx"
    unsafe_name.write_bytes(docx_path.read_bytes())

    with _client(catalog_path, unsafe_name) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GACHA_LIBRARY_INVALID"


def test_asset_must_close_over_zip_path_hash_length_and_magic(tmp_path: Path) -> None:
    catalog_path, docx_path, _catalog_value = _write_library(
        tmp_path,
        asset_bytes=b"not-an-image",
    )

    with _client(catalog_path, docx_path) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GACHA_LIBRARY_INVALID"
    assert "source DOCX replay was rejected" in (
        response.json()["error"]["details"]["reason"]
    )


def test_catalog_relationship_and_docx_locator_must_match(tmp_path: Path) -> None:
    catalog_path, docx_path, catalog = _write_library(tmp_path)
    broken = deepcopy(catalog)
    broken["candidates"][0]["image"]["relationship_id"] = "rId2"
    _rewrite_catalog(catalog_path, broken)

    with _client(catalog_path, docx_path) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GACHA_LIBRARY_INVALID"


def test_utf16_xml_with_dtd_is_rejected_before_parsing(tmp_path: Path) -> None:
    catalog_path, docx_path, _catalog_value = _write_library(tmp_path)
    utf16_document = (
        '<?xml version="1.0" encoding="UTF-16"?>'
        '<!DOCTYPE w:document [<!ENTITY xxe "forbidden">]>'
        f'<w:document xmlns:w="{W_NS}"><w:body><w:p><w:r>'
        "<w:t>&xxe;</w:t></w:r></w:p></w:body></w:document>"
    ).encode("utf-16")
    mutated = _rewrite_docx(
        docx_path.read_bytes(),
        replacements={"word/document.xml": utf16_document},
    )
    mutated_path = _write_content_addressed_docx(tmp_path, mutated)

    with _client(catalog_path, mutated_path) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    reason = response.json()["error"]["details"]["reason"]
    assert "UTF-8" in reason or "DTD" in reason


@pytest.mark.parametrize(
    "package_path",
    [
        "word/vbaProject.bin",
        "word/activeX/activeX1.bin",
        "word/embeddings/oleObject1.bin",
    ],
)
def test_active_macro_or_embedded_package_parts_are_rejected(
    tmp_path: Path,
    package_path: str,
) -> None:
    catalog_path, docx_path, _catalog_value = _write_library(tmp_path)
    mutated = _rewrite_docx(
        docx_path.read_bytes(), additions={package_path: b"active-content"}
    )
    mutated_path = _write_content_addressed_docx(tmp_path, mutated)

    with _client(catalog_path, mutated_path) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert "active, macro, or embedded" in (
        response.json()["error"]["details"]["reason"]
    )


def test_macro_enabled_content_type_is_rejected(tmp_path: Path) -> None:
    catalog_path, docx_path, _catalog_value = _write_library(tmp_path)
    with zipfile.ZipFile(docx_path) as archive:
        content_types = archive.read("[Content_Types].xml").decode("utf-8")
    macro_types = content_types.replace(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
        "application/vnd.ms-word.document.macroEnabled.main+xml",
    ).encode("utf-8")
    mutated = _rewrite_docx(
        docx_path.read_bytes(),
        replacements={"[Content_Types].xml": macro_types},
    )
    mutated_path = _write_content_addressed_docx(tmp_path, mutated)

    with _client(catalog_path, mutated_path) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert "macro-enabled content type" in (
        response.json()["error"]["details"]["reason"]
    )


def test_external_non_image_relationship_is_rejected(tmp_path: Path) -> None:
    catalog_path, docx_path, _catalog_value = _write_library(tmp_path)
    with zipfile.ZipFile(docx_path) as archive:
        relationships = archive.read(
            "word/_rels/document.xml.rels"
        ).decode("utf-8")
    external = relationships.replace(
        "</Relationships>",
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
        'Target="https://example.invalid/" TargetMode="External"/>'
        "</Relationships>",
    ).encode("utf-8")
    mutated = _rewrite_docx(
        docx_path.read_bytes(),
        replacements={"word/_rels/document.xml.rels": external},
    )
    mutated_path = _write_content_addressed_docx(tmp_path, mutated)

    with _client(catalog_path, mutated_path) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert "external DOCX relationships" in (
        response.json()["error"]["details"]["reason"]
    )


@pytest.mark.parametrize(
    ("element", "reason_fragment"),
    [
        ('<w:p><w:pPr><w:pPrChange w:id="1"/></w:pPr></w:p>', "tracked changes"),
        ('<w:p><w:commentRangeStart w:id="0"/></w:p>', "comments"),
        (
            '<w:p><w:r><w:rPr><w:vanish/></w:rPr><w:t>hidden</w:t></w:r></w:p>',
            "hidden DOCX text",
        ),
        ('<w:p><w:r><w:object/></w:r></w:p>', "active or embedded DOCX objects"),
    ],
)
def test_revision_comment_hidden_and_object_features_are_rejected(
    tmp_path: Path,
    element: str,
    reason_fragment: str,
) -> None:
    catalog_path, docx_path, _catalog_value = _write_library(tmp_path)
    with zipfile.ZipFile(docx_path) as archive:
        document = archive.read("word/document.xml").decode("utf-8")
    mutated_document = document.replace("<w:sectPr/>", element + "<w:sectPr/>").encode(
        "utf-8"
    )
    mutated = _rewrite_docx(
        docx_path.read_bytes(),
        replacements={"word/document.xml": mutated_document},
    )
    mutated_path = _write_content_addressed_docx(tmp_path, mutated)

    with _client(catalog_path, mutated_path) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert reason_fragment in response.json()["error"]["details"]["reason"]


@pytest.mark.parametrize(
    "raw_description",
    [
        "限定UP角色「雪菲（瓦德拉赫）」殘餘文字",
        "限定UP角色「雪菲（瓦德拉赫）」露易絲瑪莉（夏日）",
        "限定UP角色「雪菲（瓦德拉赫」",
    ],
)
def test_residual_mixed_or_unbalanced_character_text_is_rejected(
    tmp_path: Path,
    raw_description: str,
) -> None:
    catalog_path, docx_path, catalog = _write_library(tmp_path)
    broken = deepcopy(catalog)
    broken["candidates"][0]["raw_description_lines"] = [raw_description]
    _rewrite_catalog(catalog_path, broken)

    with _client(catalog_path, docx_path) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GACHA_LIBRARY_INVALID"


def test_non_strict_json_is_rejected(tmp_path: Path) -> None:
    catalog_path, docx_path, _catalog_value = _write_library(tmp_path)
    catalog_path.write_text(
        '{"schema_version":"gacha-community-docx-candidates/v1",'
        '"schema_version":"duplicate"}',
        encoding="utf-8",
    )

    with _client(catalog_path, docx_path) as client:
        response = client.get("/api/v1/gacha-library/forecasts")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GACHA_LIBRARY_INVALID"


@pytest.mark.parametrize("drift_target", ["catalog", "docx"])
def test_loaded_snapshot_fails_closed_after_input_drift(
    tmp_path: Path,
    drift_target: str,
) -> None:
    catalog_path, docx_path, _catalog_value = _write_library(tmp_path)
    with _client(catalog_path, docx_path) as client:
        first = client.get("/api/v1/gacha-library/forecasts")
        assert first.status_code == 200
        target = catalog_path if drift_target == "catalog" else docx_path
        target.write_bytes(target.read_bytes() + b"drift")
        drifted = client.get("/api/v1/gacha-library/forecasts")

    assert drifted.status_code == 503
    assert drifted.json()["error"]["code"] == "GACHA_LIBRARY_DRIFT"


def test_openapi_documents_private_gacha_success_and_error_contracts() -> None:
    with _client(None, None) as client:
        schema = client.get("/openapi.json").json()

    forecasts = schema["paths"]["/api/v1/gacha-library/forecasts"]["get"]
    assets = schema["paths"]["/api/v1/gacha-library/assets/{sha256}"]["get"]
    assert set(forecasts["responses"]) >= {"200", "503"}
    assert set(assets["responses"]) >= {"200", "404", "503", "422"}
