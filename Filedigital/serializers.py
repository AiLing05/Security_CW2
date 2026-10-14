from rest_framework import serializers
from .models import File, Category, FileApproval, OCRData, FileActivityLog,Notification

from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
User = get_user_model()

from .models import File, Category, FileApproval, OCRData, FileActivityLog,Notification,AccessRequest
class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        exclude = ['uploaded_by']


class AccessRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRequest
        fields = '__all__'
        read_only_fields = ['is_approved', 'reviewed_by', 'reviewed_at', 'created_at', 'requester']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class FileApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileApproval
        fields = '__all__'
        read_only_fields = ['request_date', 'decision_date']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter only users in 'Admin' or 'Manager' groups
        allowed_groups = Group.objects.filter(name__in=["Admin", "Manager"])
        allowed_users = User.objects.filter(groups__in=allowed_groups).distinct()
        self.fields['approver'].queryset = allowed_users



class OCRDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = OCRData
        fields = '__all__'

class FileActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileActivityLog
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        ordering = ['-created_at']