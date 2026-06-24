from rest_framework.routers import DefaultRouter
from .views import CourseViewSet, CourseSectionViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"sections", CourseSectionViewSet, basename="section")

urlpatterns = router.urls
