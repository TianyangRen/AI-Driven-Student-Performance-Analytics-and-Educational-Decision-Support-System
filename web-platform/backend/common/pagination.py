import uuid

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


def _request_id():
    return f"req_{uuid.uuid4().hex[:12]}"


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        return Response({
            "success": True,
            "data": data,
            "meta": {
                "page": self.page.number,
                "page_size": self.page.paginator.per_page,
                "total": self.page.paginator.count,
                "next": self.get_next_link(),
                "prev": self.get_previous_link(),
            },
        })


class RosterPagination(PageNumberPagination):
    """班级名单/预测列表用：默认页很大以覆盖任何真实教学班规模，
    仅对异常膨胀的数据集起「封顶」作用，避免无界响应。"""

    page_size = 500
    page_size_query_param = "page_size"
    max_page_size = 1000


def paginate_list(request, items, extra_meta=None):
    """把一个已排好序的 list 分页并按统一响应封装返回。

    默认 page_size 足够大（见 RosterPagination），普通班级一页返回全部，
    前端读取 `data` 数组的行为不变；同时把无界响应封顶。extra_meta 会
    并入 meta（供 list_predictions 携带 run_id / model_version 等）。
    """
    paginator = RosterPagination()
    page = paginator.paginate_queryset(items, request)
    meta = {
        "request_id": _request_id(),
        "page": paginator.page.number,
        "page_size": paginator.page.paginator.per_page,
        "total": paginator.page.paginator.count,
        "next": paginator.get_next_link(),
        "prev": paginator.get_previous_link(),
        **(extra_meta or {}),
    }
    return Response({"success": True, "data": page, "meta": meta})
