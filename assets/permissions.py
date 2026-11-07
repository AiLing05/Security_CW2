"""DAM authorization policy. Database roles, never client/JWT role claims, decide access."""
from django.db.models import Q
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import ValidationError


def active_member(user):
    return bool(user and user.is_authenticated and user.is_active
                and user.role in {'admin', 'editor', 'viewer'})


def is_admin(user):
    return active_member(user) and user.role == 'admin'


def can_edit_asset(user, asset):
    return active_member(user) and (is_admin(user) or
        (user.role == 'editor' and asset.uploaded_by_id == user.pk))


def check_tag_assignment(user, names):
    from .models import Tag
    if not is_admin(user):
        existing = set(Tag.objects.filter(name__in=names).values_list('name', flat=True))
        if set(names) - existing:
            raise ValidationError({'tags': 'Choose existing tags; only admins may create tags.'})


def visible_assets(queryset, user):
    if not active_member(user):
        return queryset.none()
    if is_admin(user):
        return queryset
    condition = Q(versions__status='approved')
    if user.role == 'editor':
        condition |= Q(uploaded_by=user)
    return queryset.filter(condition).distinct()


def visible_versions(queryset, user):
    if not active_member(user):
        return queryset.none()
    if is_admin(user):
        return queryset
    condition = Q(status='approved')
    if user.role == 'editor':
        condition |= Q(asset__uploaded_by=user)
    return queryset.filter(condition)


class IsDAMMember(BasePermission):
    def has_permission(self, request, view):
        return active_member(request.user)


class IsDAMAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_admin(request.user)


class IsAdminOrReadOnly(IsDAMMember):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.method in SAFE_METHODS or is_admin(request.user))


class AssetPermission(IsDAMMember):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        if request.method == 'DELETE':
            return is_admin(request.user)
        return request.user.role in {'admin', 'editor'}

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return active_member(request.user)
        return can_edit_asset(request.user, obj)
