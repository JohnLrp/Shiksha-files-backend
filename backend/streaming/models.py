from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    TEACHER = "teacher", "Teacher"   # can publish audio/video (host)
    STUDENT = "student", "Student"   # view-only subscriber


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Adds a `role` field used server-side to determine LiveKit publishing rights.
    The role is NEVER trusted from the frontend — only from this DB record.
    """

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
    )

    def has_role(self, role_name: str) -> bool:
        """Check role by string name, e.g. user.has_role('teacher')"""
        return self.role == role_name

    @property
    def is_teacher(self) -> bool:
        return self.role == UserRole.TEACHER

    @property
    def is_student(self) -> bool:
        return self.role == UserRole.STUDENT

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Room(models.Model):
    """
    Tracks LiveKit rooms created through the platform.
    The `name` field maps directly to the LiveKit room name in tokens.
    """

    name = models.SlugField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    host = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="hosted_rooms",
        limit_choices_to={"role": UserRole.TEACHER},
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.display_name} ({self.name})"
