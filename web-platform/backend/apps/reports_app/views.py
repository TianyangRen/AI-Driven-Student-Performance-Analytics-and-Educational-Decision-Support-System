import os

from django.http import FileResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.courses.models import CourseSection
from common.responses import ok, fail
from . import generators
from .models import ReportExport

_SECTION_TYPES = {"CLASS_SUMMARY", "RISK_LIST"}
_VALID_TYPES = {"CLASS_SUMMARY", "RISK_LIST", "COMPARISON"}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_report(request):
    """创建并同步生成报告（真实 xlsx 落盘）。

    Body:
      report_type: CLASS_SUMMARY | RISK_LIST | COMPARISON
      section_id:  CLASS_SUMMARY / RISK_LIST 必填
      dimension:   COMPARISON 用（SECTION|COURSE|TERM|ASSESSMENT_TYPE）
    """
    body = request.data
    rt = (body.get("report_type") or "CLASS_SUMMARY").upper()
    if rt not in _VALID_TYPES:
        return fail("VALIDATION_FAILED", f"report_type 必须是 {', '.join(sorted(_VALID_TYPES))} 之一", 422)

    section = None
    if rt in _SECTION_TYPES:
        section_id = body.get("section_id")
        if not section_id:
            return fail("VALIDATION_FAILED", f"{rt} 需要 section_id", 422)
        try:
            section = CourseSection.objects.select_related("course").get(id=section_id)
        except CourseSection.DoesNotExist:
            return fail("RESOURCE_NOT_FOUND", "教学班不存在", 404)
        if not request.user.is_admin and section.instructor_id != request.user.id:
            return fail("FORBIDDEN", "无权访问该教学班", 403)

    report = ReportExport.objects.create(
        section=section, requested_by=request.user,
        report_type=rt, parameters=body, status="PROCESSING",
    )
    try:
        path = generators.generate(report)
    except Exception as exc:  # noqa: BLE001 —— 生成失败标 FAILED 并回报
        report.status = "FAILED"
        report.save(update_fields=["status"])
        return fail("REPORT_GENERATION_FAILED", str(exc), 500)

    report.file_path = path
    report.status = "SUCCESS"
    report.save(update_fields=["file_path", "status"])
    return ok({"report_id": report.id, "status": report.status,
               "report_type": report.report_type, "expires_at": report.expires_at})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_report(request, report_id):
    try:
        report = ReportExport.objects.get(id=report_id)
    except ReportExport.DoesNotExist:
        return fail("RESOURCE_NOT_FOUND", "报告不存在", 404)
    return ok({
        "report_id": report.id, "status": report.status,
        "report_type": report.report_type, "created_at": report.created_at,
        "expires_at": report.expires_at,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_report(request, report_id):
    try:
        report = ReportExport.objects.get(id=report_id)
    except ReportExport.DoesNotExist:
        return fail("RESOURCE_NOT_FOUND", "报告不存在", 404)
    if report.expires_at and report.expires_at < timezone.now():
        if report.status != "EXPIRED":
            report.status = "EXPIRED"
            report.save(update_fields=["status"])
        return fail("REPORT_EXPIRED", "报告已过期", 410)
    if report.status != "SUCCESS" or not report.file_path or not os.path.exists(report.file_path):
        return fail("REPORT_NOT_READY", "报告文件不可用，请重新生成", 409)

    return FileResponse(
        open(report.file_path, "rb"),
        as_attachment=True,
        filename=generators.filename_for(report),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
