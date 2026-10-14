from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('name', 'email', 'is_staff', 'is_active', 'role')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('name', 'email')
    ordering = ('name',)

admin.site.register(User, CustomUserAdmin)
