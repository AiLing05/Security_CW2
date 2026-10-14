from django.urls import path
from .views import *




urlpatterns = [
    path('auth/users/', CustomUserViewSet.as_view({'post': 'create'}), name='register'),
]