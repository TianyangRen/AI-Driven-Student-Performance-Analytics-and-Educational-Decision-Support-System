from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


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
