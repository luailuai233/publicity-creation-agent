from pathlib import Path


def infer_material_category(file_name: str, fallback: str = "OTHER") -> str:
    name = Path(file_name).stem.lower()
    rules = (
        ("INTERVIEW", ("采访", "访谈", "interview")),
        ("SPEECH", ("发言", "讲话", "致辞", "speech")),
        ("FLOW", ("流程", "议程", "安排", "活动方案", "flow", "schedule")),
        ("PHOTO", ("照片", "图片", "photo", "image")),
        ("NOTE", ("笔记", "备忘", "note")),
    )
    for category, markers in rules:
        if any(marker in name for marker in markers):
            return category
    return fallback
