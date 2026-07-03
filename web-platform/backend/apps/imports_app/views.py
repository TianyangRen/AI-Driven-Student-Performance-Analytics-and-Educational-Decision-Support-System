import csv
import io

from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from common.responses import ok, fail
from apps.courses.models import CourseSection
from . import parsers as file_parsers
from . import services
from .models import ImportBatch
from .templates import (
    TEMPLATE_TYPES,
    example_row_for,
    header_for,
    columns_for,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_template(request):
    """
    GET /api/v1/imports/template?type=ROSTER|SCORE|ACTIVITY&fmt=csv|xlsx

    注意：文件格式参数用 fmt（不用 format）——DRF 保留 `format` 作为内容协商的
    渲染器后缀，传 ?format=csv 会在进入本视图前被判成未知 renderer 而 404。
    """
    import_type = (request.query_params.get("type") or "").upper()
    fmt = (request.query_params.get("fmt") or "csv").lower()
    if import_type not in TEMPLATE_TYPES:
        return fail("VALIDATION_FAILED", f"type 必须是 {', '.join(TEMPLATE_TYPES)} 之一", 422)
    if fmt not in ("csv", "xlsx"):
        return fail("VALIDATION_FAILED", "fmt 必须是 csv 或 xlsx", 422)

    header = header_for(import_type)
    example = example_row_for(import_type)
    filename = f"template_{import_type.lower()}.{fmt}"

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(header)
        writer.writerow(example)
        content = buf.getvalue().encode("utf-8-sig")  # BOM 便于 Excel 直接打开
        response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    else:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = import_type
        ws.append(header)
        ws.append(example)
        out = io.BytesIO()
        wb.save(out)
        response = HttpResponse(
            out.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def create_import(request, section_id):
    """POST /api/v1/sections/{section_id}/imports —— 上传并同步解析落库。"""
    try:
        section = CourseSection.objects.get(id=section_id)
    except CourseSection.DoesNotExist:
        return fail("RESOURCE_NOT_FOUND", "教学班不存在", 404)

    upload = request.FILES.get("file")
    if not upload:
        return fail("VALIDATION_FAILED", "缺少文件", 422)

    import_type = (request.data.get("import_type") or "").upper()
    if import_type not in TEMPLATE_TYPES:
        return fail("VALIDATION_FAILED", f"import_type 必须是 {', '.join(TEMPLATE_TYPES)} 之一", 422)

    batch = ImportBatch.objects.create(
        section=section,
        uploaded_by=request.user,
        file_name=upload.name,
        import_type=import_type,
        status="VALIDATING",
    )

    required = [c.name for c in columns_for(import_type) if c.required]
    try:
        rows = file_parsers.parse(upload, upload.name, required)
    except file_parsers.MissingColumns as exc:
        batch.status = "FAILED"
        batch.error_details = [{"row": 1, "column": ", ".join(exc.missing),
                                "value": "", "reason": "missing required column(s)"}]
        batch.save(update_fields=["status", "error_details"])
        return fail("VALIDATION_FAILED", str(exc), 422,
                    [{"field": "file", "reason": str(exc)}])
    except file_parsers.UnsupportedFormat as exc:
        batch.status = "FAILED"
        batch.save(update_fields=["status"])
        return fail("VALIDATION_FAILED", str(exc), 422)

    services.process_import(batch, rows, import_type)

    return ok({
        "batch_id": batch.id,
        "section_id": section.id,
        "import_type": batch.import_type,
        "status": batch.status,
        "file_name": batch.file_name,
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "error_count": len(batch.error_details or []),
    }, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_import(request, batch_id):
    try:
        batch = ImportBatch.objects.get(id=batch_id)
    except ImportBatch.DoesNotExist:
        return fail("RESOURCE_NOT_FOUND", "导入批次不存在", 404)
    return ok({
        "batch_id": batch.id,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "error_count": len(batch.error_details or []),
        "file_name": batch.file_name,
        "import_type": batch.import_type,
        "created_at": batch.created_at,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_errors(request, batch_id):
    try:
        batch = ImportBatch.objects.get(id=batch_id)
    except ImportBatch.DoesNotExist:
        return fail("RESOURCE_NOT_FOUND", "导入批次不存在", 404)
    return ok({"batch_id": batch.id, "errors": batch.error_details or []})
