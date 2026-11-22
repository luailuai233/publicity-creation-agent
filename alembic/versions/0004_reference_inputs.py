"""Add reference input lifecycle fields."""

from alembic import op
import sqlalchemy as sa


revision = "0004_reference_inputs"
down_revision = "0003_agent_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("reference_cases")}
    if "source_url" not in columns:
        op.add_column("reference_cases", sa.Column("source_url", sa.String(length=1000), nullable=False, server_default=""))
    if "raw_path" not in columns:
        op.add_column("reference_cases", sa.Column("raw_path", sa.String(length=600), nullable=False, server_default=""))
    if "fetch_status" not in columns:
        op.add_column("reference_cases", sa.Column("fetch_status", sa.String(length=32), nullable=False, server_default="NOT_REQUIRED"))


def downgrade() -> None:
    op.drop_column("reference_cases", "fetch_status")
    op.drop_column("reference_cases", "raw_path")
    op.drop_column("reference_cases", "source_url")
