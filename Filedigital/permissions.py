from rest_framework import permissions
from . models import AccessRequest
class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allow only the file owner or admin (superuser/staff)
        return request.user.is_staff or obj.uploaded_by == request.user
    
    
def has_file_access(user, file):
    if file.owner == user:
        return True
    return AccessRequest.objects.filter(file=file, requester=user, is_approved=True).exists()    