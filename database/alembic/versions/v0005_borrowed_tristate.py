"""V0005: preserve unknown or conflicting borrowed-member facts as NULL."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "v0005_borrowed_tristate"
down_revision: str | None = "v0004_unknown_operation_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "team_members",
        "is_borrowed",
        existing_type=sa.Boolean(),
        nullable=True,
    )


def downgrade() -> None:
    # PostgreSQL refuses SET NOT NULL while honest unknown rows remain.  A
    # downgrade therefore fails closed instead of coercing NULL to false.
    op.alter_column(
        "team_members",
        "is_borrowed",
        existing_type=sa.Boolean(),
        nullable=False,
    )
