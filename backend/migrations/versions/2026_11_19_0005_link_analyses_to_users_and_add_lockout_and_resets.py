"""Link analyses to accounts, and add sign-in lockout and password reset tokens.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing analyses keep an empty user_id, so no account can list them.
    op.add_column(
        "analyses",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_analyses_user_id", "analyses", ["user_id"])
    op.add_column("users", sa.Column("failed_sign_ins", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "password_reset_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_sign_ins")
    op.drop_index("ix_analyses_user_id", table_name="analyses")
    op.drop_column("analyses", "user_id")
