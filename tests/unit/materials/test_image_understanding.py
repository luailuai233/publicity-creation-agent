from pathlib import Path

from PIL import Image

from workbench.materials.image_understanding import understand_image
from workbench.ai.envelope import AIEnvelope
from workbench.ai.errors import AINetworkError
from workbench.ai.schemas.material import ImageUnderstandingResult


def test_image_without_vision_model_requires_real_human_description(tmp_path: Path) -> None:
    path = tmp_path / "photo.png"
    Image.new("RGB", (40, 30), "white").save(path)

    result = understand_image(path)

    assert result.status == "NEEDS_REVIEW"
    assert result.is_demo is False
    assert "人工" in result.summary


def test_human_description_recovers_image_without_identity_inference(tmp_path: Path) -> None:
    path = tmp_path / "photo.png"
    Image.new("RGB", (40, 30), "white").save(path)

    result = understand_image(path, human_description="操场上正在进行科学实验展示")

    assert result.status == "DONE"
    assert result.text == "操场上正在进行科学实验展示"
    assert result.identity_inferred is False


def test_visual_failure_and_identity_inference_both_require_review(tmp_path: Path) -> None:
    path = tmp_path / "photo.png"
    Image.new("RGB", (40, 30), "white").save(path)

    class FailingProvider:
        def analyze_image(self, _image_bytes, _mime_type):
            raise AINetworkError("offline")

    class IdentityProvider:
        def analyze_image(self, _image_bytes, _mime_type):
            return AIEnvelope(
                result=ImageUnderstandingResult(
                    description="画面中有人物",
                    summary="人物活动现场",
                    confidence=0.9,
                    identity_inferred=True,
                )
            )

    assert understand_image(path, provider=FailingProvider()).status == "NEEDS_REVIEW"
    identity = understand_image(path, provider=IdentityProvider())
    assert identity.status == "NEEDS_REVIEW"
    assert identity.identity_inferred is True
