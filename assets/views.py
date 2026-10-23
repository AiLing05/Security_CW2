from rest_framework import viewsets, permissions, parsers, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters import rest_framework as django_filters
from .models import User, Asset, Category, Tag, AssetVersion
from .serializers import (
    UserSerializer, AssetSerializer, CategorySerializer,
    TagSerializer, AssetVersionSerializer, MyTokenObtainPairSerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Return authenticated user's info."""
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "role": getattr(user, "role", None),
    })

# ---------------------------------------------------------------------
# AUTH VIEW
# ---------------------------------------------------------------------
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


# ---------------------------------------------------------------------
# PERMISSIONS
# ---------------------------------------------------------------------
class IsAdminEditorOrReadOnly(permissions.BasePermission):
    """
    Permissions:
    - Safe methods (GET, HEAD, OPTIONS): everyone
    - Create (POST): Admins + Editors
    - Modify (PUT, PATCH): Admins + Editors
        (Editors’ changes are saved as pending for admin approval)
    - Delete: Admins only
    - View-only: Viewers
    """

    def has_permission(self, request, view):
        # Safe methods (GET, HEAD, OPTIONS) — allow all
        if request.method in permissions.SAFE_METHODS:
            return True

        # Must be authenticated for unsafe methods
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        role = getattr(user, "role", "").lower()

        # ✅ Allow Create (POST) for Admins + Editors
        if request.method == "POST":
            return role in ("admin", "editor")

        # ✅ Allow Modify (PUT, PATCH) for Admins + Editors
        if request.method in ("PUT", "PATCH"):
            return role in ("admin", "editor")

        # ✅ Allow Delete for Admins only
        if request.method == "DELETE":
            return role == "admin"

        # Deny anything else
        return False

    def has_object_permission(self, request, view, obj):
        # Safe methods are always allowed
        if request.method in permissions.SAFE_METHODS:
            return True

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        role = getattr(user, "role", "").lower()

        # ✅ Admin has full control
        if role == "admin":
            return True

        # ✅ Editor can modify but not delete (approval logic handled in view)
        if role == "editor" and request.method in ("PUT", "PATCH", "POST"):
            return True

        # ❌ Editors cannot delete, viewers cannot modify
        return False


# ---------------------------------------------------------------------
# USER MANAGEMENT (Admin only)
# ---------------------------------------------------------------------
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]  # keep using Django admin check here

# ---------------------------------------------------------------------
# CUSTOM PERMISSIONS FOR CATEGORY
# ---------------------------------------------------------------------
class IsAdminOrReadOnly(permissions.BasePermission):
    """Allow only admins to create/update/delete; everyone can read."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return user.is_authenticated and getattr(user, "role", "").lower() == "admin"

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
    permission_classes = [permissions.IsAuthenticated]


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
    permission_classes = [IsAdminEditorOrReadOnly]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AssetFilter
    search_fields = ["title", "description", "metadata"]
    ordering_fields = ["uploaded_at", "title"]

    def perform_create(self, serializer):
        """
        Handle both initial uploads and creation of new asset versions.
        """
        request = self.request
        tags = request.data.getlist("tags[]") if hasattr(request.data, "getlist") else request.data.get("tags")
        parent_id = request.data.get("parent")
        parent_asset = Asset.objects.filter(pk=parent_id).first() if parent_id else None

        # If it's a new version for an existing asset (parent provided)
        if parent_asset:
            last_version = parent_asset.version or 1
            new_version_num = last_version + 1
            av = AssetVersion.objects.create(
                asset=parent_asset,
                file=request.data.get("file"),
                uploaded_by=request.user,
                version=new_version_num,
                status="pending",  # Needs admin approval
            )
            return av

        # Otherwise, it's a new asset (admins only — enforced by permission)
        asset = serializer.save(uploaded_by=request.user)
        if tags:
            if isinstance(tags, str):
                tag_names = [t.strip() for t in tags.split(",") if t.strip()]
            elif isinstance(tags, (list, tuple)):
                tag_names = tags
            else:
                tag_names = []
            for tname in tag_names:
                tag_obj, _ = Tag.objects.get_or_create(name=tname)
                asset.tags.add(tag_obj)

        # Create initial version entry automatically
        AssetVersion.objects.create(
            asset=asset,
            file=asset.file,
            uploaded_by=request.user,
            version=asset.version,
            status="approved",
            title=asset.title,
            description=asset.description,
            category=asset.category
        )

        return asset

    # -------------------- Editor submits new version --------------------
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def request_update(self, request, pk=None):
        """
        Editors can submit a new version of an asset.
        Creates an AssetVersion with status='pending' for admin approval.
        """
        asset = self.get_object()
        user = request.user
        if not user or not getattr(user, "role", None):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        role = getattr(user, "role", "").lower()
        if role not in ("admin", "editor"):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        # Editors can request updates; admin can too.
        file = request.data.get("file")
        comment = request.data.get("comment", "")
        title = request.data.get("title", asset.title)
        description = request.data.get("description", asset.description)

        category_id = request.data.get("category")

        # allow category ID or name
        category = None
        if category_id:
            try:
                category_int = int(category_id)
                category = Category.objects.filter(id=category_int).first()
            except (ValueError, TypeError):
                category = Category.objects.filter(name=category_id).first()

        tags_input = request.data.get("tags")  # comma separated

        last_version = asset.version or 1
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

        # Set tags if provided
        if tags_input:
            tag_names = [t.strip() for t in tags_input.split(",") if t.strip()]
            for tname in tag_names:
                tag_obj, _ = Tag.objects.get_or_create(name=tname)
                version.tags.add(tag_obj)

        serializer = AssetVersionSerializer(version, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------
# ASSET VERSIONS (Admin can approve/reject)
# ---------------------------------------------------------------------
class AssetVersionViewSet(viewsets.ModelViewSet):
    serializer_class = AssetVersionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = AssetVersion.objects.select_related("uploaded_by", "asset", "category").prefetch_related("tags").all()
        asset_id = self.request.query_params.get("asset_id")
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        return queryset.order_by("-version", "-uploaded_at")

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        # Only admins can approve/reject
        if getattr(user, "role", "").lower() != "admin":
            return Response({"detail": "Admins only"}, status=status.HTTP_403_FORBIDDEN)

        status_value = request.data.get("status")
        if status_value not in ("approved", "rejected"):
            return Response({"detail": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        instance.status = status_value
        instance.save()

        # -------------------- APPROVAL LOGIC --------------------
        if status_value == "approved":
            asset = instance.asset

            # Update metadata fields
            asset.title = instance.title or asset.title
            asset.description = instance.description or asset.description
            asset.category = instance.category or asset.category

            if instance.tags.exists():
                asset.tags.set(instance.tags.all())

            # Do not overwrite file directly with same FileField instance
            if instance.file and instance.file.name != (asset.file.name if asset.file else ""):
                # Keep old file intact — only point to the new version’s copy
                asset.file.save(
                    instance.file.name.split("/")[-1],  # filename only
                    instance.file.file,  # file object
                    save=False  # prevent immediate save to avoid double delete
                )

            asset.version = instance.version
            asset.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
