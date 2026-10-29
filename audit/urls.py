from django.urls import include, path
from rest_framework import routers

from .views import AuditIntegrityView, SecurityEventViewSet, SecuritySummaryView

router = routers.DefaultRouter()
router.register(r"events", SecurityEventViewSet, basename="audit-events")

urlpatterns = [
    path("summary/", SecuritySummaryView.as_view(), name="audit-summary"),
    path("integrity/", AuditIntegrityView.as_view(), name="audit-integrity"),
    path("", include(router.urls)),
]
