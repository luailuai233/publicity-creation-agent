"""Add quality issue resolution fields."""

from alembic import op
import sqlalchemy as sa

revision = "0007_quality_resolution"
down_revision = "0006_authoring_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("quality_issues")}
    for name, type_ in (
        ("resolution_policy", sa.String(length=16)),
        ("resolution_note", sa.Text()),
        ("fragment", sa.Text()),
        ("suggestion", sa.Text()),
    ):
        if name not in columns:
            default = "SOFT" if name == "resolution_policy" else ""
            op.add_column("quality_issues", sa.Column(name, type_, nullable=False, server_default=default))


def downgrade() -> None:
    for name in ("suggestion", "fragment", "resolution_note", "resolution_policy"):
        op.drop_column("quality_issues", name)
