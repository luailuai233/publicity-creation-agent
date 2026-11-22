from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.ai.errors import AIProviderError
from workbench.api.responses import api_error, api_response
from workbench.db.models import ReferenceCase
from workbench.db.projects import ProjectNotFoundError, get_project, touch_project_inputs
from workbench.materials.image_understanding import ImageUnderstandingError
from workbench.materials.limits import MAX_FILE_BYTES
from workbench.references.service import ReferenceAnalysisUnavailable, ReferenceCreate, ReferencePatch, analyze_reference, create_reference, delete_reference
from workbench.storage.local import LocalStorage
from workbench.web.dependencies import get_session


router = APIRouter(tags=["references"])
REFERENCE_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def serialize(reference: ReferenceCase) -> dict:
    analysis = reference.analysis
    return {
        "id": reference.id,
        "project_id": reference.project_id,
        "input_type": reference.input_type,
        "raw_text": reference.raw_text,
        "source_url": reference.source_url,
        "raw_path": reference.raw_path,
        "fetch_status": reference.fetch_status,
        "source_label": reference.source_label,
        "status": reference.status,
        "selected": reference.selected,
        "analysis": None if analysis is None else {
            "hook": analysis.hook,
            "emotion": analysis.emotion,
            "structure": analysis.structure,
            "image_role": analysis.image_role,
            "transferable": analysis.transferable,
            "avoid": analysis.avoid,
            "is_demo": analysis.is_demo,
        },
    }


@router.get("/api/projects/{project_id}/references")
def index(project_id: str, session: Session = Depends(get_session)):
    items = session.scalars(select(ReferenceCase).where(ReferenceCase.project_id == project_id).order_by(ReferenceCase.created_at)).all()
    return api_response([serialize(item) for item in items])


@router.post("/api/projects/{project_id}/references", status_code=201)
def create(project_id: str, data: ReferenceCreate, request: Request, session: Session = Depends(get_session)):
    return api_response(
        serialize(create_reference(session, project_id, data, provider=request.app.state.ai_provider)),
        status_code=201,
    )


@router.post("/api/projects/{project_id}/references/upload", status_code=201)
async def upload_screenshot(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    source_label: str = Form(default=""),
    description: str = Form(default=""),
    session: Session = Depends(get_session),
):
    try:
        get_project(session, project_id)
    except ProjectNotFoundError:
        return api_error("PROJECT_NOT_FOUND", "没有找到这个创作任务", 404)
    file_name = file.filename or "screenshot"
    suffix = Path(file_name).suffix.lower()
    expected_type = REFERENCE_IMAGE_TYPES.get(suffix)
    if expected_type is None or file.content_type != expected_type:
        return api_error("INVALID_REFERENCE_IMAGE", "仅支持 PNG、JPG/JPEG 和 WEBP 截图，且文件类型必须匹配", 422)
    payload = await file.read()
    if len(payload) > MAX_FILE_BYTES:
        return api_error("REFERENCE_IMAGE_TOO_LARGE", "单张截图不能超过 20 MB", 422)
    storage = LocalStorage(request.app.state.settings.paths.uploads)
    stored = storage.save_material_file(project_id, file_name, BytesIO(payload))
    try:
        reference = create_reference(
            session,
            project_id,
            ReferenceCreate(
                input_type="SCREENSHOT",
                raw_path=str(stored.path),
                raw_text=description.strip(),
                source_label=source_label.strip() or stored.original_name,
            ),
            provider=request.app.state.ai_provider,
        )
    except ImageUnderstandingError as error:
        storage.delete_file(stored.path)
        return api_error("INVALID_REFERENCE_IMAGE", str(error), 422)
    return api_response(serialize(reference), status_code=201)


@router.patch("/api/references/{reference_id}")
def update(reference_id: str, patch: ReferencePatch, session: Session = Depends(get_session)):
    reference = session.get(ReferenceCase, reference_id)
    if reference is None:
        return api_error("REFERENCE_NOT_FOUND", "没有找到这个参考案例", 404)
    for key, value in patch.model_dump(exclude_none=True).items():
        setattr(reference, key, value)
    touch_project_inputs(session, reference.project_id)
    session.commit()
    session.refresh(reference)
    return api_response(serialize(reference))


@router.delete("/api/references/{reference_id}")
def destroy(reference_id: str, request: Request, session: Session = Depends(get_session)):
    reference = session.get(ReferenceCase, reference_id)
    if reference is None:
        return api_error("REFERENCE_NOT_FOUND", "没有找到这个参考案例", 404)
    delete_reference(session, LocalStorage(request.app.state.settings.paths.uploads), reference_id)
    return api_response({"deleted": reference_id})


@router.post("/api/references/{reference_id}/analyze")
def analyze(reference_id: str, request: Request, session: Session = Depends(get_session)):
    try:
        analyze_reference(session, request.app.state.ai_provider, reference_id)
    except LookupError:
        return api_error("REFERENCE_NOT_FOUND", "没有找到这个参考案例", 404)
    except ReferenceAnalysisUnavailable as error:
        return api_error("REFERENCE_NEEDS_REVIEW", str(error), 409)
    except AIProviderError as error:
        messages = {
            "AI_AUTHENTICATION_ERROR": "模型服务认证失败，请检查 API Key",
            "AI_RATE_LIMIT_ERROR": "模型服务当前限流，请稍后重试",
            "AI_NETWORK_ERROR": "暂时无法连接模型服务，请稍后重试",
            "AI_REQUEST_ERROR": "模型服务拒绝了分析请求，请检查模型名称或接口兼容配置",
            "AI_RESPONSE_SCHEMA_ERROR": "模型返回格式不符合要求，请重试",
            "AI_CONTENT_ERROR": "模型无法处理当前案例内容，请调整后重试",
        }
        return api_error(error.code, messages.get(error.code, "模型分析失败，请稍后重试"), 502)
    return api_response(serialize(session.get(ReferenceCase, reference_id)))
