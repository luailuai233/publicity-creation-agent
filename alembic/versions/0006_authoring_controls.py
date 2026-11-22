"""Add strategy and draft authoring controls."""

from alembic import op
import sqlalchemy as sa

revision = "0006_authoring_controls"
down_revision = "0005_fact_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    strategy_columns = {column["name"] for column in sa.inspect(connection).get_columns("strategies")}
    if "protagonist" not in strategy_columns:
        op.add_column("strategies", sa.Column("protagonist", sa.String(length=160), nullable=False, server_default="未指定"))
    draft_columns = {column["name"] for column in sa.inspect(connection).get_columns("drafts")}
    if "locked_fact_ids" not in draft_columns:
        op.add_column("drafts", sa.Column("locked_fact_ids", sa.JSON(), nullable=False, server_default="[]"))
    if "locked_block_ids" not in draft_columns:
        op.add_column("drafts", sa.Column("locked_block_ids", sa.JSON(), nullable=False, server_default="[]"))
    if "undo_snapshot" not in draft_columns:
        op.add_column("drafts", sa.Column("undo_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("drafts", "undo_snapshot")
    op.drop_column("drafts", "locked_block_ids")
    op.drop_column("drafts", "locked_fact_ids")
    op.drop_column("strategies", "protagonist")
