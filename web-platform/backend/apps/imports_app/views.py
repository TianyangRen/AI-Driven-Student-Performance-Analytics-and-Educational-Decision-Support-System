from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from common.responses import ok, fail
from apps.courses.models import CourseSection
from .models import ImportBatch


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def create_import(request, section_id):
    try:
        section = CourseSection.objects.get(id=section_id)
    except CourseSection.DoesNotExist:
        return fail("RESOURCE_NOT_FOUND", "教学班不存在", 404)
    upload = request.FILES.get("file")
    if not upload:
        return fail("VALIDATION_FAILED", "缺少文件", 422)
    import_type = request.data.get("import_type", "MIXED")
    batch = ImportBatch.objects.create(
        section=section,
        uploaded_by=request.user,
        file_name=upload.name,
        import_type=import_type,
        status="VALIDATING",
        total_rows=0,
        valid_rows=0,
    )
    return ok({
        "batch_id": batch.id,
        "section_id": section.id,
        "import_type": batch.import_type,
        "status": batch.status,
        "file_name": batch.file_name,
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
        "file_name": batch.file_name,
        "import_type": batch.import_type,
        "created_at": batch.created_at,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_errors(request, batch_id):
    return ok({"batch_id": batch_id, "errors": []})
