"""Idempotently provision least-privilege PostgreSQL service roles.

Alembic remains the only schema owner. The importer can write the serving
and full artifact mirrors except for append-only activation history, the API
can only read them, and the scheduler can only touch its two control tables.
Passwords are accepted from environment variables and are never emitted to
stdout or logs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import psycopg
from psycopg import sql


TYPED_SERVING_TABLES = (
    "import_runs",
    "characters",
    "claims",
    "evidence",
    "stages",
    "teams",
    "team_members",
    "stage_evidence",
    "stage_claims",
    "team_evidence",
    "claim_evidence",
    "operation_timelines",
    "timeline_steps",
    "arena_defenses",
    "arena_defense_members",
    "arena_counters",
    "arena_counter_members",
    "arena_counter_evidence",
    "arena_counter_claims",
    "gacha_timeline_events",
    "gacha_timeline_evidence",
    "gacha_timeline_claims",
    "gacha_community_sources",
    "gacha_timeline_community_sources",
    "arena_source_records",
    "parena_cases",
    "parena_case_matchups",
    "parena_case_sources",
    "parena_case_evidence",
    "parena_case_claims",
)
CORE_MIRROR_TABLES = (
    "core_revisions",
    "core_files",
    "core_csv_rows",
    "materialization_state",
)
APPEND_ONLY_TABLES = ("revision_activations",)
MUTABLE_MIRROR_TABLES = TYPED_SERVING_TABLES + CORE_MIRROR_TABLES
SERVING_TABLES = MUTABLE_MIRROR_TABLES + APPEND_ONLY_TABLES
SCHEDULER_TABLES = ("scheduler_leases", "scheduler_runs")


@dataclass(frozen=True)
class ServiceRole:
    name: str
    password: str


def _required_secret(name: str) -> str:
    value = os.getenv(name, "")
    lowered = value.lower()
    if len(value) < 16 or "replace" in lowered or "placeholder" in lowered:
        raise RuntimeError(f"{name} must be a non-placeholder secret of at least 16 characters")
    return value


def _ensure_login_role(cursor: psycopg.Cursor, role: ServiceRole) -> None:
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role.name,))
    exists = cursor.fetchone() is not None
    action = "ALTER ROLE" if exists else "CREATE ROLE"
    cursor.execute(
        sql.SQL(
            f"{action} {{}} WITH LOGIN PASSWORD {{}} "
            "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
        ).format(sql.Identifier(role.name), sql.Literal(role.password))
    )


def _revoke_role_memberships(cursor: psycopg.Cursor, role_name: str) -> None:
    """Remove inherited/SET ROLE privilege paths from a drifted service role."""

    cursor.execute(
        "SELECT parent.rolname "
        "FROM pg_auth_members membership "
        "JOIN pg_roles parent ON parent.oid = membership.roleid "
        "JOIN pg_roles member ON member.oid = membership.member "
        "WHERE member.rolname = %s",
        (role_name,),
    )
    for (parent_role,) in cursor.fetchall():
        cursor.execute(
            sql.SQL("REVOKE {} FROM {}").format(
                sql.Identifier(parent_role),
                sql.Identifier(role_name),
            )
        )


def _table_list(names: tuple[str, ...]) -> sql.Composed:
    return sql.SQL(", ").join(sql.Identifier(name) for name in names)


def provision_roles(
    owner_database_url: str,
    *,
    api_password: str,
    importer_password: str,
    scheduler_password: str,
) -> dict[str, object]:
    roles = {
        "api": ServiceRole("pcr_api", api_password),
        "importer": ServiceRole("pcr_importer", importer_password),
        "scheduler": ServiceRole("pcr_scheduler", scheduler_password),
    }

    with psycopg.connect(owner_database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_user")
            owner = cursor.fetchone()[0]
            for role in roles.values():
                _ensure_login_role(cursor, role)
                _revoke_role_memberships(cursor, role.name)
                cursor.execute(
                    sql.SQL("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {}")
                    .format(sql.Identifier(role.name))
                )
                cursor.execute(
                    sql.SQL("REVOKE ALL ON SCHEMA public FROM {}").format(
                        sql.Identifier(role.name)
                    )
                )
                cursor.execute(
                    sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
                        sql.Identifier(role.name)
                    )
                )

            cursor.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM PUBLIC")
            cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            cursor.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "REVOKE ALL ON TABLES FROM PUBLIC"
                ).format(sql.Identifier(owner))
            )

            cursor.execute(
                sql.SQL("GRANT SELECT ON TABLE {} TO {}").format(
                    _table_list(SERVING_TABLES), sql.Identifier(roles["api"].name)
                )
            )
            cursor.execute(
                sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {} TO {}").format(
                    _table_list(MUTABLE_MIRROR_TABLES),
                    sql.Identifier(roles["importer"].name),
                )
            )
            cursor.execute(
                sql.SQL("GRANT SELECT, INSERT ON TABLE {} TO {}").format(
                    _table_list(APPEND_ONLY_TABLES),
                    sql.Identifier(roles["importer"].name),
                )
            )
            cursor.execute(
                sql.SQL("GRANT SELECT, INSERT, UPDATE ON TABLE {} TO {}").format(
                    _table_list(SCHEDULER_TABLES), sql.Identifier(roles["scheduler"].name)
                )
            )

    return {
        "status": "SERVICE_ROLES_READY",
        "roles": {key: value.name for key, value in roles.items()},
        "api_permissions": ["SELECT typed and artifact mirror"],
        "importer_permissions": [
            "SELECT/INSERT/UPDATE/DELETE mutable mirror",
            "SELECT/INSERT revision activations",
        ],
        "scheduler_permissions": ["SELECT/INSERT/UPDATE scheduler control"],
    }


def main() -> int:
    owner_database_url = os.getenv("PCR_OWNER_DATABASE_URL") or os.getenv("PCR_DATABASE_URL")
    if not owner_database_url:
        raise RuntimeError("PCR_OWNER_DATABASE_URL is required")
    result = provision_roles(
        owner_database_url,
        api_password=_required_secret("PCR_API_DB_PASSWORD"),
        importer_password=_required_secret("PCR_IMPORTER_DB_PASSWORD"),
        scheduler_password=_required_secret("PCR_SCHEDULER_DB_PASSWORD"),
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
