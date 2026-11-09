from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Asset, Category


from .permissions import is_admin


class DAMAdminOnly:
    def has_module_permission(self, request):
        return is_admin(request.user) and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return is_admin(request.user) and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return is_admin(request.user) and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return is_admin(request.user) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return is_admin(request.user) and super().has_delete_permission(request, obj)


# Custom User admin
@admin.register(User)
class UserAdmin(DAMAdminOnly, BaseUserAdmin):
    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser:
            return tuple(fields) + ('is_superuser', 'is_staff', 'groups', 'user_permissions')
        return fields

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (
            obj is None or not obj.is_superuser or request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and (
            obj is None or (obj.pk != request.user.pk and
            (not obj.is_superuser or request.user.is_superuser)))

    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {"fields": ("role",)}),
    )
    list_display = ("username", "email", "role", "is_staff", "is_active")


# Custom Asset admin
@admin.register(Asset)
class AssetAdmin(DAMAdminOnly, admin.ModelAdmin):
    list_display = ("title", "uploaded_by_name", "uploaded_at", "category")

    def uploaded_by_name(self, obj):
        return obj.uploaded_by.username if obj.uploaded_by else "-"
    uploaded_by_name.short_description = "Uploaded By"

# Custom Category admin
@admin.register(Category)
class CategoryAdmin(DAMAdminOnly, admin.ModelAdmin):
    list_display = ("name",)
