"""Add normalized fact identity fields."""

from alembic import op
import sqlalchemy as sa


revision = "0005_fact_identity"
down_revision = "0004_reference_inputs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("fact_cards")}
    if "normalized_value" not in columns:
        op.add_column("fact_cards", sa.Column("normalized_value", sa.Text(), nullable=False, server_default=""))
        op.create_index("ix_fact_cards_normalized_value", "fact_cards", ["normalized_value"])
    if "fingerprint" not in columns:
        op.add_column("fact_cards", sa.Column("fingerprint", sa.String(length=64), nullable=False, server_default=""))
        op.create_index("ix_fact_cards_fingerprint", "fact_cards", ["fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_fact_cards_fingerprint", table_name="fact_cards")
    op.drop_column("fact_cards", "fingerprint")
    op.drop_index("ix_fact_cards_normalized_value", table_name="fact_cards")
    op.drop_column("fact_cards", "normalized_value")
