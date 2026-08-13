from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from pcr_pipeline.gacha_ingest.cli import main, write_atomic
from pcr_pipeline.gacha_ingest.docx import (
    CANDIDATE_SCHEMA_VERSION,
    GachaDocxError,
    canonical_json_bytes,
    extract_gacha_forecast_docx,
)


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"


def _paragraph(text: str, *, fragmented: bool = True) -> str:
    fragments = [text[index : index + 2] for index in range(0, len(text), 2)]
    if not fragmented:
        fragments = [text]
    runs = "".join(f"<w:r><w:t>{escape(value)}</w:t></w:r>" for value in fragments)
    return f"<w:p>{runs}</w:p>"


def _image_paragraph(relationship_id: str) -> str:
    return (
        "<w:p><w:r><w:drawing><a:blip r:embed=\""
        f"{relationship_id}"
        "\"/></w:drawing></w:r></w:p>"
    )


def _jpeg(payload: bytes) -> bytes:
    return b"\xff\xd8\xff\xe0" + payload + b"\xff\xd9"


def _write_docx(
    path: Path,
    blocks: list[tuple[list[str], str, bytes]],
    *,
    comments: bool = False,
    external_first_image: bool = False,
    include_table: bool = False,
    missing_last_image: bool = False,
    tracked_changes: bool = False,
    target_names: list[str] | None = None,
) -> None:
    paragraphs: list[str] = []
    relationships: list[str] = []
    images: list[tuple[str, bytes]] = []
    for index, (descriptions, forecast, image_bytes) in enumerate(blocks, start=1):
        paragraphs.extend(_paragraph(value) for value in descriptions)
        paragraphs.append(_paragraph(forecast))
        relationship_id = f"rId{index}"
        paragraphs.append(_image_paragraph(relationship_id))
        target_name = (
            target_names[index - 1]
            if target_names is not None
            else f"image{index}.jpeg"
        )
        if external_first_image and index == 1:
            relationships.append(
                f'<Relationship Id="{relationship_id}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                'Target="https://example.invalid/image.jpeg" TargetMode="External"/>'
            )
        else:
            relationships.append(
                f'<Relationship Id="{relationship_id}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                f'Target="media/{target_name}"/>'
            )
            if not (missing_last_image and index == len(blocks)):
                images.append((target_name, _jpeg(image_bytes)))
    body = "".join(paragraphs)
    if tracked_changes:
        body = f'<w:ins w:id="1">{body}</w:ins>'
    if include_table:
        body += "<w:tbl><w:tr><w:tc><w:p/></w:tc></w:tr></w:tbl>"
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{W_NS}" xmlns:a="{A_NS}" xmlns:r="{R_NS}">'
        f"<w:body>{body}<w:sectPr/></w:body></w:document>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="{REL_NS}">'
        f"{''.join(relationships)}</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Types xmlns="{CT_NS}">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="jpeg" ContentType="image/jpeg"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/_rels/document.xml.rels", rels)
        for target_name, image_bytes in images:
            archive.writestr(f"word/media/{target_name}", image_bytes)
        if comments:
            archive.writestr(
                "word/comments.xml",
                f'<w:comments xmlns:w="{W_NS}"/>',
            )


def _fixture_blocks() -> list[tuple[list[str], str, bytes]]:
    return [
        (
            ["限定UP角色「雪菲（瓦德拉赫）」"],
            "台服預測2026/10/31～11/3",
            b"first-image",
        ),
        (
            [
                "「咲戀（夏日）」「真步（夢想樂園）」「伊莉亞（祭服）」",
                "鈴奈（夏日）鈴莓（夏日）珠希（夏日）凱留（夏日）",
                "「貪吃佩可（夏日）」復刻池",
            ],
            "台服預測2026/10/23～10/31",
            b"second-image",
        ),
        (
            ["第144次限定UP角色「克蕾琪塔（夏日）」"],
            "台服預測2026/11/15～12/1",
            b"third-image",
        ),
    ]


