import json

from workbench.logging import sanitize_event


def test_sanitize_event_removes_secrets_sensitive_text_and_phone_but_keeps_trace_ids() -> None:
    event = sanitize_event({
        "request_id": "req-123", "project_id": "project-1", "run_id": "run-1", "step_id": "step-1",
        "authorization": "Bearer sk-secret-value", "api_key": "sk-secret-value",
        "prompt": "完整提示词", "reference_text": "案例原文", "upload_text": "上传正文",
        "error": "失败，联系人 13812345678，token=sk-secret-value",
    })
    serialized = json.dumps(event, ensure_ascii=False)

    assert all(value in serialized for value in ("req-123", "project-1", "run-1", "step-1"))
    assert all(value not in serialized for value in ("sk-secret-value", "完整提示词", "案例原文", "上传正文", "13812345678"))
    assert "[REDACTED]" in serialized
