from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from rest_framework import routers
from assets.views import (
    UserViewSet, AssetViewSet, CategoryViewSet,
    TagViewSet, AssetVersionViewSet, MyTokenObtainPairView,
    me_view, logout_view, protected_asset_file, protected_version_file
)
from rest_framework_simplejwt.views import TokenRefreshView


router = routers.DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"assets", AssetViewSet, basename="assets")
router.register(r"categories", CategoryViewSet)
router.register(r"tags", TagViewSet)
router.register(r"versions", AssetVersionViewSet, basename="versions")


def home(request):
    return JsonResponse({"message": "Welcome to the DAM backend API!"})


urlpatterns = [
    path("admin/", admin.site.urls),

    # Protected file access routes
    path(
        "api/assets/<int:asset_id>/file/",
        protected_asset_file,
        name="protected_asset_file",
    ),
    path(
        "api/versions/<int:version_id>/file/",
        protected_version_file,
        name="protected_version_file",
    ),

    path("api/", include(router.urls)),
    path("api/me/", me_view, name="me"),
    path("api/logout/", logout_view, name="logout"),
    path("api/audit/", include("audit.urls")),
    path("api/token/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("", home),
]

# Safe error handlers
handler400 = "dam_backend.error_views.bad_request"
handler403 = "dam_backend.error_views.permission_denied"
handler404 = "dam_backend.error_views.page_not_found"
handler500 = "dam_backend.error_views.server_error"