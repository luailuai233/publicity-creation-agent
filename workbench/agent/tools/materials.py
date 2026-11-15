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
        for material in materials:
            result = parse_path(material.path, material.mime_type)
            material.parsed_text = result.text
            material.summary = result.summary
            material.category = result.category
            material.parse_status = result.status
            context.session.execute(delete(SourceChunk).where(SourceChunk.material_id == material.id))
            context.session.add(SourceChunk(material_id=material.id, content=result.text, paragraph=1))
        context.session.commit()
        return AgentToolResult(summary=f"已解析 {len(materials)} 份资料", artifacts=["source_chunks"])
