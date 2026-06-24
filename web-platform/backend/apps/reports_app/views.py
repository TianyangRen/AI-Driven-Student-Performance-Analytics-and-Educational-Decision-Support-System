from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from common.responses import ok, fail
from .models import ReportExport


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_report(request):
    body = request.data
    section_id = body.get("section_id")
    rt = body.get("report_type", "CLASS_SUMMARY")
    report = ReportExport.objects.create(
        section_id=section_id,
        requested_by=request.user,
        report_type=rt,
        parameters=body,
        status="SUCCESS",
        file_path=f"/data/reports/demo-{rt.lower()}.txt",
    )
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
        return fail("REPORT_EXPIRED", "报告已过期", 410)
    content = f"[DEMO REPORT]\nType: {report.report_type}\nParameters: {report.parameters}\n"
    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f"attachment; filename=report_{report.id}.txt"
    return response
