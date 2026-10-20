from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer

User = get_user_model()

class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        # Never accept a client-selected role during public registration.
        fields = ('id', 'email', 'password', 'name', 'phone', 'location')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user_role, _ = Group.objects.get_or_create(name='User')
        user = super().create(validated_data)
        user.role = user_role
        user.groups.add(user_role)
        user.save(update_fields=['role'])
        return user
