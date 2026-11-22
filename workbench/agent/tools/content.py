from typing import Literal

from pydantic import BaseModel

from workbench.agent.tools.base import AgentToolContext, AgentToolResult
from workbench.db.models import AgentRun, Project
from workbench.drafts.service import create_outline, generate_draft


class ContentToolInput(BaseModel):
    project_id: str
    mode: Literal["initial", "revision"] = "initial"


class GenerateContentTool:
    name = "generate_content"
    input_model = ContentToolInput

    def can_run(self, snapshot) -> bool:
        return snapshot.selected_strategy_id is not None

    def execute(self, context: AgentToolContext, data: ContentToolInput) -> AgentToolResult:
        outline = create_outline(context.session, context.provider, data.project_id)
        title = outline.titles[outline.recommended_title_index]
        draft = generate_draft(context.session, context.provider, data.project_id, title, outline.outline, revision=data.mode == "revision")
        project = context.session.get(Project, data.project_id)
        decisions = dict(project.decisions or {})
        decisions["recommended_title"] = title
        project.decisions = decisions
        if data.mode == "revision":
            run = context.session.get(AgentRun, context.run_id)
            if run is not None:
                run.revision_count += 1
        context.session.commit()
        return AgentToolResult(summary=f"已生成标题、大纲和正文：{title}", result_ref=draft.id, artifacts=["draft", "citations"])
