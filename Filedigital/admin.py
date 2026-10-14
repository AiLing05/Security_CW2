from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Category,File, FileApproval, OCRData, FileActivityLog, Backup,AccessRequest

admin.site.register(Category)
admin.site.register(File)
admin.site.register(FileApproval)
admin.site.register(OCRData)
admin.site.register(FileActivityLog)
admin.site.register(Backup)

# @admin.register(AccessRequest)
# class AccessRequestAdmin(admin.ModelAdmin):
#     list_display = ('file', 'requester', 'is_approved', 'reviewed_by', 'created_at', 'reviewed_at')
#     list_filter = ('is_approved', 'created_at')
#     search_fields = ('file__name', 'requester__name')

from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from .models import AccessRequest

@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ('file', 'requester', 'is_approved', 'reviewed_by', 'created_at', 'reviewed_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('file__name', 'requester__username')

    def save_model(self, request, obj, form, change):
        # If the request is being approved, send an email
        if obj.is_approved is not None and (not change or obj.is_approved != form.cleaned_data['is_approved']):
            if obj.is_approved:  # Only send email if the request is approved
                self.send_access_notification(obj)
        
        super().save_model(request, obj, form, change)

    def send_access_notification(self, access_request):
        # Email content
        subject = f"Access Request {'Approved' if access_request.is_approved else 'Denied'}"
        message = (
            f"Dear {access_request.requester.username},\n\n"
            f"Your request to access the file '{access_request.file.name}' has been {'approved' if access_request.is_approved else 'denied'}.\n\n"
            f"Thank you for using our service!"
        )

        # Send the email
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,  # Your system's email
            [access_request.requester.email],
            fail_silently=False,
        )
