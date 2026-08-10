from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from .models import (
    ArenaCounter,
    ArenaCounterClaim,
    ArenaCounterEvidence,
    ArenaCounterMember,
    ArenaDefense,
    ArenaDefenseMember,
    ArenaSourceRecord,
    Character,
    Claim,
    ClaimEvidence,
    Evidence,
    GachaCommunitySource,
    GachaTimelineClaim,
    GachaTimelineCommunitySource,
    GachaTimelineEvent,
    GachaTimelineEvidence,
    ImportRun,
    MaterializationState,
    OperationTimeline,
    ParenaCase,
    ParenaCaseClaim,
    ParenaCaseEvidence,
    ParenaCaseMatchup,
    ParenaCaseSource,
    Stage,
    StageClaim,
    StageEvidence,
    Team,
    TeamEvidence,
    TeamMember,
    TimelineStep,
)


LEGACY_MATERIALIZATION_MANIFEST_VERSION = 2
ARENA_MATERIALIZATION_MANIFEST_VERSION = 3
GACHA_MATERIALIZATION_MANIFEST_VERSION = 4
MATERIALIZATION_MANIFEST_VERSION = 5

# Every table that can affect a public strategy response belongs to the serving
# closure.  Scheduler state and ImportRun are intentionally excluded: the
# former is not strategy data and the latter contains this manifest itself.
LEGACY_SERVING_MODELS = (
    Stage,
    Team,
    TeamMember,
    Character,
    Evidence,
    Claim,
    StageEvidence,
    StageClaim,
    TeamEvidence,
    ClaimEvidence,
    OperationTimeline,
    TimelineStep,
)

ARENA_SERVING_MODELS = (
    ArenaDefense,
    ArenaDefenseMember,
    ArenaCounter,
    ArenaCounterMember,
    ArenaCounterEvidence,
    ArenaCounterClaim,
)

GACHA_SERVING_MODELS = (
    GachaTimelineEvent,
    GachaTimelineEvidence,
    GachaTimelineClaim,
    GachaCommunitySource,
    GachaTimelineCommunitySource,
)

PARENA_SERVING_MODELS = (
    ArenaSourceRecord,
    ParenaCase,
    ParenaCaseMatchup,
    ParenaCaseSource,
    ParenaCaseEvidence,
    ParenaCaseClaim,
)

ARENA_MATERIALIZATION_SERVING_MODELS = (
    *LEGACY_SERVING_MODELS,
    *ARENA_SERVING_MODELS,
)
GACHA_MATERIALIZATION_SERVING_MODELS = (
    *ARENA_MATERIALIZATION_SERVING_MODELS,
    *GACHA_SERVING_MODELS,
)
SERVING_MODELS = (*GACHA_MATERIALIZATION_SERVING_MODELS, *PARENA_SERVING_MODELS)

_SUPPORTED_MODELS_BY_VERSION = {
    LEGACY_MATERIALIZATION_MANIFEST_VERSION: LEGACY_SERVING_MODELS,
    ARENA_MATERIALIZATION_MANIFEST_VERSION: ARENA_MATERIALIZATION_SERVING_MODELS,
    GACHA_MATERIALIZATION_MANIFEST_VERSION: GACHA_MATERIALIZATION_SERVING_MODELS,
    MATERIALIZATION_MANIFEST_VERSION: SERVING_MODELS,
}


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _models_declared_by_manifest(
    manifest: dict[str, Any] | None,
) -> tuple[type[Any], ...] | None:
    if not isinstance(manifest, dict):
        return None
    version = manifest.get("schema_version")
    tables = manifest.get("tables")
    models = _SUPPORTED_MODELS_BY_VERSION.get(version)
    if models is None or not isinstance(tables, dict):
        return None
    if set(tables) != {model.__tablename__ for model in models}:
        return None
    return models


def _detected_persisted_manifest(session: Session) -> dict[str, Any] | None:
    """Find the immutable manifest owning the currently materialized rows.

    During rollback/reactivation, the singleton still points at the previous
    revision until the replacement has been fully verified.  The normalized
    rows' import_run_id is therefore the primary signal; an empty mirror falls
    back to the active singleton.  Mixed run ownership deliberately selects no
    legacy projection, causing the full current closure to expose the drift.
    """

    # A verified rollback can run this application at an older additive schema
    # revision.  Only inspect serving tables that physically exist; selected
    # legacy tables are still queried below and therefore remain fail-closed.
    existing_tables = set(inspect(session.connection()).get_table_names())
    run_ids: set[str] = set()
    for model in SERVING_MODELS:
        if model.__tablename__ not in existing_tables:
            continue
        import_run_column = model.__table__.c.get("import_run_id")
        if import_run_column is None:
            continue
        run_ids.update(
            run_id
            for run_id in session.scalars(select(import_run_column).distinct())
            if isinstance(run_id, str)
        )
    if len(run_ids) > 1:
        return None

    run: ImportRun | None = None
    if run_ids:
        run = session.get(ImportRun, next(iter(run_ids)))
    else:
        state = session.get(MaterializationState, 1)
        if state is not None and state.active_import_run_id is not None:
            run = session.get(ImportRun, state.active_import_run_id)
    if run is None or run.status != "SUCCEEDED":
        return None
    manifest = run.manifest.get("materialization")
    return manifest if _models_declared_by_manifest(manifest) is not None else None


