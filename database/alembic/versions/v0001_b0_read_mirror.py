"""V0001: additive B0 read-mirror and scheduler-control schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "v0001_b0_read_mirror"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

jsonb = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "import_runs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("fixture_sha256", sa.String(64), nullable=False),
        sa.Column("canonical_source", sa.String(80), nullable=False),
        sa.Column("research_core_version", sa.String(40), nullable=False),
        sa.Column("application_version", sa.String(40), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("manifest", jsonb, nullable=False),
        sa.Column("row_counts", jsonb, nullable=False),
        sa.CheckConstraint(
            "status IN ('RUNNING','SUCCEEDED','FAILED')",
            name=op.f("ck_import_runs_import_status"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_import_runs"),
        sa.UniqueConstraint("fixture_sha256", name="uq_import_runs_fixture_sha256"),
    )

    op.create_table(
        "characters",
        sa.Column("unit_key", sa.String(100), nullable=False),
        sa.Column("tw_name", sa.String(160), nullable=False),
        sa.Column("jp_name", sa.String(160), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("tw_release_date", sa.Date(), nullable=True),
        sa.Column("availability_status", sa.String(32), nullable=False),
        sa.Column("ue1_status", sa.String(32), nullable=False),
        sa.Column("ue2_status", sa.String(32), nullable=False),
        sa.Column("six_star_status", sa.String(32), nullable=False),
        sa.Column("connect_rank_status", sa.String(32), nullable=False),
        sa.Column("element", sa.String(32), nullable=False),
        sa.Column("source_evidence_ids", jsonb, nullable=False),
        sa.Column("last_verified", sa.Date(), nullable=False),
        sa.Column("last_review_due", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_characters_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("unit_key", name="pk_characters"),
    )

    op.create_table(
        "claims",
        sa.Column("claim_id", sa.String(140), nullable=False),
        sa.Column("module", sa.String(40), nullable=False),
        sa.Column("server", sa.String(40), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(50), nullable=False),
        sa.Column("claim_confidence", sa.String(8), nullable=False),
        sa.Column("independence_check", sa.String(20), nullable=False),
        sa.Column("version_match", sa.String(20), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("verified_date", sa.Date(), nullable=False),
        sa.Column("next_review_due", sa.Date(), nullable=True),
        sa.Column("affected_files", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("declared_evidence_ids", jsonb, nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_claims_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("claim_id", name="pk_claims"),
    )

    op.create_table(
        "evidence",
        sa.Column("evidence_id", sa.String(80), nullable=False),
        sa.Column("declared_claim_id", sa.String(140), nullable=True),
        sa.Column("linked_claim_id", sa.String(140), nullable=True),
        sa.Column("module", sa.String(40), nullable=False),
        sa.Column("server", sa.String(40), nullable=False),
        sa.Column("source_tier", sa.String(40), nullable=False),
        sa.Column("evidence_confidence", sa.String(8), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("published_date_precision", sa.String(20), nullable=False),
        sa.Column("verified_date", sa.Date(), nullable=False),
        sa.Column("claim_summary", sa.Text(), nullable=False),
        sa.Column("limitations", sa.Text(), nullable=False),
        sa.Column("affected_files", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_evidence_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["linked_claim_id"],
            ["claims.claim_id"],
            name="fk_evidence_linked_claim_id_claims",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("evidence_id", name="pk_evidence"),
    )

    op.create_table(
        "stages",
        sa.Column("guide_id", sa.String(160), nullable=False),
        sa.Column("server", sa.String(16), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("area", sa.String(80), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("verified_date", sa.Date(), nullable=False),
        sa.Column("applicable_version", sa.String(80), nullable=False),
        sa.Column("team_count", sa.Integer(), nullable=False),
        sa.Column("source_tier", sa.String(40), nullable=False),
        sa.Column("claim_confidence", sa.String(8), nullable=False),
        sa.Column("reproducibility", sa.String(32), nullable=False),
        sa.Column("last_review_due", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.CheckConstraint(
            "team_count >= 0", name=op.f("ck_stages_stage_team_count_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_stages_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("guide_id", name="pk_stages"),
    )
    op.create_index(
        "ix_stages_server_mode_area_stage",
        "stages",
        ["server", "mode", "area", "stage"],
        unique=False,
    )

    op.create_table(
        "teams",
        sa.Column("team_id", sa.String(120), nullable=False),
        sa.Column("guide_id", sa.String(160), nullable=False),
        sa.Column("server", sa.String(16), nullable=False),
        sa.Column("stage_label", sa.String(100), nullable=False),
        sa.Column("support_slot", sa.String(16), nullable=True),
        sa.Column("operation_mode", sa.String(32), nullable=False),
        sa.Column("requirements", jsonb, nullable=False),
        sa.Column("requirements_raw", sa.Text(), nullable=False),
        sa.Column("clear_status", sa.String(32), nullable=False),
        sa.Column("stability", sa.String(80), nullable=False),
        sa.Column("source_ids", jsonb, nullable=False),
        sa.Column("tw_availability_check", sa.String(20), nullable=False),
        sa.Column("verified_date", sa.Date(), nullable=False),
        sa.Column("last_review_due", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("signature", sa.String(600), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["guide_id"],
            ["stages.guide_id"],
            name="fk_teams_guide_id_stages",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_teams_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("team_id", name="pk_teams"),
        sa.UniqueConstraint("guide_id", "signature", name="uq_teams_guide_signature"),
    )

    op.create_table(
        "team_members",
        sa.Column("team_id", sa.String(120), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("unit_key", sa.String(100), nullable=False),
        sa.Column("is_borrowed", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "slot BETWEEN 1 AND 5", name=op.f("ck_team_members_team_member_slot_range")
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.team_id"], name="fk_team_members_team_id_teams", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["unit_key"],
            ["characters.unit_key"],
            name="fk_team_members_unit_key_characters",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("team_id", "slot", name="pk_team_members"),
        sa.UniqueConstraint("team_id", "unit_key", name="uq_team_members_team_unit"),
    )

    op.create_table(
        "stage_evidence",
        sa.Column("guide_id", sa.String(160), nullable=False),
        sa.Column("evidence_id", sa.String(80), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.evidence_id"],
            name="fk_stage_evidence_evidence_id_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["guide_id"], ["stages.guide_id"], name="fk_stage_evidence_guide_id_stages", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("guide_id", "evidence_id", name="pk_stage_evidence"),
    )
    op.create_table(
        "stage_claims",
        sa.Column("guide_id", sa.String(160), nullable=False),
        sa.Column("claim_id", sa.String(140), nullable=False),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["claims.claim_id"],
            name="fk_stage_claims_claim_id_claims",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["guide_id"], ["stages.guide_id"], name="fk_stage_claims_guide_id_stages", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("guide_id", "claim_id", name="pk_stage_claims"),
    )
    op.create_table(
        "team_evidence",
        sa.Column("team_id", sa.String(120), nullable=False),
        sa.Column("evidence_id", sa.String(80), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.evidence_id"],
            name="fk_team_evidence_evidence_id_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.team_id"], name="fk_team_evidence_team_id_teams", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("team_id", "evidence_id", name="pk_team_evidence"),
    )
    op.create_table(
        "claim_evidence",
        sa.Column("claim_id", sa.String(140), nullable=False),
        sa.Column("evidence_id", sa.String(80), nullable=False),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claims.claim_id"], name="fk_claim_evidence_claim_id_claims", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.evidence_id"],
            name="fk_claim_evidence_evidence_id_evidence",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("claim_id", "evidence_id", name="pk_claim_evidence"),
    )

    op.create_table(
        "scheduler_leases",
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "expires_at > acquired_at",
            name=op.f("ck_scheduler_leases_scheduler_lease_positive_window"),
        ),
        sa.PrimaryKeyConstraint("name", name="pk_scheduler_leases"),
    )
    op.create_table(
        "scheduler_runs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("idempotency_key", sa.String(240), nullable=False),
        sa.Column("job_name", sa.String(120), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("shadow_mode", sa.Boolean(), nullable=False),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detail", jsonb, nullable=False),
        sa.CheckConstraint(
            "status IN ('STARTED','SUCCEEDED','FAILED','SKIPPED')",
            name=op.f("ck_scheduler_runs_scheduler_run_status"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scheduler_runs"),
        sa.UniqueConstraint("idempotency_key", name="uq_scheduler_runs_idempotency_key"),
        sa.UniqueConstraint("job_name", "scheduled_for", name="uq_scheduler_runs_job_scheduled"),
    )


def downgrade() -> None:
    op.drop_table("scheduler_runs")
    op.drop_table("scheduler_leases")
    op.drop_table("claim_evidence")
    op.drop_table("team_evidence")
    op.drop_table("stage_claims")
    op.drop_table("stage_evidence")
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_index("ix_stages_server_mode_area_stage", table_name="stages")
    op.drop_table("stages")
    op.drop_table("evidence")
    op.drop_table("claims")
    op.drop_table("characters")
    op.drop_table("import_runs")