def _sanitized_full_document_blocks() -> list[tuple[list[str], str, bytes]]:
    rows = [
        (["「步未(怪盜)」「真琴(指揮官)」「可可蘿(遊俠)」復刻池"], "2026/8/1～8/16"),
        (["限定UP角色「鏡華（歌德）」"], "2026/8/11～8/23"),
        (["「克蘿茜(風靈)」「碧(駕駛員)」「鳳凰」", "「美冬(工作服)」「碧(工作服)」復刻池"], "2026/8/16～8/31"),
        (["限定UP角色「凱留（霸瞳天星）」"], "2026/8/23～8/31"),
        (["限定UP角色「真穗（少女與戰車）」"], "2026/8/31～9/22"),
        (["限定UP角色「艾麗卡（少女與戰車）」"], "2026/9/11～9/22"),
        (["常駐角色「露露伊」"], "2026/9/22～10/1"),
        (["「鏡華(春日)」「碧卡拉」「吉塔(魔導士)」復刻池"], "2026/9/22～10/1"),
        (["限定UP角色「莉莉（女武神）」"], "2026/10/1～10/11"),
        (["限定UP角色「普蕾希亞（女武神）」"], "2026/10/11～10/23"),
        (["「彩羽」「霞（修女）」「華音」「紡希（煉獄）」復刻池"], "2026/10/11～10/23"),
        (["限定UP角色「可璃亞（女武神）」"], "2026/10/23～10/31"),
        (["「咲戀（夏日）」「真步（夢想樂園）」「伊莉亞（祭服）」", "鈴奈（夏日）鈴莓（夏日）珠希（夏日）凱留（夏日）", "「貪吃佩可（夏日）」復刻池"], "2026/10/23～10/31"),
        (["限定UP角色「雪菲（瓦德拉赫）」"], "2026/10/31～11/3"),
        (["限定UP角色「露易絲瑪莉（夏日）」"], "2026/11/3～11/15"),
        (["「優依（聖誕節）」「美空（聖誕節）」「普蕾西亞(夏日)」", "「雪菲(夏日)」「厄莉絲(夏日)」復刻池"], "2026/11/3～11/15"),
        (["第144次限定UP角色「克蕾琪塔（夏日）」"], "2026/11/15～12/1"),
    ]
    return [
        (descriptions, f"台服預測{forecast}", f"image-{index}".encode("ascii"))
        for index, (descriptions, forecast) in enumerate(rows, start=1)
    ]


def test_extracts_fragmented_runs_multiline_rerun_and_exact_image_relationships(
    tmp_path: Path,
) -> None:
    source = tmp_path / "forecast.docx"
    _write_docx(
        source,
        _fixture_blocks(),
        target_names=["image10.jpeg", "image2.jpeg", "image1.jpeg"],
    )

    result = extract_gacha_forecast_docx(source, source_id="GACHA-COMM-002")

    assert result["schema_version"] == CANDIDATE_SCHEMA_VERSION
    assert result["source"]["document_sha256"] == hashlib.sha256(
        source.read_bytes()
    ).hexdigest()
    assert result["summary"] == {
        "candidate_count": 3,
        "canonical_write_count": 0,
        "character_label_count": 10,
        "coverage_end": "2026-12-01",
        "coverage_start": "2026-10-23",
        "pool_kind_counts": {"LIMITED_PICKUP": 2, "RERUN": 1},
        "review_status_counts": {"PENDING": 3},
        "unique_date_window_count": 3,
        "warning_counts": {"UNQUOTED_CHARACTER_SEQUENCE": 1},
    }
    first, rerun, last = result["candidates"]
    assert first["forecast_start"] == "2026-10-31"
    assert first["forecast_end"] == "2026-11-03"
    assert first["image"]["filename"] == "image10.jpeg"
    assert first["image"]["sha256"] == hashlib.sha256(
        _jpeg(b"first-image")
    ).hexdigest()
    assert rerun["raw_character_names"] == [
        "咲戀（夏日）",
        "真步（夢想樂園）",
        "伊莉亞（祭服）",
        "鈴奈（夏日）",
        "鈴莓（夏日）",
        "珠希（夏日）",
        "凱留（夏日）",
        "貪吃佩可（夏日）",
    ]
    assert rerun["parser_warnings"] == ["UNQUOTED_CHARACTER_SEQUENCE"]
    assert rerun["review_reason"] == "UNDELIMITED_CHARACTER_TEXT_REQUIRES_REVIEW"
    assert last["raw_sequence_label"] == "第144次"
    assert all(candidate["proposed_event_id"] is None for candidate in result["candidates"])
    assert not any(candidate["promotion_eligible"] for candidate in result["candidates"])
    assert all(
        candidate["identity_status"] == "UNVERIFIED_COMMUNITY_NAME"
        for candidate in result["candidates"]
    )


def test_repeat_extraction_is_byte_identical(tmp_path: Path) -> None:
    source = tmp_path / "forecast.docx"
    _write_docx(source, _fixture_blocks())

    first = extract_gacha_forecast_docx(source, source_id="GACHA-COMM-002")
    second = extract_gacha_forecast_docx(source, source_id="GACHA-COMM-002")

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert [item["candidate_id"] for item in first["candidates"]] == [
        item["candidate_id"] for item in second["candidates"]
    ]


def test_sanitized_full_document_shape_matches_real_checkpoint(tmp_path: Path) -> None:
    source = tmp_path / "forecast.docx"
    _write_docx(source, _sanitized_full_document_blocks())

    result = extract_gacha_forecast_docx(source, source_id="GACHA-COMM-002")

    assert result["summary"] == {
        "candidate_count": 17,
        "canonical_write_count": 0,
        "character_label_count": 39,
        "coverage_end": "2026-12-01",
        "coverage_start": "2026-08-01",
        "pool_kind_counts": {
            "LIMITED_PICKUP": 10,
            "PERMANENT_PICKUP": 1,
            "RERUN": 6,
        },
        "review_status_counts": {"PENDING": 17},
        "unique_date_window_count": 13,
        "warning_counts": {"UNQUOTED_CHARACTER_SEQUENCE": 1},
    }
    assert [len(item["raw_character_names"]) for item in result["candidates"]] == [
        3,
        1,
        5,
        1,
        1,
        1,
        1,
        3,
        1,
        1,
        4,
        1,
        8,
        1,
        1,
        5,
        1,
    ]
    assert [item["raw_sequence_label"] for item in result["candidates"][:-1]] == [
        None
    ] * 16
    assert result["candidates"][-1]["raw_sequence_label"] == "第144次"


