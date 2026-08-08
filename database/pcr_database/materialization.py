from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Character,
    Claim,
    ClaimEvidence,
    Evidence,
    Stage,
    StageClaim,
    StageEvidence,
    Team,
    TeamEvidence,
    TeamMember,
)


MATERIALIZATION_MANIFEST_VERSION = 1

# Every table that can affect a public B0 response belongs to the serving
# closure.  Scheduler state and ImportRun are intentionally excluded: the
# former is not strategy data and the latter contains this manifest itself.
SERVING_MODELS = (
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
)


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


def build_materialization_manifest(session: Session) -> dict[str, Any]:
    """Hash the complete normalized serving closure deterministically.

    Each table records its exact primary-key set (including relation-table
    pairs) and a hash for every complete normalized row.  This catches both
    missing/extra links and divergence between normalized columns and their
    retained source_payload without duplicating the full source text inside
    ImportRun.
    """

    tables: dict[str, Any] = {}
    for model in SERVING_MODELS:
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
        "schema_version": MATERIALIZATION_MANIFEST_VERSION,
        "tables": tables,
        "sha256": _sha256(tables),
    }


def materialization_drift_reason(
    expected: dict[str, Any] | None,
    actual: dict[str, Any],
) -> str | None:
    if not isinstance(expected, dict):
        return "materialization_manifest_missing"
    if expected.get("schema_version") != MATERIALIZATION_MANIFEST_VERSION:
        return "materialization_manifest_version"
    expected_tables = expected.get("tables")
    if not isinstance(expected_tables, dict):
        return "materialization_manifest_missing"
    actual_tables = actual["tables"]
    if set(expected_tables) != set(actual_tables):
        return "materialization_table_set_drift"
    for table_name in sorted(expected_tables):
        if expected_tables[table_name] != actual_tables[table_name]:
            return f"materialization_{table_name}_drift"
    if expected.get("sha256") != actual.get("sha256"):
        return "materialization_digest_drift"
    return None
