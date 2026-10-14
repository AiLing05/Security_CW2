from django.shortcuts import render
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
from PIL import Image
from pdf2image import convert_from_path
from django.contrib.postgres.search import SearchVector, SearchQuery
from rest_framework import viewsets,status
from .models import File, Category, FileApproval, OCRData, FileActivityLog, Backup
from .serializers import (FileSerializer,CategorySerializer,FileApprovalSerializer,  OCRDataSerializer, FileActivityLogSerializer)
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .permissions import *
import logging
from django.db.models import Q, Count
from django.utils.dateparse import parse_date
import json
from rest_framework.filters import SearchFilter

import threading
import time

logger = logging.getLogger(__name__)

from datetime import timedelta
from django.utils import timezone
from django.utils.timezone import now

from django.core.mail import send_mail
from django.conf import settings
from users.models import User
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
import json
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.views.decorators.cache import cache_page
from django.core.cache import cache

import cv2
import numpy as np
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from rest_framework.response import Response
from datetime import datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.timezone import now
from django.http import JsonResponse
from .models import File, AccessRequest
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.utils.timezone import now
from .models import AccessRequest
from .serializers import AccessRequestSerializer

from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser


from docx import Document 
from pptx import Presentation 
import pandas as pd
logger = logging.getLogger(__name__)



def get_or_set_cache(cache_key, queryset, serializer_class, timeout=60*15, force_refresh=False):
    """
    Fetch data from cache or set cache if not available.
    If data is not found in cache, it is fetched from the database
    and cached for subsequent requests.
    """
    if force_refresh:
        cache.delete(cache_key)  

    data = cache.get(cache_key)

    if data is None:
        print(f"Fetching {cache_key} from Database...")
        serialized_data = serializer_class(queryset, many=True).data
        cache.set(cache_key, json.dumps(serialized_data), timeout)
        print(f"Cache set for {cache_key}")
        return serialized_data
    else:
        print(f"Fetching {cache_key} from Cache...")
        return json.loads(data)

def invalidate_cache(cache_key):
    """
    Invalidate a specific cache key.
    """
    cache.delete(cache_key)
    print(f"Cache invalidated for key: {cache_key}")

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser

class AccessRequestViewSet(viewsets.ModelViewSet):
    queryset = AccessRequest.objects.all()
    serializer_class = AccessRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return AccessRequest.objects.all()
        return AccessRequest.objects.filter(requester=user)

    def perform_create(self, serializer):
        access_request = serializer.save(requester=self.request.user)
        self.send_submission_notification(access_request)  # ⬅️ Send email on submission

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def review(self, request, pk=None):
        access_request = self.get_object()
        approve = request.data.get('is_approved')

        if approve is None:
            return Response({'error': 'Please provide is_approved field (true/false).'}, status=400)

        access_request.is_approved = approve
        access_request.reviewed_by = request.user
        access_request.reviewed_at = timezone.now()
        access_request.save()

        # If approved, update the file's approval status
        if approve and access_request.file:
            file = access_request.file
            file.is_approved = True
            file.save()

        self.send_review_notification(access_request)  # ⬅️ Send email on approval/rejection

        return Response(AccessRequestSerializer(access_request).data, status=status.HTTP_200_OK)

    def send_submission_notification(self, access_request):
        subject = "Access Request Submitted"
        message = (
            f"Hello {access_request.requester.get_full_name()},\n\n"
            f"Your request to access the file '{access_request.file.name}' has been submitted for review.\n"
            f"You will be notified once it is reviewed.\n\nThank you."
        )
        self.send_email(access_request.requester.email, subject, message)

    def send_review_notification(self, access_request):
        subject = f"Access Request {'Approved' if access_request.is_approved else 'Denied'}"
        message = (
            f"Hello {access_request.requester.get_full_name()},\n\n"
            f"Your request to access the file '{access_request.file.name}' has been "
            f"{'approved' if access_request.is_approved else 'denied'} by {access_request.reviewed_by.get_full_name()}.\n\n"
            f"Thank you."
        )
        self.send_email(access_request.requester.email, subject, message)

    def send_email(self, to_email, subject, message):
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [to_email],
                fail_silently=False
            )
        except Exception as e:
            # Log the exception (optional: logger.error(f"Email failed: {e}"))
            print(f"Email send failed: {e}")




from .models import File, Backup
from .utils import encrypt_file
import os
from .utils import decrypt_file
from django.core.files.base import ContentFile
from rest_framework.permissions import DjangoModelPermissions

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Count
# from .models import FileActivityLog



CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)

class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer 
    permission_classes = [DjangoModelPermissions]
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['category__id']

    @action(detail=False, methods=['get'], url_path='search')
    def search_files(self, request):
        query = request.GET.get("query", "") or request.GET.get("q", "")
        category = request.GET.get("category")
        date = request.GET.get("date")

        # Construct a cache key based on search parameters
        cache_key = f"search:{query}:{category}:{date}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        filters = Q()

        # Search by query (name, OCR text, or file extension)
        if query:
            filters &= (
                Q(name__icontains=query) |  # Case-insensitive partial match for name
                Q(ocrdata__extracted_text__icontains=query) |  # OCR text match
                Q(file__iendswith=f".{query.lower()}")  # Match file extension
            )

       
        if category:
            filters &= Q(category__id=category)  # Directly filter by category ID

  
        if date:
            try:
                parsed_date = datetime.strptime(date, '%Y-%m-%d').date()
                filters &= Q(added_date__date=parsed_date)
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)


        results = File.objects.filter(filters, is_approved=True).annotate(
            popularity=Count('fileactivitylog')
        ).order_by('-popularity', '-added_date')

        serializer = self.get_serializer(results, many=True)


        cache.set(cache_key, json.dumps(serializer.data), timeout=60 * 5)

        return Response(serializer.data)

    def list(self, request):
            cache_key = 'file_list'

            # 1. Try to get data from cache
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                print(f"✅ Fetching '{cache_key}' from Cache...")
                return Response(json.loads(cached_data))

            # 2. If cache miss, get data from DB
            print(f"❌ '{cache_key}' not found in cache. Fetching from DB...")
            queryset = File.objects.all()
            serializer = FileSerializer(queryset, many=True)
            data = serializer.data

            # 3. Store data in cache for 15 minutes (or any desired time)
            cache.set(cache_key, json.dumps(data), timeout=60 * 15)
            print(f"📦 Stored '{cache_key}' in cache.")

            return Response(data)
    def retrieve(self, request, *args, **kwargs):
        cache_key = f"File{kwargs.get('pk')}"
        return Response(get_or_set_cache(cache_key, File.objects.filter(pk=kwargs.get('pk')), self.serializer_class))

    def perform_create(self, serializer):
        user = self.request.user  
        file_instance = serializer.save(uploaded_by=user)  
        invalidate_cache("all_files")
        
        # Log file upload activity
        FileActivityLog.objects.create(
            file=file_instance,
            user=user,
            action='upload',
            notes='File uploaded via API'
        )

        # ✅ Create Backup
        Backup.objects.create(
            file=file_instance.file,
            name=file_instance.name,
            category=file_instance.category,
            file_type=file_instance.file_type,
            is_approved=file_instance.is_approved,
            uploaded_by=user
        )
        
        # 🔥 Auto-create a FileApproval and send mail manually
        approver = User.objects.filter(is_staff=True).exclude(id=user.id).first()
        approval = None
        if approver:
            approval = FileApproval.objects.create(
                file=file_instance,
                approver=approver,
                status='pending'
            )
        
            # ✅ Manually send the email (since perform_create of FileApprovalViewSet isn't triggered)
            if approver.email:
                send_mail(
                    subject='New File Pending Approval',
                    message=f'Dear {approver.get_full_name()},\n\n'
                            f'A file "{file_instance.name}" has been submitted and requires your approval.\n\n'
                            f'Please log in to the system to review it.\n\nThank you.',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[approver.email],
                    fail_silently=True
                )

        # Start background thread for escalation
        if approval:
            threading.Thread(target=escalate_pending_approval_thread, args=(approval.id,), daemon=True).start()
            
        # Run file processing (OCR extraction, etc.) in a background thread
        threading.Thread(target=self.process_file_in_background, args=(file_instance, user), daemon=True).start()
    
    def process_file_in_background(self, file_instance, user):
        file_path = file_instance.file.path
        extracted_text = ""
        try:
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                image = cv2.imread(file_path)
                image = self.preprocess_image(image)
                extracted_text = pytesseract.image_to_string(image)

            elif file_path.lower().endswith('.pdf'):
                images = convert_from_path(file_path)
                for image in images:
                    image = np.array(image)
                    image = self.preprocess_image(image)
                    extracted_text += pytesseract.image_to_string(image) + "\n"

            elif file_path.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    extracted_text = f.read()

            elif file_path.lower().endswith('.docx'):
                doc = Document(file_path)
                for para in doc.paragraphs:
                    extracted_text += para.text + "\n"

            elif file_path.lower().endswith('.pptx'):
                prs = Presentation(file_path)
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            extracted_text += shape.text + "\n"

            elif file_path.lower().endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path)
                extracted_text = df.to_string()

            elif file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
                extracted_text = df.to_string()

            # If OCR text is extracted, save it to the OCRData model
            if extracted_text:
                OCRData.objects.create(file=file_instance, extracted_text=extracted_text)
                logger.info(f"OCRData successfully created for file: {file_instance.name}")
            else:
                logger.warning(f"OCR extraction failed: No text found in {file_instance.name}")

        except Exception as e:
            logger.error(f"OCR Extraction Error: {e}")
    
    def preprocess_image(self, image):
        """Enhances the image before OCR."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh
        
    def backup_and_notify(self, file_instance, user):    
        """Handles backup and email notification after file upload."""
        # Encrypt the content and backup logic (as before)
        with open(file_instance.file.path, 'rb') as f:
            raw_data = f.read()
        
        # Encrypt the content
        encrypted_data = encrypt_file(raw_data)
        
        # Set backup path
        backup_filename = f"{file_instance.name}.enc"
        backup_path = os.path.join(settings.MEDIA_ROOT, 'backup_documents', backup_filename)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Save encrypted file
        with open(backup_path, 'wb') as f:
            f.write(encrypted_data)
    
    @action(detail=True, methods=['GET'], permission_classes=[IsOwnerOrAdmin])
    def get_ocr_text(self, request, pk=None):
        try:
            ocr_data = OCRData.objects.get(file_id=pk)
            return Response({"file_id": pk, "extracted_text": ocr_data.extracted_text})
        except OCRData.DoesNotExist:
            try:
                file_instance = self.get_object()
                file_path = file_instance.file.path
                extracted_text = ""

                if file_path.lower().endswith('.pdf'):
                    images = convert_from_path(file_path, dpi=300, poppler_path=r"C:\poppler-24.08.0\Library\bin")
                    for img in images:
                        extracted_text += pytesseract.image_to_string(img) + "\n"

                elif file_path.lower().endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        extracted_text = f.read()

                elif file_path.lower().endswith('.docx'):
                    doc = Document(file_path)
                    for para in doc.paragraphs:
                        extracted_text += para.text + "\n"

                elif file_path.lower().endswith('.pptx'):
                    prs = Presentation(file_path)
                    for slide in prs.slides:
                        for shape in slide.shapes:
                            if hasattr(shape, "text"):
                                extracted_text += shape.text + "\n"

                elif file_path.lower().endswith('.xls') or file_path.lower().endswith('.xlsx'):
                    df = pd.read_excel(file_path)
                    extracted_text = df.to_string()

                elif file_path.lower().endswith('.csv'):
                    df = pd.read_csv(file_path)
                    extracted_text = df.to_string()

                OCRData.objects.create(file=file_instance, extracted_text=extracted_text)
                return Response({"file_id": pk, "extracted_text": extracted_text})
            except Exception as e:
                logger.error(f"❌ Error during OCR extraction: {e}")
                return Response({"error": "OCR extraction failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        @action(detail=True, methods=['POST'], permission_classes=[IsOwnerOrAdmin])
        def restore(self, request, pk=None):
            """Restores a file from backup"""
            try:
                backup_instance = Backup.objects.get(pk=pk)

                # Prevent restoring if the file already exists
                if File.objects.filter(file=backup_instance.file, uploaded_by=backup_instance.uploaded_by).exists():
                    return Response(
                        {"error": "This file has already been restored."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Path to the backup file
                backup_path = backup_instance.file.path
                # Read and decrypt file
                try:
                    with open(backup_path, 'rb') as f:
                       encrypted_data = f.read()

                    decrypted_data = decrypt_file(encrypted_data)
                except Exception as e:
                    return Response({"error": f"Failed to decrypt file: {str(e)}"}, status=500)

                # Create new file
                content_file = ContentFile(decrypted_data, name=backup_instance.name)

                # Restore the file
                restored_file = File.objects.create(
                    file=backup_instance.file,
                    name=backup_instance.name,
                    added_date=backup_instance.added_date,
                    category=backup_instance.category,
                    file_type=backup_instance.file_type,
                    is_approved=backup_instance.is_approved,
                    uploaded_by=backup_instance.uploaded_by
                )

                return Response(
                    {"message": "File restored successfully", "file_id": restored_file.id},
                    status=status.HTTP_201_CREATED
                )

            except Backup.DoesNotExist:
                return Response({"error": "Backup file not found"}, status=status.HTTP_404_NOT_FOUND)  

    # @action(detail=True, methods=['GET'], permission_classes=[IsOwnerOrAdmin])
    # def get_ocr_text(self, request, pk=None):
    #         """API endpoint to retrieve OCR text for a file"""
    #         try:
    #             ocr_data = OCRData.objects.get(file_id=pk)
    #             return Response({"file_id": pk, "extracted_text": ocr_data.extracted_text})
    #         except OCRData.DoesNotExist:
    #             try:
    #                 file_instance = self.get_object()
    #                 file_path = file_instance.file.path
    #                 extracted_text = ""

    #                 if file_path.lower().endswith('.pdf'):
    #                     images = convert_from_path(file_path, dpi=300, poppler_path=r"C:\poppler-24.08.0\Library\bin")
    #                     for img in images:
    #                         extracted_text += pytesseract.image_to_string(img) + "\n"
    #                 else:
    #                     image = Image.open(file_path)
    #                     extracted_text = pytesseract.image_to_string(image)

    #                 # Save it in the OCRData model for next time
    #                 OCRData.objects.create(file=file_instance, extracted_text=extracted_text)

    #                 return Response({"file_id": pk, "extracted_text": extracted_text})
    #             except Exception as e:
    #                 return Response({"error": f"OCR extraction failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
            
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [DjangoModelPermissions]

    def list(self, request, *args, **kwargs):
        cached_data = cache.get('category_list')
        if cached_data:
            print("✅ Serving from cache: category list")
            return Response(cached_data)

        print("❌ 'category_list' not found in cache. Fetching from DB...")
        response = super().list(request, *args, **kwargs)
        cache.set('category_list', response.data, timeout=60 * 15)
        print("📦 Stored 'category_list' in cache.")
        return response

class FileApprovalViewSet(viewsets.ModelViewSet):
    queryset = FileApproval.objects.all()
    serializer_class = FileApprovalSerializer
    permission_classes = [DjangoModelPermissions]
    
    
# def get_renderers(self):
#     user = self.request.user
#     if user.groups.filter(name='Viewer').exists():
#         return [JSONRenderer()]  # Must return at least one renderer to avoid crash
#     return [JSONRenderer(), BrowsableAPIRenderer()]

#     def dispatch(self, request, *args, **kwargs):
#         if request.user.groups.filter(name='Viewer').exists():
#             return Response({'detail': 'You do not have permission to access this endpoint.'},
#                             status=status.HTTP_403_FORBIDDEN)
#         return super().dispatch(request, *args, **kwargs)
    

    # def list(self, request, *args, **kwargs):
    #     cached_data = cache.get('file_approval_list')
    #     if cached_data:
    #         print("✅ Serving from cache: file approvals")
    #         return Response(cached_data)

    #     print("❌ 'file_approval_list' not found in cache. Fetching from DB...")
    #     response = super().list(request, *args, **kwargs)
    #     cache.set('file_approval_list', response.data, timeout=60 * 15)
    #     print("📦 Stored 'file_approval_list' in cache.")
    #     return response

    def perform_create(self, serializer):
        approval = serializer.save()

        # Update File's is_approved based on status
        if approval.status == 'approved':
            approval.file.is_approved = True
        else:
            approval.file.is_approved = False
        approval.file.save()

        # Set decision_date if status is not pending
        if approval.status != 'pending':
            approval.decision_date = now()
            approval.save()

        # Log activity
        FileActivityLog.objects.create(
            file=approval.file,
            user=approval.approver,
            action=approval.status,
            notes=approval.notes
        )
            
        # ✅ Notify uploader if file is approved
        if approval.status == 'approved' and approval.file.uploaded_by.email:
            send_mail(
                subject='Your File Has Been Approved',
                message=f'Dear {approval.file.uploaded_by.get_full_name()},\n\n'
                        f'Your file "{approval.file.name}" has been approved by {approval.approver.get_full_name()}.\n\n'
                        f'Thank you for using our service!',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[approval.file.uploaded_by.email],
                fail_silently=True
            )
            
        # ✅ Notify uploader if file is rejected
        if approval.status == 'rejected' and approval.file.uploaded_by.email:
            send_mail(
                subject='Your File Has Been Rejected',
                message=f'Dear,\n\n'
                        f'We regret to inform you that your file "{approval.file.name}" has been rejected.\n\n'
                        f'Please review the feedback from the approver and make necessary changes.\n\n'
                        f'Thank you for using our service!',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[approval.file.uploaded_by.email],
                fail_silently=True
            )

        
        # Escalation setup after 24 hours
        if approval.status == 'pending':
            threading.Thread(target=escalate_pending_approval_thread, args=(approval.id,), daemon=True).start()
        
def escalate_pending_approval_thread(approval_id):
    """Runs in background to check after 24h and escalate if still pending"""
    logger.info(f"🚀 Escalation thread started for approval ID {approval_id}")
    time.sleep(60*60*24)  # 24 hours
    from .models import FileApproval
    try:
        approval = FileApproval.objects.get(id=approval_id)
        logger.info(f"📌 Approval status after wait: {approval.status}")

        if approval.status == 'pending':
            try:
                logger.info(f"📧 Escalation email will be sent to: {settings.EMAIL_HOST_USER}") 
                
                send_mail(
                    subject='Approval Escalation Alert',
                    message=f'File "{approval.file.name}" is still pending approval after 24 hours.',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[settings.EMAIL_HOST_USER],  # Replace as needed
                    fail_silently=False
                )
                logger.info(f"Escalation email sent for file {approval.file.name}")
            except Exception as e:
                logger.error(f"Failed to send escalation email: {e}")
                
    except FileApproval.DoesNotExist:
        logger.error(f"❌ Approval with ID {approval_id} does not exist.")
    

        escalate_pending_approval_thread.apply_async((approval.id,), eta=now() + timedelta(minutes=1))
        




class FileActivityLogViewSet(viewsets.ModelViewSet):
    queryset = FileActivityLog.objects.all()
    serializer_class = FileActivityLogSerializer
    def list(self, request, *args, **kwargs):
            cache_key = 'activity_log_list'

            # Check if the data is cached
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                print("✅ Serving from cache: activity logs")
                return Response(json.loads(cached_data))

            # If not cached, get data from DB
            print("❌ Cache miss. Fetching activity logs from DB...")
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

            # Cache the serialized data for 15 minutes
            cache.set(cache_key, json.dumps(data), timeout=60 * 15)
            print("📦 Activity logs cached.")

            return Response(data)
        
    def retrieve(self, request, *args, **kwargs):
        cache_key = f"File{kwargs.get('pk')}"
        return Response(get_or_set_cache(cache_key, FileActivityLog.objects.filter(pk=kwargs.get('pk')), self.serializer_class))

    def perform_create(self, serializer):
        serializer.save()
 
        invalidate_cache("all_fileactivitylog")

  


# 🗓 Weekly Report Scheduler (Auto-run every 7 days)
def generate_report():
    now = datetime.now()
    last_week = now - timedelta(days=7)

    logs = FileActivityLog.objects.filter(timestamp__range=(last_week, now))

    print(f"[{now}] Weekly report generated with {logs.count()} logs")

    # You can add logic here to:
    # - Save to PDF
    # - Send email to admin
    # - Save to model etc.

    # Schedule next report after 7 days (604800 seconds)
    threading.Timer(604800, generate_report).start()
    


@staff_member_required
def report_data(request):
    report_type = request.GET.get('type')

    if report_type == 'action_counts':
        data = FileActivityLog.objects.values('action').annotate(count=Count('id'))

    elif report_type == 'user_activity':
        data = FileActivityLog.objects.values('user__email').annotate(count=Count('id')).order_by('-count')

    elif report_type == 'file_popularity':
        data = FileActivityLog.objects.exclude(file_isnull=True).values('file_name').annotate(count=Count('id')).order_by('-count')

    elif report_type == 'logins':
        data = FileActivityLog.objects.filter(action='login').values('user__email').annotate(count=Count('id')).order_by('-count')
    
    elif report_type == 'logouts':
        data = FileActivityLog.objects.filter(action='logout').values('user__email').annotate(count=Count('id')).order_by('-count')
        
    elif report_type == 'logouts':
        data = FileActivityLog.objects.filter(action='logout').values('user__email').annotate(count=Count('id')).order_by('-count')

    else:
        return JsonResponse({'error': 'Invalid report type'}, status=400)

    return JsonResponse(
        {'report_type': report_type, 'results': list(data)},
        status=200,
        json_dumps_params={'indent': 2}
    )

