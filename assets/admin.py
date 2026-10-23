from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Asset, Category


# Custom User admin
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {"fields": ("role",)}),
    )
    list_display = ("username", "email", "role", "is_staff", "is_active")


# Custom Asset admin
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("title", "uploaded_by_name", "uploaded_at", "category")

    def uploaded_by_name(self, obj):
        return obj.uploaded_by.username if obj.uploaded_by else "-"
    uploaded_by_name.short_description = "Uploaded By"

    def has_change_permission(self, request, obj=None):
        if not obj:
            return True
        if hasattr(request.user, "role"):
            return request.user.role == "admin" or (
                request.user.role == "editor" and obj.uploaded_by == request.user
            )
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if hasattr(request.user, "role"):
            return request.user.role == "admin"
        return super().has_delete_permission(request, obj)


# Custom Category admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
