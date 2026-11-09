from rest_framework import viewsets, permissions, parsers, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters import rest_framework as django_filters
from .models import User, Asset, Category, Tag, AssetVersion
from .serializers import (
    UserSerializer,
    AssetSerializer,
    CategorySerializer,
    TagSerializer,
    AssetVersionSerializer,
    MyTokenObtainPairSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .file_validators import validate_uploaded_file
from rest_framework.exceptions import ValidationError
from .input_validators import (
    validate_tags_input,
    validate_text_input,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from pathlib import Path
import mimetypes


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Return authenticated user's info."""
    user = request.user
    return Response(
        {
            "id": user.id,
            "username": user.username,
            "role": getattr(user, "role", None),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Blacklist a refresh token during logout."""
    refresh_token = request.data.get("refresh")

    if not isinstance(refresh_token, str) or not refresh_token:
        return Response(
            {"detail": "Refresh token is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = RefreshToken(refresh_token)

        # Prevent one authenticated user from revoking
        # another user's refresh token.
        if str(token.get("user_id")) != str(request.user.pk):
            return Response(
                {"detail": "Invalid refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token.blacklist()

    except TokenError:
        return Response(
            {"detail": "Invalid or expired refresh token."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"detail": "Logged out successfully."},
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------
# AUTH VIEW - LOGIN RATE LIMITING
# ---------------------------------------------------------------------
class LoginRateThrottle(AnonRateThrottle):
    scope = "login"
    rate = "5/min"


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


# Permissions are shared with file routes and serializer visibility filtering.
from .permissions import (
    AssetPermission, IsDAMAdmin, IsDAMMember, IsAdminOrReadOnly,
    check_tag_assignment, visible_assets, visible_versions,
)
from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import PermissionDenied


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsDAMAdmin]

    def perform_update(self, serializer):
        target = serializer.instance
        if target.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied('Only a superuser can change a superuser account.')
        if target.pk == self.request.user.pk and (
            serializer.validated_data.get('role', target.role) != 'admin'
            or not serializer.validated_data.get('is_active', target.is_active)
        ):
            raise PermissionDenied('You cannot remove your own administrator access.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise PermissionDenied('You cannot delete your own administrator account.')
        if instance.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied('Only a superuser can delete a superuser account.')
        instance.delete()


# ---------------------------------------------------------------------
# CATEGORY + TAGS
# ---------------------------------------------------------------------
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None  # optional, to simplify test_get_categories_list


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]


# ---------------------------------------------------------------------
# ASSET FILTERS
# ---------------------------------------------------------------------
class AssetFilter(django_filters.FilterSet):
    tags = django_filters.CharFilter(field_name="tags__name", lookup_expr="icontains")
    date_from = django_filters.DateFilter(field_name="uploaded_at", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="uploaded_at", lookup_expr="lte")
    category = django_filters.NumberFilter(field_name="category__id")

    class Meta:
        model = Asset
        fields = ["uploaded_by", "category", "tags", "date_from", "date_to"]


# ---------------------------------------------------------------------
# ASSETS
# ---------------------------------------------------------------------
class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.prefetch_related("tags", "versions", "category").all()
    serializer_class = AssetSerializer
    permission_classes = [AssetPermission]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = AssetFilter
    search_fields = ["title", "description", "metadata"]
    ordering_fields = ["uploaded_at", "title"]

    def get_queryset(self):
        return visible_assets(super().get_queryset(), self.request.user)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        if request.user.role == 'editor':
            # Every editor write uses the approval workflow, including direct PUT/PATCH.
            return self.request_update(request, pk=kwargs.get('pk'))
        asset = self.get_object()
        Asset.objects.select_for_update().get(pk=asset.pk)
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Handle both initial uploads and creation of new asset versions.
        """
        request = self.request

        if hasattr(request.data, "getlist"):
            raw_tags = request.data.getlist("tags[]")
            if not raw_tags:
                raw_tags = request.data.getlist("tags")
        else:
            raw_tags = request.data.get("tags[]")
            if raw_tags is None:
                raw_tags = request.data.get("tags")

        tag_names = validate_tags_input(raw_tags)
        check_tag_assignment(request.user, tag_names)

        if request.data.get('parent'):
            raise ValidationError({'parent': 'Use the asset request_update endpoint for new versions.'})

        asset = serializer.save(uploaded_by=request.user, created_by=request.user)

        for tname in tag_names:
            tag_obj, _ = Tag.objects.get_or_create(name=tname)
            asset.tags.add(tag_obj)

        # Create initial version entry automatically
        initial_version = AssetVersion.objects.create(
            asset=asset,
            file=asset.file,
            uploaded_by=request.user,
            version=asset.version,
            status="approved",
            title=asset.title,
            description=asset.description,
            category=asset.category,
        )

        # Copy validated tags to the initial version.
        initial_version.tags.set(asset.tags.all())

        return asset

    # -------------------- Editor submits new version --------------------
    @action(
        detail=True, methods=["post"], permission_classes=[AssetPermission]
    )
    @transaction.atomic
    def request_update(self, request, pk=None):
        """
        Admin and Editor can submit a new version of an asset.
        """
        asset = self.get_object()
        # Serialize version numbering against all other submissions for this asset.
        asset = Asset.objects.select_for_update().get(pk=asset.pk)
        user = request.user
        if not user or not getattr(user, "role", None):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        role = getattr(user, "role", "").lower()
        if role not in ("admin", "editor"):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        if 'parent' in request.data or 'metadata' in request.data:
            raise ValidationError({'detail': 'Parent and JSON metadata cannot be changed through version requests.'})
        file = request.FILES.get("file")

        if file is not None:
            validate_uploaded_file(file)

        comment = request.data.get("comment", "")

        title = validate_text_input(
            request.data.get("title", asset.title), "title", 120, required=True
        )

        description = validate_text_input(
            request.data.get("description", asset.description), "description", 2000
        )

        category_id = request.data.get("category_id", request.data.get("category"))
        category = asset.category

        if category_id not in (None, ""):
            try:
                category_int = int(category_id)
                category = Category.objects.filter(id=category_int).first()
            except (ValueError, TypeError):
                category = Category.objects.filter(name=category_id).first()

            if category is None:
                raise ValidationError({"category": "Please select a valid category."})

        tags_input = request.data.get("tags")
        tag_names = validate_tags_input(tags_input) if tags_input is not None else None
        if tag_names is not None:
            check_tag_assignment(request.user, tag_names)

        last_version = asset.versions.aggregate(number=Max('version'))['number'] or asset.version
        new_version = last_version + 1

        # -------------------- Create version with metadata --------------------
        version = AssetVersion.objects.create(
            asset=asset,
            file=file or asset.file,
            uploaded_by=user,
            version=new_version,
            status="pending",
            comment=comment,
            title=title,
            description=description,
            category=category,
        )

        # Set validated tags if provided
        if tag_names is None:
            version.tags.set(asset.tags.all())
        else:
            for tname in tag_names:
                tag_obj, _ = Tag.objects.get_or_create(name=tname)
                version.tags.add(tag_obj)

        serializer = AssetVersionSerializer(version, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------
# ASSET VERSIONS (Admin can approve/reject)
# ---------------------------------------------------------------------
class AssetVersionViewSet(viewsets.ModelViewSet):
    # Creation is through request_update; versions cannot be overwritten with PUT.
    http_method_names = ['get', 'head', 'options', 'patch', 'delete']
    serializer_class = AssetVersionSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = (
            AssetVersion.objects.select_related("uploaded_by", "asset", "category")
            .prefetch_related("tags")
            .all()
        )
        queryset = visible_versions(queryset, self.request.user)
        asset_id = self.request.query_params.get("asset_id")
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        return queryset.order_by("-version", "-uploaded_at")

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        asset = Asset.objects.select_for_update().get(pk=instance.asset_id)
        instance.refresh_from_db()
        user = request.user

        # Only admins can approve/reject
        if getattr(user, "role", "").lower() != "admin":
            return Response({"detail": "Admins only"}, status=status.HTTP_403_FORBIDDEN)

        status_value = request.data.get("status")
        if status_value not in ("approved", "rejected"):
            return Response(
                {"detail": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST
            )

        if set(request.data) != {'status'}:
            raise ValidationError({'detail': 'Only status may be changed on a submitted version.'})
        if instance.status != 'pending':
            raise ValidationError({'status': 'Only pending versions can be reviewed.'})
        if status_value == 'approved' and instance.version <= asset.version:
            raise ValidationError({'status': 'A newer version is already current.'})
        instance.status = status_value
        instance.save()

        # -------------------- APPROVAL LOGIC --------------------
        if status_value == "approved":

            # Update metadata fields
            asset.title = instance.title or asset.title
            asset.description = instance.description if instance.description is not None else asset.description
            asset.category = instance.category or asset.category

            asset.tags.set(instance.tags.all())

            # Do not overwrite file directly with same FileField instance
            if instance.file and instance.file.name != (
                asset.file.name if asset.file else ""
            ):
                # Publish the immutable stored version without copying or opening it.
                asset.file = instance.file.name

            asset.version = instance.version
            asset.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsDAMMember])
def protected_asset_file(request, asset_id):
    asset = get_object_or_404(visible_assets(Asset.objects.all(), request.user), pk=asset_id)

    # Use the latest approved file when available.
    latest = asset.latest_version()
    stored_file = latest.file if latest and latest.file else asset.file

    if not stored_file:
        raise Http404("File not found.")

    try:
        stored_file.open("rb")
        return FileResponse(
            stored_file,
            content_type=mimetypes.guess_type(stored_file.name)[0]
            or "application/octet-stream",
            as_attachment=False,
            filename=Path(stored_file.name).name,
        )
    except (FileNotFoundError, OSError):
        raise Http404("File not found.")


@api_view(["GET"])
@permission_classes([IsDAMMember])
def protected_version_file(request, version_id):
    version = get_object_or_404(visible_versions(AssetVersion.objects.all(), request.user), pk=version_id)

    if not version.file:
        raise Http404("File not found.")

    try:
        version.file.open("rb")
        return FileResponse(
            version.file,
            content_type=mimetypes.guess_type(version.file.name)[0]
            or "application/octet-stream",
            as_attachment=False,
            filename=Path(version.file.name).name,
        )
    except (FileNotFoundError, OSError):
        raise Http404("File not found.")
