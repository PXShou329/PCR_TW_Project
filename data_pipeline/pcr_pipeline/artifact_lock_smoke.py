from __future__ import annotations

import hashlib
import json
import os
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _digest(seed: str, label: str) -> str:
    return hashlib.sha256(f"{seed}:{label}".encode()).hexdigest()


def _sqlstate(error: BaseException) -> str | None:
    current: BaseException | None = error
    while current is not None:
        sqlstate = getattr(current, "sqlstate", None)
        if sqlstate:
            return str(sqlstate)
        current = current.__cause__ or current.__context__
    return None


def run_smoke(database_url: str) -> dict[str, object]:
    engine = create_engine(database_url, pool_pre_ping=True)
    seed = uuid.uuid4().hex
    import_run_id = str(uuid.uuid4())
    revision_id = _digest(seed, "revision")
    fixture_sha256 = _digest(seed, "fixture")
    setup_complete = False
    denial_sqlstate: str | None = None

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO import_runs "
                    "(id, fixture_sha256, canonical_source, research_core_version, "
                    "application_version, imported_at, status, manifest, row_counts) "
                    "VALUES (:id, :fixture_sha256, 'B1_LOCK_PROBE', 'B1', 'B1', "
                    "CURRENT_TIMESTAMP, 'RUNNING', CAST(:manifest AS jsonb), "
                    "CAST(:row_counts AS jsonb))"
                ),
                {
                    "id": import_run_id,
                    "fixture_sha256": fixture_sha256,
                    "manifest": json.dumps({"probe": seed}),
                    "row_counts": json.dumps({}),
                },
            )
            connection.execute(
                text(
                    "INSERT INTO core_revisions "
                    "(revision_id, import_run_id, raw_tree_sha256, semantic_tree_sha256, "
                    "manifest_sha256, materialization_sha256, file_count, csv_file_count, "
                    "csv_row_count, evidence_to_claim_count, evidence_to_claim_sha256, "
                    "claim_to_evidence_count, claim_to_evidence_sha256, status, manifest, "
                    "project_version, serialization_version, created_at) "
                    "VALUES (:revision_id, :import_run_id, :raw_tree_sha256, "
                    ":semantic_tree_sha256, :manifest_sha256, NULL, 1, 1, 0, 0, "
                    ":evidence_to_claim_sha256, 0, :claim_to_evidence_sha256, "
                    "'STAGING', CAST(:manifest AS jsonb), 'B1_LOCK_PROBE', 1, "
                    "CURRENT_TIMESTAMP)"
                ),
                {
                    "revision_id": revision_id,
                    "import_run_id": import_run_id,
                    "raw_tree_sha256": revision_id,
                    "semantic_tree_sha256": _digest(seed, "semantic"),
                    "manifest_sha256": _digest(seed, "manifest"),
                    "evidence_to_claim_sha256": _digest(seed, "evidence-to-claim"),
                    "claim_to_evidence_sha256": _digest(seed, "claim-to-evidence"),
                    "manifest": json.dumps({"probe": seed}),
                },
            )
        setup_complete = True

        with engine.connect() as artifact_connection:
            artifact_transaction = artifact_connection.begin()
            try:
                artifact_connection.execute(
                    text(
                        "INSERT INTO core_files "
                        "(revision_id, relative_path, ordinal, sha256, semantic_sha256, "
                        "size_bytes, content, is_csv, natural_key_field, header) "
                        "VALUES (:revision_id, 'probe.csv', 1, :sha256, :semantic_sha256, "
                        "1, :content, true, 'probe_id', CAST(:header AS jsonb))"
                    ),
                    {
                        "revision_id": revision_id,
                        "sha256": _digest(seed, "file"),
                        "semantic_sha256": _digest(seed, "file-semantic"),
                        "content": b"x",
                        "header": json.dumps(["probe_id"]),
                    },
                )

                with engine.connect() as finalizer_connection:
                    finalizer_transaction = finalizer_connection.begin()
                    try:
                        finalizer_connection.execute(
                            text("SET LOCAL lock_timeout = '750ms'")
                        )
                        finalizer_connection.execute(
                            text(
                                "UPDATE core_revisions SET status='SUCCEEDED' "
                                "WHERE revision_id=:revision_id"
                            ),
                            {"revision_id": revision_id},
                        )
                    except DBAPIError as error:
                        denial_sqlstate = _sqlstate(error)
                        if denial_sqlstate != "55P03" or "lock timeout" not in str(
                            error.orig
                        ).lower():
                            raise RuntimeError(
                                "finalizer failed for a reason other than the parent row lock"
                            ) from error
                    else:
                        raise RuntimeError(
                            "revision finalized while an artifact transaction was open"
                        )
                    finally:
                        finalizer_transaction.rollback()

                status = artifact_connection.execute(
                    text(
                        "SELECT status FROM core_revisions "
                        "WHERE revision_id=:revision_id"
                    ),
                    {"revision_id": revision_id},
                ).scalar_one()
                if status != "STAGING":
                    raise RuntimeError("denied finalizer changed the parent revision")
            finally:
                artifact_transaction.rollback()
    finally:
        if setup_complete:
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM core_revisions WHERE revision_id=:revision_id"),
                    {"revision_id": revision_id},
                )
                connection.execute(
                    text("DELETE FROM import_runs WHERE id=:import_run_id"),
                    {"import_run_id": import_run_id},
                )
            with engine.connect() as connection:
                residue = int(
                    connection.execute(
                        text(
                            "SELECT "
                            "(SELECT count(*) FROM core_revisions "
                            "WHERE revision_id=:revision_id) + "
                            "(SELECT count(*) FROM import_runs WHERE id=:import_run_id)"
                        ),
                        {
                            "revision_id": revision_id,
                            "import_run_id": import_run_id,
                        },
                    ).scalar_one()
                )
            if residue != 0:
                raise RuntimeError("artifact/finalize lock probe cleanup left database rows")

    if denial_sqlstate != "55P03":
        raise RuntimeError("artifact/finalize lock denial was not observed")
    return {
        "status": "ARTIFACT_FINALIZE_LOCK_OK",
        "denial_sqlstate": denial_sqlstate,
        "cleanup_rows": 0,
    }


def main() -> int:
    result = run_smoke(_required_environment("PCR_IMPORTER_DATABASE_URL"))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
