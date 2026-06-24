import uuid
from rest_framework.response import Response
from rest_framework.views import exception_handler


def _request_id():
    return f"req_{uuid.uuid4().hex[:12]}"


def ok(data=None, status=200, meta=None):
    payload = {"success": True, "data": data, "meta": {"request_id": _request_id(), **(meta or {})}}
    return Response(payload, status=status)


def fail(code, message, http_status=400, details=None):
    return Response(
        {
            "success": False,
            "error": {"code": code, "message": message, "details": details or []},
            "meta": {"request_id": _request_id()},
        },
        status=http_status,
    )


def unified_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    detail = response.data
    code = "ERROR"
    message = "Request failed"
    details = []
    if isinstance(detail, dict):
        if "detail" in detail:
            message = str(detail["detail"])
            code = getattr(detail["detail"], "code", "ERROR").upper()
        else:
            message = "Validation failed"
            code = "VALIDATION_FAILED"
            details = [{"field": k, "reason": v if isinstance(v, str) else " ".join(map(str, v))}
                       for k, v in detail.items()]
    response.data = {
        "success": False,
        "error": {"code": code, "message": message, "details": details},
        "meta": {"request_id": _request_id()},
    }
    return response
