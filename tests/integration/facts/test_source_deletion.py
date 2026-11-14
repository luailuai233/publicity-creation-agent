from io import BytesIO
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from workbench.db.base import Base
from workbench.db.models import FactCard, FactSource, Material, Project, SourceChunk
from workbench.materials.service import delete_material
from workbench.storage.local import LocalStorage


def test_deleting_only_source_reverts_confirmed_fact_to_pending(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'source-delete.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    storage = LocalStorage(tmp_path / "storage" / "projects")

    with sessions() as session:
        project = Project(name="来源删除")
        session.add(project)
        session.flush()
        stored = storage.save_material_file(project.id, "source.txt", BytesIO(b"source"))
        material = Material(project_id=project.id, file_name="source.txt", mime_type="text/plain", path=str(stored.path))
        session.add(material)
        session.flush()
        chunk = SourceChunk(material_id=material.id, content="活动时间是 9:00")
        fact = FactCard(project_id=project.id, type="TIME", content="活动时间是 9:00", status="CONFIRMED")
        session.add_all([chunk, fact])
        session.flush()
        session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id))
        session.commit()
        material_id, fact_id = material.id, fact.id

        delete_material(session, storage, material_id)

        restored = session.get(FactCard, fact_id)
        assert restored.status == "PENDING"
        assert stored.path.exists() is False
