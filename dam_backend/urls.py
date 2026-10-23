from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from rest_framework import routers
from assets.views import (
    UserViewSet, AssetViewSet, CategoryViewSet,
    TagViewSet, AssetVersionViewSet, MyTokenObtainPairView, me_view
)
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

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
    path("api/", include(router.urls)),
    path("api/me/", me_view, name="me"),  # ✅ added route
    path("api/token/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("", home),
]

# ✅ Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
