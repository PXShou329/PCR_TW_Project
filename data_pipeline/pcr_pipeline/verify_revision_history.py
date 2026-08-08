from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from pcr_database.models import (
    CoreRevision,
    ImportRun,
    MaterializationState,
    RevisionActivation,
)

from .research_core_snapshot import materialized_report


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _canonical_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _canonical_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def _sha256(value: Any) -> str:
    payload = json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_revision_history(database_url: str) -> dict[str, object]:
    engine_options: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith(("postgresql://", "postgresql+")):
        engine_options["isolation_level"] = "REPEATABLE READ"
    engine = create_engine(database_url, **engine_options)
    with Session(engine) as session, session.begin():
        revisions = session.scalars(
            select(CoreRevision).order_by(CoreRevision.revision_id)
        ).all()
        runs = session.scalars(select(ImportRun).order_by(ImportRun.id)).all()
        activations = session.scalars(
            select(RevisionActivation).order_by(RevisionActivation.sequence_no)
        ).all()
        state = session.get(MaterializationState, 1)
        if state is None or not revisions or not activations:
            raise RuntimeError("revision history is incomplete")

        run_by_id = {run.id: run for run in runs}
        revision_ids = {revision.revision_id for revision in revisions}
        revision_records: list[dict[str, object]] = []
        for revision in revisions:
            if revision.status != "SUCCEEDED" or revision.import_run_id is None:
                raise RuntimeError(
                    f"revision is not an immutable successful snapshot: {revision.revision_id}"
                )
            run = run_by_id.get(revision.import_run_id)
            if run is None or run.status != "SUCCEEDED":
                raise RuntimeError(f"revision import provenance is missing: {revision.revision_id}")
            if (
                run.fixture_sha256 != revision.raw_tree_sha256
                or revision.raw_tree_sha256 != revision.revision_id
            ):
                raise RuntimeError(f"revision raw-tree provenance drifted: {revision.revision_id}")
            materialization = run.manifest.get("materialization")
            if (
                not isinstance(materialization, dict)
                or materialization.get("sha256") != revision.materialization_sha256
            ):
                raise RuntimeError(
                    f"revision typed-materialization provenance drifted: {revision.revision_id}"
                )
            report = materialized_report(session, revision.revision_id).as_dict()
            if run.manifest.get("core_revision") != report:
                raise RuntimeError(
                    f"ImportRun core_revision provenance drifted: {revision.revision_id}"
                )
            revision_records.append(
                {
                    "revision_id": revision.revision_id,
                    "import_run_id": revision.import_run_id,
                    "semantic_tree_sha256": revision.semantic_tree_sha256,
                    "manifest_sha256": revision.manifest_sha256,
                    "materialization_sha256": revision.materialization_sha256,
                    "file_count": revision.file_count,
                    "csv_file_count": revision.csv_file_count,
                    "csv_row_count": revision.csv_row_count,
                    "evidence_to_claim_count": revision.evidence_to_claim_count,
                    "evidence_to_claim_sha256": revision.evidence_to_claim_sha256,
                    "claim_to_evidence_count": revision.claim_to_evidence_count,
                    "claim_to_evidence_sha256": revision.claim_to_evidence_sha256,
                    "status": revision.status,
                    "manifest": revision.manifest,
                    "project_version": revision.project_version,
                    "serialization_version": revision.serialization_version,
                    "created_at": revision.created_at,
                    "report": report,
                }
            )

        expected_sequence = list(range(1, len(activations) + 1))
        actual_sequence = [int(activation.sequence_no) for activation in activations]
        if actual_sequence != expected_sequence:
            raise RuntimeError("activation sequence is not contiguous")
        previous_target: str | None = None
        previous_epoch = -1
        activation_records: list[dict[str, object]] = []
        for activation in activations:
            if activation.to_revision_id not in revision_ids:
                raise RuntimeError("activation points to an unknown revision")
            if activation.from_revision_id != previous_target:
                raise RuntimeError("activation history does not form one canonical chain")
            if int(activation.epoch) <= previous_epoch:
                raise RuntimeError("activation epochs are not strictly increasing")
            if activation.sequence_no == 1 and activation.kind != "IMPORT":
                raise RuntimeError("first activation is not an import")
            activation_records.append(
                {
                    "activation_id": activation.activation_id,
                    "sequence_no": int(activation.sequence_no),
                    "from_revision_id": activation.from_revision_id,
                    "to_revision_id": activation.to_revision_id,
                    "kind": activation.kind,
                    "reason": activation.reason,
                    "actor": activation.actor,
                    "activated_at": activation.activated_at,
                    "epoch": int(activation.epoch),
                }
            )
            previous_target = activation.to_revision_id
            previous_epoch = int(activation.epoch)

        if (
            state.active_revision_id != previous_target
            or state.active_import_run_id
            != next(
                revision.import_run_id
                for revision in revisions
                if revision.revision_id == previous_target
            )
        ):
            raise RuntimeError("active pointer differs from final activation audit")
        if int(state.epoch) < previous_epoch:
            raise RuntimeError("materialization epoch predates final activation audit")

        run_records = [
            {
                "id": run.id,
                "fixture_sha256": run.fixture_sha256,
                "canonical_source": run.canonical_source,
                "research_core_version": run.research_core_version,
                "application_version": run.application_version,
                "imported_at": run.imported_at,
                "status": run.status,
                "manifest": run.manifest,
                "row_counts": run.row_counts,
            }
            for run in runs
        ]
        history = {
            "materialization_state": {
                "id": state.id,
                "active_revision_id": state.active_revision_id,
                "active_import_run_id": state.active_import_run_id,
                "epoch": int(state.epoch),
                "materialization_sha256": state.materialization_sha256,
                "serving_counts": state.serving_counts,
                "updated_at": state.updated_at,
            },
            "revisions": revision_records,
            "import_runs": run_records,
            "activations": activation_records,
        }
        active_revision_id = state.active_revision_id
        history_sha256 = _sha256(history)

    return {
        "status": "REVISION_HISTORY_VERIFIED",
        "history_sha256": history_sha256,
        "revision_count": len(revision_records),
        "import_run_count": len(run_records),
        "activation_count": len(activation_records),
        "inactive_revision_count": len(revision_records) - 1,
        "active_revision_id": active_revision_id,
    }


def main() -> int:
    result = verify_revision_history(_required_environment("PCR_DATABASE_URL"))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
