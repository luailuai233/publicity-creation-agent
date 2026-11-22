from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from workbench.ai.errors import AIProviderError


class ImageUnderstandingError(ValueError):
    pass


@dataclass(frozen=True)
class ImageUnderstanding:
    text: str
    summary: str
    status: str
    confidence: float = 0.0
    identity_inferred: bool = False
    is_demo: bool = False


def understand_image(
    path: Path,
    *,
    provider=None,
    human_description: str | None = None,
    max_pixels: int = 40_000_000,
) -> ImageUnderstanding:
    try:
        with Image.open(path) as image:
            width, height = image.size
            image_format = image.format
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageUnderstandingError("图片损坏或格式不可读") from exc
    if width * height > max_pixels:
        raise ImageUnderstandingError("图片像素超过限制")
    if human_description and human_description.strip():
        text = human_description.strip()
        return ImageUnderstanding(text=text, summary=text[:180], status="DONE", confidence=1.0)
    if provider is not None and hasattr(provider, "analyze_image"):
        try:
            envelope = provider.analyze_image(path.read_bytes(), Image.MIME.get(image_format, "image/png"))
        except AIProviderError:
            envelope = None
        if envelope is not None and envelope.status == "DONE" and envelope.result is not None:
            result = envelope.result
            needs_review = result.identity_inferred or result.confidence < 0.7
            return ImageUnderstanding(
                text=result.description,
                summary=result.summary,
                status="NEEDS_REVIEW" if needs_review else "DONE",
                confidence=result.confidence,
                identity_inferred=result.identity_inferred,
            )
    summary = f"{width}×{height} 图片尚未解析，请人工补充场景与可见文字说明。"
    return ImageUnderstanding(text="", summary=summary, status="NEEDS_REVIEW")
