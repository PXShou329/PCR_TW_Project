"""V0004: preserve source-unknown PVE operation modes without inference."""

from collections.abc import Sequence

from alembic import op


revision: str = "v0004_unknown_operation_mode"
down_revision: str | None = "v0003_core_revision_mirror"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONSTRAINT_NAME = "ck_operation_timelines_operation_timeline_mode"


def upgrade() -> None:
    op.drop_constraint(
        op.f(CONSTRAINT_NAME),
        "operation_timelines",
        type_="check",
    )
    op.create_check_constraint(
        op.f(CONSTRAINT_NAME),
        "operation_timelines",
        "operation_mode IN ('AUTO','SEMI_AUTO','MANUAL_TIMELINE','UNKNOWN')",
    )


def downgrade() -> None:
    # PostgreSQL validates the restored constraint against existing rows.  A
    # database that still contains UNKNOWN facts therefore fails the downgrade
    # transaction instead of silently coercing or deleting canonical data.
    op.drop_constraint(
        op.f(CONSTRAINT_NAME),
        "operation_timelines",
        type_="check",
    )
    op.create_check_constraint(
        op.f(CONSTRAINT_NAME),
        "operation_timelines",
        "operation_mode IN ('AUTO','SEMI_AUTO','MANUAL_TIMELINE')",
    )
