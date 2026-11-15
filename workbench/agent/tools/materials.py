from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import delete, select

from workbench.agent.tools.base import AgentToolContext, AgentToolResult
from workbench.db.models import Material, SourceChunk
from workbench.materials.parsers import parse_path


class MaterialToolInput(BaseModel):
    project_id: str


class ParseMaterialsTool:
    name = "parse_materials"
    input_model = MaterialToolInput

    def can_run(self, snapshot) -> bool:
        return bool(snapshot.pending_material_ids)

    def execute(self, context: AgentToolContext, data: MaterialToolInput) -> AgentToolResult:
        materials = list(context.session.scalars(select(Material).where(Material.project_id == data.project_id, Material.parse_status == "QUEUED")).all())
        failed = 0
        for material in materials:
            try:
                result = parse_path(Path(material.path), material.mime_type)
                material.parsed_text = result.text
                material.summary = result.summary
                material.category = result.category
                material.parse_status = result.status
                context.session.execute(delete(SourceChunk).where(SourceChunk.material_id == material.id))
                context.session.add(SourceChunk(material_id=material.id, content=result.text, paragraph=1))
            except Exception:
                material.parse_status = "FAILED"
                failed += 1
        context.session.commit()
        return AgentToolResult(summary=f"已处理 {len(materials)} 份资料，其中 {failed} 份失败", artifacts=["source_chunks"])
