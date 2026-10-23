from rest_framework import serializers
from .models import User, Asset, Category, Tag, AssetVersion
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.hashers import make_password


# --------------------------
# JWT Token Serializer with role
# --------------------------
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['username'] = self.user.username
        data['role'] = self.user.role
        return data


# --------------------------
# User Serializer
# --------------------------
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "role",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.password = make_password(password)
        instance.save()
        return instance


# --------------------------
# Tag & Category Serializers
# --------------------------
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


# --------------------------
# AssetVersion Serializer
# --------------------------
class AssetVersionSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False)
    tag_names = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = AssetVersion
        fields = [
            "id",
            "file",
            "uploaded_at",
            "uploaded_by",
            "version",
            "status",
            "comment",
            "title",
            "description",
            "category",
            "category_id",
            "tags",
            "tag_names",
        ]
        read_only_fields = ["uploaded_at", "uploaded_by", "version", "status"]


# --------------------------
# Asset Serializer
# --------------------------
class AssetSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False)
    tags = TagSerializer(many=True, read_only=True)
    versions = AssetVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Asset
        fields = [
            "id",
            "title",
            "description",
            "file",
            "uploaded_at",
            "uploaded_by",
            "category_id",
            "tags",
            "metadata",
            "version",
            "parent",
            "versions",
        ]
        read_only_fields = ("uploaded_by", "version", "uploaded_at", "versions")

    # Always return latest approved version for frontend
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        latest = instance.latest_version()
        if latest:
            rep["title"] = latest.title or instance.title
            rep["description"] = latest.description or instance.description
            rep["file"] = latest.file.url if latest.file else instance.file.url
            rep["version"] = latest.version or instance.version
            rep["category"] = CategorySerializer(latest.category).data if latest.category else (
                CategorySerializer(instance.category).data if instance.category else None
            )
            rep["tags"] = TagSerializer(latest.tags.all(), many=True).data
        else:
            rep["title"] = instance.title
            rep["description"] = instance.description
            rep["file"] = instance.file.url if instance.file else None
            rep["version"] = instance.version
            rep["category"] = CategorySerializer(instance.category).data if instance.category else None
            rep["tags"] = TagSerializer(instance.tags.all(), many=True).data
        return rep

    # Update Asset → create new version if file or admin edits
    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        category_id = validated_data.pop("category_id", None)
        tag_names = validated_data.pop("tag_names", None)
        tags_data = validated_data.pop("tags", None)
        new_file = validated_data.pop("file", None)

        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update category
        if category_id:
            try:
                category = Category.objects.get(pk=category_id)
                instance.category = category
            except Category.DoesNotExist:
                pass

        # Update tags from tag_names
        if tag_names is not None:
            instance.tags.clear()
            for t in [x.strip() for x in tag_names.split(",") if x.strip()]:
                tag_obj, _ = Tag.objects.get_or_create(name=t)
                instance.tags.add(tag_obj)

        # Update tags from tags_data
        if tags_data is not None:
            instance.tags.clear()
            for t in tags_data:
                tag_obj, _ = Tag.objects.get_or_create(name=t.get("name"))
                instance.tags.add(tag_obj)

        # Create new version if file changed or admin edits
        if new_file or (user and user.role == "admin"):
            latest_version = instance.latest_version()
            version_number = (latest_version.version + 1) if latest_version else 1

            asset_version = AssetVersion.objects.create(
                asset=instance,
                file=new_file if new_file else instance.file,
                uploaded_by=user if user else None,
                version=version_number,
                status="approved" if (user and user.role == "admin") else "pending",
                title=validated_data.get("title", instance.title),
                description=validated_data.get("description", instance.description),
                category=instance.category,
            )

            # Copy tags
            for tag in instance.tags.all():
                asset_version.tags.add(tag)

        instance.save()
        return instance
