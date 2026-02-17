from rest_framework.permissions import BasePermission

from streaming.models import Room


class IsTeacher(BasePermission):
    message = "Only teachers are permitted to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_teacher
        )


class IsStudent(BasePermission):
    message = "Only students are permitted to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_student
        )


class IsRoomHost(BasePermission):
    message = "You are not the host of this room."

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if isinstance(obj, Room):
            return obj.host == request.user
        return False


class IsTeacherOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.is_teacher