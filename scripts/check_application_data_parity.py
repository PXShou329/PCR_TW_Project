#!/usr/bin/env python3
"""Verify the structural, data-gated subset of Application Gate D.

This command deliberately does not execute PostgreSQL ACL or unique-writer
runtime probes.  It must therefore never report Gate D as passed on its own.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for package_root in ("apps/api", "data_pipeline", "database"):
    resolved = str(REPOSITORY_ROOT / package_root)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

STATS_PATH = REPOSITORY_ROOT / "research_core/pcr_tw_project/tools/stats.json"
PUBLIC_STRATEGY_PREFIX = "/api/v1/"
LOCAL_FILE_LIBRARY_PREFIXES = (
    "/api/v1/gacha-library",
    "/api/v1/pve-library",
)
REQUIRED_PVP_DATA_SCHEMAS = {
    "/api/v1/pvp/characters": "PvpCharacterData",
    "/api/v1/pvp/counters": "ArenaCounterData",
}
REQUIRED_PVP_PATHS = frozenset(REQUIRED_PVP_DATA_SCHEMAS)
REQUIRED_PVP_SCHEMAS = frozenset(REQUIRED_PVP_DATA_SCHEMAS.values())
REQUIRED_GACHA_DATA_SCHEMAS = {
    "/api/v1/gacha/timeline": "GachaTimelineEventData",
    "/api/v1/gacha/community-sources": "GachaCommunitySourceData",
}
REQUIRED_GACHA_PATHS = frozenset(REQUIRED_GACHA_DATA_SCHEMAS)
REQUIRED_GACHA_SCHEMAS = frozenset(REQUIRED_GACHA_DATA_SCHEMAS.values())
REQUIRED_GACHA_LIMITED_PROVENANCE_FIELDS = frozenset(
    {"limited_status", "limited_claim_id"}
)
REQUIRED_LIST_DATA_SCHEMAS = {
    **REQUIRED_PVP_DATA_SCHEMAS,
    **REQUIRED_GACHA_DATA_SCHEMAS,
}
V3_RESPONSE_META_FIELDS = frozenset(
    {
        "server",
        "environment_version",
        "verified_at",
        "stale_status",
        "confidence",
        "evidence_ids",
        "claim_ids",
        "data_revision",
    }
)
READ_ONLY_COMPUTE_POST_PATHS = frozenset(
    {
        "/api/v1/solver/pve",
        "/api/v1/solver/pvp",
        "/api/v1/solver/parena",
    }
)
STATE_CHANGING_METHODS = frozenset({"put", "patch", "delete"})

JsonObject = dict[str, Any]
OpenApiLoader = Callable[[], JsonObject]
StatsLoader = Callable[[], JsonObject]
RoundTripRunner = Callable[..., dict[str, Any]]


def load_openapi() -> JsonObject:
    """Build OpenAPI from the live FastAPI app without opening a database."""

    database_url = "sqlite+pysqlite:///:memory:"
    previous_database_url = os.environ.get("PCR_DATABASE_URL")
    if previous_database_url is None:
        os.environ["PCR_DATABASE_URL"] = database_url
    try:
        from pcr_api.config import Settings
        from pcr_api.main import create_app
    finally:
        if previous_database_url is None:
            os.environ.pop("PCR_DATABASE_URL", None)

    return create_app(settings=Settings(database_url=database_url)).openapi()


def load_stats() -> JsonObject:
    with STATS_PATH.open(encoding="utf-8") as stream:
        document = json.load(stream)
    if not isinstance(document, dict):
        raise ValueError("stats root must be an object")
    return document


def run_required_round_trip(**kwargs: Any) -> dict[str, Any]:
    from pcr_pipeline.verify_round_trip import run_round_trip_smoke

    return run_round_trip_smoke(**kwargs)


def _component_name(reference: object) -> str | None:
    prefix = "#/components/schemas/"
    if not isinstance(reference, str) or not reference.startswith(prefix):
        return None
    name = reference.removeprefix(prefix)
    return name or None


def _mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _allows_null(schema: Mapping[str, Any]) -> bool:
    schema_type = schema.get("type")
    if schema_type == "null" or (
        isinstance(schema_type, list) and "null" in schema_type
    ):
        return True
    alternatives = schema.get("anyOf") or schema.get("oneOf") or []
    return isinstance(alternatives, list) and any(
        _allows_null(candidate)
        for candidate in alternatives
        if isinstance(candidate, Mapping)
    )


def _is_admin_path(path: str) -> bool:
    return path == "/api/v1/admin" or path.startswith("/api/v1/admin/")


def _is_local_file_library_path(path: str) -> bool:
    return any(
        path == prefix or path.startswith(f"{prefix}/")
        for prefix in LOCAL_FILE_LIBRARY_PREFIXES
    )


def _validate_envelope_response(
    *,
    path: str,
    method: str,
    operation: Mapping[str, Any],
    schemas: Mapping[str, Any],
    errors: list[str],
    expected_list_item_schema: str | None = None,
) -> None:
    responses = _mapping(operation.get("responses"))
    response = _mapping(responses.get("200")) if responses else None
    content = _mapping(response.get("content")) if response else None
    media_type = _mapping(content.get("application/json")) if content else None
    response_schema = _mapping(media_type.get("schema")) if media_type else None
    envelope_name = _component_name(response_schema.get("$ref")) if response_schema else None
    label = f"{path}: {method.upper()} 200"
    if envelope_name is None or not envelope_name.startswith("Envelope_"):
        errors.append(f"{label} must reference an Envelope component")
        return
    envelope = _mapping(schemas.get(envelope_name))
    if envelope is None:
        errors.append(f"{path}: missing envelope component {envelope_name}")
        return
    envelope_properties = _mapping(envelope.get("properties"))
    envelope_required = envelope.get("required")
    if not isinstance(envelope_required, list) or not {"data", "meta"}.issubset(
        set(envelope_required)
    ):
        errors.append(f"{path}: envelope must require data and meta")
    meta_schema = (
        _mapping(envelope_properties.get("meta"))
        if envelope_properties is not None
        else None
    )
    if meta_schema is None or meta_schema.get("$ref") != (
        "#/components/schemas/ResponseMeta"
    ):
        errors.append(f"{path}: envelope meta must reference ResponseMeta")
    if expected_list_item_schema is not None:
        data_schema = (
            _mapping(envelope_properties.get("data"))
            if envelope_properties is not None
            else None
        )
        items = _mapping(data_schema.get("items")) if data_schema else None
        item_schema = _component_name(items.get("$ref")) if items else None
        if (
            data_schema is None
            or data_schema.get("type") != "array"
            or item_schema != expected_list_item_schema
        ):
            errors.append(
                f"{label} data must be list[{expected_list_item_schema}]"
            )


def validate_openapi(document: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    paths = _mapping(document.get("paths"))
    components_root = _mapping(document.get("components"))
    schemas = _mapping(components_root.get("schemas")) if components_root else None
    if paths is None:
        return ["OpenAPI paths must be an object"]
    if schemas is None:
        return ["OpenAPI components.schemas must be an object"]

    strategy_paths = {
        path: item
        for path, item in paths.items()
        if isinstance(path, str)
        and path.startswith(PUBLIC_STRATEGY_PREFIX)
        and not _is_admin_path(path)
    }
    public_paths = {
        path: item
        for path, item in strategy_paths.items()
        if not _is_local_file_library_path(path)
    }
    if not public_paths:
        errors.append("no public /api/v1/* strategy paths")

    for path, raw_path_item in sorted(strategy_paths.items()):
        path_item = _mapping(raw_path_item)
        if path_item is None:
            errors.append(f"{path}: path item must be an object")
            continue
        for method in sorted(STATE_CHANGING_METHODS & set(path_item)):
            errors.append(f"{path}: public write method is forbidden: {method.upper()}")
        post = _mapping(path_item.get("post"))
        if post is not None and path not in READ_ONLY_COMPUTE_POST_PATHS:
            errors.append(f"{path}: public write method is forbidden: POST")
        if _is_local_file_library_path(path) and _mapping(path_item.get("get")) is None:
            errors.append(f"{path}: local file library path must define GET")

    for missing in sorted(REQUIRED_PVP_PATHS - set(public_paths)):
        errors.append(f"missing required PVP path: {missing}")
    for missing in sorted(REQUIRED_PVP_SCHEMAS - set(schemas)):
        errors.append(f"missing required PVP schema: {missing}")
    for missing in sorted(REQUIRED_GACHA_PATHS - set(public_paths)):
        errors.append(f"missing required Gacha path: {missing}")
    for missing in sorted(REQUIRED_GACHA_SCHEMAS - set(schemas)):
        errors.append(f"missing required Gacha schema: {missing}")

    gacha_timeline = _mapping(schemas.get("GachaTimelineEventData"))
    if gacha_timeline is not None:
        properties = _mapping(gacha_timeline.get("properties"))
        required = gacha_timeline.get("required")
        property_names = set(properties) if properties is not None else set()
        required_names = set(required) if isinstance(required, list) else set()
        for field in sorted(REQUIRED_GACHA_LIMITED_PROVENANCE_FIELDS - property_names):
            errors.append(
                f"GachaTimelineEventData missing limited provenance property: {field}"
            )
        for field in sorted(REQUIRED_GACHA_LIMITED_PROVENANCE_FIELDS - required_names):
            errors.append(
                f"GachaTimelineEventData limited provenance is not required: {field}"
            )
        limited_claim = (
            _mapping(properties.get("limited_claim_id"))
            if properties is not None
            else None
        )
        if limited_claim is not None and not _allows_null(limited_claim):
            errors.append("GachaTimelineEventData.limited_claim_id must be nullable")

    for path, raw_path_item in sorted(public_paths.items()):
        path_item = _mapping(raw_path_item)
        if path_item is None:
            errors.append(f"{path}: path item must be an object")
            continue
        post = _mapping(path_item.get("post"))
        get = _mapping(path_item.get("get"))
        if get is None and not (
            path in READ_ONLY_COMPUTE_POST_PATHS and post is not None
        ):
            errors.append(f"{path}: public strategy path must define GET")
        if get is not None:
            _validate_envelope_response(
                path=path,
                method="get",
                operation=get,
                schemas=schemas,
                errors=errors,
                expected_list_item_schema=REQUIRED_LIST_DATA_SCHEMAS.get(path),
            )
        if post is not None and path in READ_ONLY_COMPUTE_POST_PATHS:
            _validate_envelope_response(
                path=path,
                method="post",
                operation=post,
                schemas=schemas,
                errors=errors,
            )

    response_meta = _mapping(schemas.get("ResponseMeta"))
    if response_meta is None:
        errors.append("missing ResponseMeta schema")
        return errors
    properties = _mapping(response_meta.get("properties"))
    required = response_meta.get("required")
    property_names = set(properties) if properties is not None else set()
    required_names = set(required) if isinstance(required, list) else set()
    for field in sorted(V3_RESPONSE_META_FIELDS - property_names):
        errors.append(f"ResponseMeta missing v3 property: {field}")
    for field in sorted(V3_RESPONSE_META_FIELDS - required_names):
        errors.append(f"ResponseMeta v3 field is not required: {field}")
    return errors


def read_data_gates(stats: Mapping[str, Any]) -> tuple[dict[str, bool], list[str]]:
    errors: list[str] = []
    gate = _mapping(stats.get("gate"))
    if gate is None:
        return {}, ["stats.gate must be an object"]
    values: dict[str, bool] = {}
    for name in ("gate_a", "gate_b", "gate_c"):
        value = gate.get(name)
        if not isinstance(value, bool):
            errors.append(f"stats.gate.{name} must be boolean")
            continue
        values[name] = value
    return values, errors


def _print_errors(errors: Sequence[str]) -> None:
    for error in errors:
        print(f"APPLICATION_DATA_PARITY_ERROR={error}", file=sys.stderr)


def _print_runtime_evidence_status() -> None:
    print("RUNTIME_ACL=NOT_RUN")
    print("UNIQUE_WRITER_RUNTIME=NOT_RUN")
    print("ADMIN_AUTHORIZATION=NOT_RUN")


def main(
    argv: Sequence[str] | None = None,
    *,
    openapi_loader: OpenApiLoader = load_openapi,
    stats_loader: StatsLoader = load_stats,
    round_trip_runner: RoundTripRunner = run_required_round_trip,
) -> int:
    parser = argparse.ArgumentParser(
        description="Verify structural Application/Data parity without claiming Gate D"
    )
    parser.add_argument("--run-round-trip", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    arguments = parser.parse_args(argv)

    try:
        openapi = openapi_loader()
        stats = stats_loader()
    except (OSError, ValueError, RuntimeError) as error:
        _print_errors([str(error)])
        _print_runtime_evidence_status()
        print("APPLICATION_GATE_D_STATUS=STRUCTURAL_FAILED")
        return 1

    structural_errors = validate_openapi(openapi)
    gates, gate_errors = read_data_gates(stats)
    structural_errors.extend(gate_errors)
    if structural_errors:
        _print_errors(structural_errors)
        _print_runtime_evidence_status()
        print("APPLICATION_GATE_D_STATUS=STRUCTURAL_FAILED")
        return 1

    print("APPLICATION_DATA_PARITY_STRUCTURAL_OK")
    for name in ("gate_a", "gate_b", "gate_c"):
        print(f"DATA_{name.upper()}={'PASS' if gates[name] else 'FAIL'}")

    if arguments.run_round_trip:
        try:
            round_trip = round_trip_runner(run_baseline=True)
        except (OSError, RuntimeError, ValueError) as error:
            _print_errors([f"round trip failed: {error}"])
            print("ROUND_TRIP=FAILED")
            _print_runtime_evidence_status()
            print("APPLICATION_GATE_D_STATUS=ROUND_TRIP_FAILED")
            return 1
        if round_trip.get("status") != "ROUND_TRIP_OK":
            _print_errors(["round trip did not return ROUND_TRIP_OK"])
            print("ROUND_TRIP=FAILED")
            _print_runtime_evidence_status()
            print("APPLICATION_GATE_D_STATUS=ROUND_TRIP_FAILED")
            return 1
        print("ROUND_TRIP=ROUND_TRIP_OK")
    else:
        print("ROUND_TRIP=NOT_RUN")

    _print_runtime_evidence_status()
    if not all(gates.values()):
        status = "BLOCKED_BY_DATA_GATES"
    else:
        status = "BLOCKED_BY_RUNTIME_EVIDENCE"
    print(f"APPLICATION_GATE_D_STATUS={status}")
    return 1 if arguments.require_pass else 0


if __name__ == "__main__":
    raise SystemExit(main())