def test_candidate_identity_is_bound_to_declared_source_id(tmp_path: Path) -> None:
    source = tmp_path / "forecast.docx"
    _write_docx(source, _fixture_blocks())

    first = extract_gacha_forecast_docx(source, source_id="GACHA-COMM-002")
    rebound = extract_gacha_forecast_docx(source, source_id="GACHA-COMM-999")

    assert [item["candidate_id"] for item in first["candidates"]] != [
        item["candidate_id"] for item in rebound["candidates"]
    ]


@pytest.mark.parametrize(
    ("builder_options", "message"),
    (
        ({"comments": True}, "comments must be removed"),
        ({"external_first_image": True}, "external DOCX relationships"),
        ({"include_table": True}, "table-based forecast layouts"),
        ({"missing_last_image": True}, "embedded image part is missing"),
        ({"tracked_changes": True}, "tracked changes must be accepted"),
    ),
)
def test_unsupported_or_unverifiable_docx_features_fail_closed(
    tmp_path: Path,
    builder_options: dict[str, bool],
    message: str,
) -> None:
    source = tmp_path / "forecast.docx"
    _write_docx(source, _fixture_blocks(), **builder_options)

    with pytest.raises(GachaDocxError, match=message):
        extract_gacha_forecast_docx(source, source_id="GACHA-COMM-002")


@pytest.mark.parametrize(
    ("description", "forecast", "message"),
    (
        ("角色「未知」", "台服預測2026/8/1～8/2", "pool kind is not explicit"),
        (
            "限定UP角色「未知」復刻池",
            "台服預測2026/8/1～8/2",
            "pool kind markers are ambiguous",
        ),
        (
            "限定UP角色「未知」",
            "台服預測2026/2/30～3/2",
            "invalid calendar date",
        ),
        (
            "限定UP角色「未知」",
            "台服預測2026/12/30～1/2",
            "cross-year ranges must state the end year",
        ),
        (
            "「角色A」角色B（夏日）復刻池",
            "台服預測2026/8/1～8/2",
            "mixed quoted and unquoted character text",
        ),
        (
            "「角色A」「角色B復刻池",
            "台服預測2026/8/1～8/2",
            "unbalanced character quote",
        ),
        (
            "「角色A（夏日」復刻池",
            "台服預測2026/8/1～8/2",
            "unbalanced character punctuation",
        ),
    ),
)
def test_ambiguous_pool_or_date_text_fails_closed(
    tmp_path: Path,
    description: str,
    forecast: str,
    message: str,
) -> None:
    source = tmp_path / "forecast.docx"
    _write_docx(source, [([description], forecast, b"image")])

    with pytest.raises(GachaDocxError, match=message):
        extract_gacha_forecast_docx(source, source_id="GACHA-COMM-002")


def test_cli_writes_canonical_json_without_touching_source(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "forecast.docx"
    output = tmp_path / "candidates.json"
    _write_docx(source, _fixture_blocks())
    source_before = source.read_bytes()

    assert (
        main(
            [
                "--input",
                str(source),
                "--source-id",
                "GACHA-COMM-002",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    assert source.read_bytes() == source_before
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert output.read_bytes() == canonical_json_bytes(parsed)
    assert json.loads(capsys.readouterr().out)["candidate_count"] == 3


def test_utf16_xml_and_entity_declarations_fail_before_xml_parsing(
    tmp_path: Path,
) -> None:
    source = tmp_path / "forecast.docx"
    _write_docx(source, _fixture_blocks())
    rewritten = tmp_path / "utf16.docx"
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(
        rewritten, "w", compression=zipfile.ZIP_DEFLATED
    ) as output:
        for info in original.infolist():
            payload = original.read(info.filename)
            if info.filename == "word/document.xml":
                text = payload.decode("utf-8")
                text = text.replace(
                    "?>",
                    "?><!DOCTYPE w:document [<!ENTITY injected 'EXPANDED'>]>",
                    1,
                ).replace("限定UP角色", "&injected;限定UP角色", 1)
                payload = text.replace('encoding="UTF-8"', 'encoding="UTF-16"').encode(
                    "utf-16"
                )
            output.writestr(info.filename, payload)

    with pytest.raises(GachaDocxError, match="must use UTF-8 encoding"):
        extract_gacha_forecast_docx(rewritten, source_id="GACHA-COMM-002")


def test_atomic_write_failure_preserves_existing_output_and_removes_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "candidates.json"
    output.write_bytes(b"existing")

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr("pcr_pipeline.gacha_ingest.cli.os.replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        write_atomic(output, b"replacement")

    assert output.read_bytes() == b"existing"
    assert list(tmp_path.glob(".candidates.json.*.tmp")) == []