def _newer_tables_are_empty(
    session: Session,
    selected_models: tuple[type[Any], ...],
) -> bool:
    selected = set(selected_models)
    # Tables introduced after an immutable legacy manifest may legitimately be
    # absent after a schema downgrade.  Any newer table that is still present
    # must remain empty or the current full closure is forced.
    existing_tables = set(inspect(session.connection()).get_table_names())
    return all(
        session.scalar(select(model).limit(1)) is None
        for model in SERVING_MODELS
        if model not in selected and model.__tablename__ in existing_tables
    )


def build_materialization_manifest(
    session: Session,
    *,
    expected_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Hash the complete normalized serving closure deterministically.

    Each table records its exact primary-key set (including relation-table
    pairs) and a hash for every complete normalized row.  This catches both
    missing/extra links and divergence between normalized columns and their
    retained source_payload without duplicating the full source text inside
    ImportRun.  ``expected_manifest`` is used for immutable legacy replay; an
    omitted value is detected from the run owning the normalized rows so an
    A4 rollback can be verified before the active singleton is switched.
    """

    expected = (
        expected_manifest
        if expected_manifest is not None
        else _detected_persisted_manifest(session)
    )
    selected_models = _models_declared_by_manifest(expected)
    selected_version = (
        expected.get("schema_version")
        if selected_models is not None and isinstance(expected, dict)
        else MATERIALIZATION_MANIFEST_VERSION
    )

    # Immutable v2/v3 manifests may replay only while every table introduced
    # after their schema version is empty.  Any unprotected newer row forces
    # the full current closure so an old digest can never silently ignore it.
    if (
        selected_models is not None
        and selected_models != SERVING_MODELS
        and not _newer_tables_are_empty(session, selected_models)
    ):
        selected_models = SERVING_MODELS
        selected_version = MATERIALIZATION_MANIFEST_VERSION
    elif selected_models is None:
        selected_models = SERVING_MODELS

    tables: dict[str, Any] = {}
    for model in selected_models:
        table = model.__table__
        primary_key_columns = list(table.primary_key.columns)
        rows = session.scalars(select(model).order_by(*primary_key_columns)).all()
        row_hashes: dict[str, str] = {}
        for row in rows:
            key_values = [_json_value(getattr(row, column.name)) for column in primary_key_columns]
            key = _canonical_json(key_values[0] if len(key_values) == 1 else key_values)
            normalized = {
                column.name: _json_value(getattr(row, column.name)) for column in table.columns
            }
            row_hashes[key] = _sha256(normalized)
        tables[table.name] = {
            "primary_keys": list(row_hashes),
            "row_sha256": row_hashes,
            "sha256": _sha256(row_hashes),
        }

    return {
        "schema_version": selected_version,
        "tables": tables,
        "sha256": _sha256(tables),
    }


def materialization_drift_reason(
    expected: dict[str, Any] | None,
    actual: dict[str, Any],
) -> str | None:
    if not isinstance(expected, dict):
        return "materialization_manifest_missing"
    expected_version = expected.get("schema_version")
    expected_models = _SUPPORTED_MODELS_BY_VERSION.get(expected_version)
    if expected_models is None:
        return "materialization_manifest_version"
    expected_tables = expected.get("tables")
    if not isinstance(expected_tables, dict):
        return "materialization_manifest_missing"
    if set(expected_tables) != {model.__tablename__ for model in expected_models}:
        return "materialization_table_set_drift"
    if actual.get("schema_version") != expected_version:
        return "materialization_manifest_version"
    actual_tables = actual.get("tables")
    if not isinstance(actual_tables, dict):
        return "materialization_manifest_missing"
    if set(expected_tables) != set(actual_tables):
        return "materialization_table_set_drift"
    for table_name in sorted(expected_tables):
        if expected_tables[table_name] != actual_tables[table_name]:
            return f"materialization_{table_name}_drift"
    if expected.get("sha256") != actual.get("sha256"):
        return "materialization_digest_drift"
    return None
