"""Add persistent agent runtime state.

Revision ID: 0003_agent_runtime
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_agent_runtime"
down_revision = "0002_project_sort_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    project_columns = {column["name"] for column in inspector.get_columns("projects")}
    if "goal" not in project_columns:
        op.add_column("projects", sa.Column("goal", sa.Text(), nullable=False, server_default=""))
    if "decisions" not in project_columns:
        op.add_column("projects", sa.Column("decisions", sa.JSON(), nullable=False, server_default="{}"))
    if "revision" not in project_columns:
        op.add_column("projects", sa.Column("revision", sa.Integer(), nullable=False, server_default="0"))
    draft_columns = {column["name"] for column in sa.inspect(connection).get_columns("drafts")}
    if "revision" not in draft_columns:
        op.add_column("drafts", sa.Column("revision", sa.Integer(), nullable=False, server_default="0"))
    if "quality_status" not in draft_columns:
        op.add_column("drafts", sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="NOT_CHECKED"))

    tables = set(sa.inspect(connection).get_table_names())
    if "agent_runs" not in tables:
        op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("plan_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("current_stage", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("tool_call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_tool_calls", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("max_revisions", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("waiting_reason", sa.String(length=120), nullable=True),
        sa.Column("waiting_payload", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pause_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active_key", sa.String(length=36), nullable=True, unique=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_agent_runs_project_id", "agent_runs", ["project_id"])
        op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    if "agent_steps" not in tables:
        op.create_table(
        "agent_steps",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("input_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("output_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("result_ref", sa.String(length=255), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("run_id", "sequence", name="uq_agent_step_run_sequence"),
        )
        op.create_index("ix_agent_steps_run_id", "agent_steps", ["run_id"])
        op.create_index("ix_agent_steps_input_fingerprint", "agent_steps", ["input_fingerprint"])

    if "agent_messages" not in tables:
        op.create_table(
        "agent_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_agent_messages_run_id", "agent_messages", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_messages_run_id", table_name="agent_messages")
    op.drop_table("agent_messages")
    op.drop_index("ix_agent_steps_input_fingerprint", table_name="agent_steps")
    op.drop_index("ix_agent_steps_run_id", table_name="agent_steps")
    op.drop_table("agent_steps")
    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_project_id", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_column("drafts", "quality_status")
    op.drop_column("drafts", "revision")
    op.drop_column("projects", "revision")
    op.drop_column("projects", "decisions")
    op.drop_column("projects", "goal")
