from rest_framework import permissions


class IsSecurityAuditor(permissions.BasePermission):
    """
    Least privilege: only users with the DAM role "admin" may read the audit
    trail. Editors and viewers receive 403 (which is itself logged).
    """

    message = "Only administrators can view security audit data."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and getattr(user, "role", "").lower() == "admin"
            and request.method in permissions.SAFE_METHODS
        )
