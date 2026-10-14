from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (FileViewSet, CategoryViewSet, FileApprovalViewSet,
                FileActivityLogViewSet,AccessRequestViewSet)
from . import views
from .views import (FileViewSet, CategoryViewSet, FileApprovalViewSet, FileActivityLogViewSet)
from .views import report_data

router = DefaultRouter()
router.register('files', FileViewSet)
router.register('categories', CategoryViewSet)
router.register('approvals', FileApprovalViewSet)
# router.register('ocrdata', OCRDataViewSet)
router.register('fileactivity', FileActivityLogViewSet)
router.register('access', AccessRequestViewSet, basename='access-request')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/files/<int:pk>/restore/', FileViewSet.as_view({'post': 'restore'}), name='file-restore'),
    path('api/files/<int:pk>/get_ocr_text/', FileViewSet.as_view({'post': 'restore'}), name='file-restore'),

    # path('admin/report-data/', report_data, name='report_data'),
    path('api/admin/report-data/', report_data, name='report_data'),
]