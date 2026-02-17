from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from streaming.models import Room, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Extends default UserAdmin to show and edit the `role` field."""

    list_display = ["username", "email", "role", "is_staff", "is_active"]
    list_filter = ["role", "is_staff", "is_active"]
    fieldsets = UserAdmin.fieldsets + (
        ("LiveKit Role", {"fields": ("role",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("LiveKit Role", {"fields": ("role",)}),
    )


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["display_name", "name", "host", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "display_name", "host__username"]
    prepopulated_fields = {"name": ("display_name",)}
