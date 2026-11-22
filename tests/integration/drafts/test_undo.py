from pathlib import Path

from workbench.drafts.schemas import DraftPatch
from workbench.drafts.service import save_draft, undo_last_rewrite

from tests.integration.drafts.test_paragraph_rewrite import RewriteProvider, seed


def test_undo_restores_last_agent_rewrite_and_is_single_use(tmp_path: Path) -> None:
    session, draft, fact = seed(tmp_path)
    original = draft.content
    from workbench.drafts.service import rewrite_paragraph

    rewrite_paragraph(session, RewriteProvider("现场共有20人参与实验。", [fact.id]), draft.id, "b1", "更生动", expected_revision=3)
    restored = undo_last_rewrite(session, draft.id)

    assert restored.content == original
    assert restored.undo_snapshot is None
    assert restored.quality_status == "STALE"


def test_manual_edit_invalidates_undo_snapshot(tmp_path: Path) -> None:
    session, draft, fact = seed(tmp_path)
    from workbench.drafts.service import rewrite_paragraph

    rewrite_paragraph(session, RewriteProvider("现场共有20人参与实验。", [fact.id]), draft.id, "b1", "更生动", expected_revision=3)
    saved = save_draft(session, draft.id, DraftPatch(content="用户手工版本"))

    assert saved.undo_snapshot is None
