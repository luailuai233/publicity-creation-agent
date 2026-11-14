"""Add deterministic project ordering.

Revision ID: 0002_project_sort_order
"""

import time

from alembic import op
import sqlalchemy as sa


revision = "0002_project_sort_order"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("sort_order", sa.BigInteger(), nullable=True))
    connection = op.get_bind()
    rows = list(connection.execute(sa.text("SELECT id FROM projects ORDER BY created_at, id")))
    base = time.time_ns() - len(rows)
    for offset, row in enumerate(rows):
        connection.execute(
            sa.text("UPDATE projects SET sort_order = :value WHERE id = :id"),
            {"value": base + offset, "id": row.id},
        )
    op.create_index("ix_projects_sort_order", "projects", ["sort_order"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_projects_sort_order", table_name="projects")
    op.drop_column("projects", "sort_order")
