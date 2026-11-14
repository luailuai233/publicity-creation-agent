import uuid
from typing import Any, Optional

from fastapi.responses import JSONResponse


def api_response(data: Any = None, error: Optional[dict] = None, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"data": data, "error": error, "requestId": str(uuid.uuid4())},
    )


def api_error(code: str, message: str, status_code: int, details: Any = None) -> JSONResponse:
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return api_response(error=error, status_code=status_code)
