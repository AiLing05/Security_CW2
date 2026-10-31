from rest_framework import serializers
from .models import User, Asset, Category, Tag, AssetVersion
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.hashers import make_password
from .file_validators import validate_uploaded_file
import json
from .input_validators import (
    validate_text_input,
    validate_tag_name,
    validate_category_name,
    validate_tags_input,
)

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

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


    # Require a password when creating a new user
    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({
                "password": "Password is required."
            })

        # Check similarity against user attributes
        if "password" in attrs:
            user = User(
                username=attrs.get(
                    "username",
                    self.instance.username if self.instance else ""
                ),
                email=attrs.get(
                    "email",
                    self.instance.email if self.instance else ""
                ),
                first_name=attrs.get(
                    "first_name",
                    self.instance.first_name if self.instance else ""
                ),
                last_name=attrs.get(
                    "last_name",
                    self.instance.last_name if self.instance else ""
                ),
            )

            try:
                validate_password(attrs["password"], user=user)
            except DjangoValidationError as error:
                raise serializers.ValidationError({
                    "password": error.messages
                })

        return attrs

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

    def validate_name(self, value):
        return validate_tag_name(value)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]

    def validate_name(self, value):
        return validate_category_name(value)


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

    def validate_file(self, value):
        return validate_uploaded_file(value)

    def validate_title(self, value):
        if value is None:
            return value
        return validate_text_input(
            value, "title", 120, required=True
        )

    def validate_description(self, value):
        if value is None:
            return value
        return validate_text_input(
            value, "description", 2000
        )

    def validate_category_id(self, value):
        if not Category.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                "Please select a valid category."
            )
        return value


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

    def validate_file(self, value):
        return validate_uploaded_file(value)

    def validate_title(self, value):
        return validate_text_input(
            value, "title", 120, required=True
        )

    def validate_description(self, value):
        return validate_text_input(
            value, "description", 2000
        )

    def validate_category_id(self, value):
        if not Category.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                "Please select a valid category."
            )
        return value

    def validate_metadata(self, value):
        if value is None:
            return value

        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Metadata must be a JSON object."
            )

        if len(json.dumps(value, ensure_ascii=False)) > 4096:
            raise serializers.ValidationError(
                "Metadata is too large."
            )

        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        # Require category when creating a new asset.
        if self.instance is None and not self.initial_data.get("parent"):
            if not attrs.get("category_id"):
                raise serializers.ValidationError({
                    "category_id": "Please select a category."
                })

        # Prevent clearing category when updating an existing asset.
        if self.instance is not None:
            if "category_id" in self.initial_data:
                raw_category = self.initial_data.get("category_id")

                if raw_category is None or str(raw_category).strip() == "":
                    raise serializers.ValidationError({
                        "category_id": "Please select a category."
                    })

        return attrs
    
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
            rep["tags"] = TagSerializer(latest.tags.all() if latest.tags.exists() else instance.tags.all(), many=True).data
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

        # Read tags submitted by the Asset Details page.
        raw_tags = None

        if request is not None and "tags" in request.data:
            raw_tags = request.data.get("tags")

        # Validate tags before changing or saving the asset.
        if raw_tags is not None:
            validated_tags = validate_tags_input(raw_tags)

        elif tag_names is not None:
            validated_tags = validate_tags_input(tag_names)

        elif tags_data is not None:
            names = [
                item.get("name") if isinstance(item, dict) else item
                for item in tags_data
            ]
            validated_tags = validate_tags_input(names)

        else:
            validated_tags = None

        # Update basic metadata.
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update category.
        if category_id is not None:
            instance.category = Category.objects.get(pk=category_id)

        # Update tags only after validation succeeds.
        if validated_tags is not None:
            instance.tags.clear()

            for name in validated_tags:
                tag_obj, _ = Tag.objects.get_or_create(name=name)
                instance.tags.add(tag_obj)

        # Create a new asset version if needed.
        if new_file or (user and user.role == "admin"):
            latest_version = instance.latest_version()
            version_number = (
                latest_version.version + 1
                if latest_version else 1
            )

            asset_version = AssetVersion.objects.create(
                asset=instance,
                file=new_file if new_file else instance.file,
                uploaded_by=user if user else None,
                version=version_number,
                status="approved" if (
                    user and user.role == "admin"
                ) else "pending",
                title=validated_data.get("title", instance.title),
                description=validated_data.get(
                    "description", instance.description
                ),
                category=instance.category,
            )

            # Copy validated tags into the new version.
            for tag in instance.tags.all():
                asset_version.tags.add(tag)

        instance.save()
        return instance

