from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy

import pytest

from scripts import check_application_data_parity as verifier


@pytest.fixture(scope="module")
def live_openapi() -> dict:
    return verifier.load_openapi()


@pytest.fixture(scope="module")
def current_stats() -> dict:
    return verifier.load_stats()


def test_default_structural_verifier_reports_current_data_gate_block(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert verifier.main([]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert "APPLICATION_DATA_PARITY_STRUCTURAL_OK" in output.out
    assert "DATA_GATE_A=FAIL" in output.out
    assert "DATA_GATE_B=FAIL" in output.out
    assert "DATA_GATE_C=FAIL" in output.out
    assert "ROUND_TRIP=NOT_RUN" in output.out
    assert "RUNTIME_ACL=NOT_RUN" in output.out
    assert "UNIQUE_WRITER_RUNTIME=NOT_RUN" in output.out
    assert "ADMIN_AUTHORIZATION=NOT_RUN" in output.out
    assert "APPLICATION_GATE_D_STATUS=BLOCKED_BY_DATA_GATES" in output.out
    assert "APPLICATION_GATE_D_STATUS=PASS" not in output.out


def test_missing_required_response_metadata_fails_structural_verification(
    live_openapi: dict,
    current_stats: dict,
    capsys: pytest.CaptureFixture[str],
) -> None:
    drifted = deepcopy(live_openapi)
    drifted["components"]["schemas"]["ResponseMeta"]["required"].remove(
        "confidence"
    )

    result = verifier.main(
        [],
        openapi_loader=lambda: drifted,
        stats_loader=lambda: current_stats,
    )

    output = capsys.readouterr()
    assert result == 1
    assert "ResponseMeta v3 field is not required: confidence" in output.err
    assert "APPLICATION_GATE_D_STATUS=STRUCTURAL_FAILED" in output.out


@pytest.mark.parametrize(
    ("mutate", "expected_error"),
    [
        (
            lambda document: document["paths"].pop("/api/v1/pvp/characters"),
            "missing required PVP path: /api/v1/pvp/characters",
        ),
        (
            lambda document: document["paths"].pop("/api/v1/gacha/timeline"),
            "missing required Gacha path: /api/v1/gacha/timeline",
        ),
        (
            lambda document: document["paths"]["/api/v1/pvp/counters"].update(
                {"post": deepcopy(document["paths"]["/api/v1/pvp/counters"]["get"])}
            ),
            "public write method is forbidden: POST",
        ),
    ],
)
def test_missing_contract_or_public_write_method_fails_closed(
    live_openapi: dict,
    current_stats: dict,
    capsys: pytest.CaptureFixture[str],
    mutate: Callable[[dict], object],
    expected_error: str,
) -> None:
    drifted = deepcopy(live_openapi)
    mutate(drifted)

    result = verifier.main(
        [],
        openapi_loader=lambda: drifted,
        stats_loader=lambda: current_stats,
    )

    output = capsys.readouterr()
    assert result == 1
    assert expected_error in output.err
    assert "APPLICATION_GATE_D_STATUS=STRUCTURAL_FAILED" in output.out


def test_pvp_route_with_wrong_envelope_data_schema_fails_closed(
    live_openapi: dict,
    current_stats: dict,
    capsys: pytest.CaptureFixture[str],
) -> None:
    drifted = deepcopy(live_openapi)
    response_schema = drifted["paths"]["/api/v1/pvp/characters"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    response_schema["$ref"] = "#/components/schemas/Envelope_BaselineData_"

    result = verifier.main(
        [],
        openapi_loader=lambda: drifted,
        stats_loader=lambda: current_stats,
    )

    output = capsys.readouterr()
    assert result == 1
    assert (
        "/api/v1/pvp/characters: GET 200 data must be list[PvpCharacterData]"
        in output.err
    )
    assert "APPLICATION_GATE_D_STATUS=STRUCTURAL_FAILED" in output.out


@pytest.mark.parametrize(
    ("path", "expected_schema"),
    [
        ("/api/v1/gacha/timeline", "GachaTimelineEventData"),
        ("/api/v1/gacha/community-sources", "GachaCommunitySourceData"),
    ],
)
def test_gacha_route_with_wrong_envelope_data_schema_fails_closed(
    live_openapi: dict,
    current_stats: dict,
    capsys: pytest.CaptureFixture[str],
    path: str,
    expected_schema: str,
) -> None:
    drifted = deepcopy(live_openapi)
    response_schema = drifted["paths"][path]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    response_schema["$ref"] = "#/components/schemas/Envelope_BaselineData_"

    result = verifier.main(
        [],
        openapi_loader=lambda: drifted,
        stats_loader=lambda: current_stats,
    )

    output = capsys.readouterr()
    assert result == 1
    assert f"{path}: GET 200 data must be list[{expected_schema}]" in output.err
    assert "APPLICATION_GATE_D_STATUS=STRUCTURAL_FAILED" in output.out


@pytest.mark.parametrize(
    ("mutate", "expected_error"),
    [
        (
            lambda schema: schema["required"].remove("limited_claim_id"),
            "GachaTimelineEventData limited provenance is not required: "
            "limited_claim_id",
        ),
        (
            lambda schema: schema["properties"].pop("limited_claim_id"),
            "GachaTimelineEventData missing limited provenance property: "
            "limited_claim_id",
        ),
        (
            lambda schema: schema["properties"].update(
                {"limited_claim_id": {"type": "string"}}
            ),
            "GachaTimelineEventData.limited_claim_id must be nullable",
        ),
    ],
)
def test_gacha_limited_provenance_contract_fails_closed(
    live_openapi: dict,
    current_stats: dict,
    capsys: pytest.CaptureFixture[str],
    mutate: Callable[[dict], object],
    expected_error: str,
) -> None:
    drifted = deepcopy(live_openapi)
    mutate(drifted["components"]["schemas"]["GachaTimelineEventData"])

    result = verifier.main(
        [],
        openapi_loader=lambda: drifted,
        stats_loader=lambda: current_stats,
    )

    output = capsys.readouterr()
    assert result == 1
    assert expected_error in output.err
    assert "APPLICATION_GATE_D_STATUS=STRUCTURAL_FAILED" in output.out


def test_admin_is_out_of_scope_and_allowlisted_compute_post_is_read_only(
    live_openapi: dict,
    current_stats: dict,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expanded = deepcopy(live_openapi)
    envelope_post = deepcopy(expanded["paths"]["/api/v1/pvp/counters"]["get"])
    expanded["paths"]["/api/v1/admin/reviews"] = {"post": {}}
    expanded["paths"]["/api/v1/solver/pve"] = {"post": envelope_post}

    result = verifier.main(
        [],
        openapi_loader=lambda: expanded,
        stats_loader=lambda: current_stats,
    )

    output = capsys.readouterr()
    assert result == 0
    assert output.err == ""
    assert "APPLICATION_DATA_PARITY_STRUCTURAL_OK" in output.out
    assert "ADMIN_AUTHORIZATION=NOT_RUN" in output.out
    assert "APPLICATION_GATE_D_STATUS=BLOCKED_BY_DATA_GATES" in output.out


def test_personal_gacha_post_is_not_compute_allowlisted(
    live_openapi: dict,
    current_stats: dict,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expanded = deepcopy(live_openapi)
    expanded["paths"]["/api/v1/gacha/gem-scenario"] = {
        "post": deepcopy(expanded["paths"]["/api/v1/gacha/timeline"]["get"])
    }

    result = verifier.main(
        [],
        openapi_loader=lambda: expanded,
        stats_loader=lambda: current_stats,
    )

    output = capsys.readouterr()
    assert result == 1
    assert (
        "/api/v1/gacha/gem-scenario: public write method is forbidden: POST"
        in output.err
    )
    assert "APPLICATION_GATE_D_STATUS=STRUCTURAL_FAILED" in output.out


def test_require_pass_exits_one_while_data_gates_are_blocked(
    live_openapi: dict,
    current_stats: dict,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = verifier.main(
        ["--require-pass"],
        openapi_loader=lambda: live_openapi,
        stats_loader=lambda: current_stats,
    )

    output = capsys.readouterr()
    assert result == 1
    assert "APPLICATION_DATA_PARITY_STRUCTURAL_OK" in output.out
    assert "APPLICATION_GATE_D_STATUS=BLOCKED_BY_DATA_GATES" in output.out


def test_round_trip_flag_reuses_baseline_enabled_smoke(
    live_openapi: dict,
    current_stats: dict,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[dict[str, bool]] = []

    def fake_round_trip(**kwargs) -> dict:
        calls.append(kwargs)
        return {"status": "ROUND_TRIP_OK"}

    result = verifier.main(
        ["--run-round-trip"],
        openapi_loader=lambda: live_openapi,
        stats_loader=lambda: current_stats,
        round_trip_runner=fake_round_trip,
    )

    output = capsys.readouterr()
    assert result == 0
    assert calls == [{"run_baseline": True}]
    assert "ROUND_TRIP=ROUND_TRIP_OK" in output.out
    assert "APPLICATION_GATE_D_STATUS=BLOCKED_BY_DATA_GATES" in output.out
