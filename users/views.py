from .models import *
from .serializers import *
from Filedigital.ResponseFunction import *
from djoser.views import UserViewSet

class CustomUserViewSet(UserViewSet):
    def get_serializer_class(self):
        if self.action == "create":  # Ensure custom serializer is used for registration
            return CustomUserCreateSerializer
        return super().get_serializer_class()