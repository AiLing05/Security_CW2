from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.forms import ModelForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth.models import Group
from django.utils import timezone
from users.models import User
from Filedigital.models import File, Category, FileApproval, FileActivityLog, AccessRequest


class ProfileForm(ModelForm):
    class Meta:
        model = User
        fields = ["name", "phone", "location"]




def is_manager(user):
    return user.is_staff or user.is_superuser or user.groups.filter(name__in=['Admin', 'Manager']).exists()


def visible_files(user):
    if is_manager(user):
        return File.objects.all()
    approved_access = AccessRequest.objects.filter(requester=user, is_approved=True).values('file_id')
    return File.objects.filter(Q(uploaded_by=user) | Q(file_type='public', is_approved=True) | Q(pk__in=approved_access)).distinct()


def signin(request):
    if request.user.is_authenticated:
        return redirect('frontend:dashboard')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return redirect('frontend:dashboard')
        messages.error(request, 'Invalid email or password.')
    return render(request, 'frontend/auth.html', {'mode': 'login'})


def signup(request):
    if request.user.is_authenticated:
        return redirect('frontend:dashboard')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        if password != request.POST.get('confirm_password'):
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Registration could not be completed with those details.')
        else:
            try:
                validate_password(password)
                role, _ = Group.objects.get_or_create(name='User')
                user = User.objects.create_user(email=email, password=password,
                    name=request.POST.get('name', '').strip(),
                    phone=request.POST.get('phone', '').strip(),
                    location=request.POST.get('location', '').strip(), role=role)
                user.groups.add(role)
                login(request, user)
                return redirect('frontend:dashboard')
            except (ValidationError, IntegrityError, ValueError) as exc:
                messages.error(request, '; '.join(getattr(exc, 'messages', [str(exc)])))
    return render(request, 'frontend/auth.html', {'mode': 'register'})


@login_required(login_url='frontend:login')
def dashboard(request):
    files = visible_files(request.user)
    recent = files.order_by('-added_date')[:6]
    logs = FileActivityLog.objects.filter(user=request.user).order_by('-timestamp')[:5]
    return render(request, 'frontend/app.html', {'page': 'dashboard', 'files': recent,
        'total_files': files.count(), 'my_uploads': File.objects.filter(uploaded_by=request.user).count(),
        'pending': FileApproval.objects.filter(status='pending').count() if is_manager(request.user) else AccessRequest.objects.filter(requester=request.user, is_approved__isnull=True).count(),
        'logs': logs, 'manager': is_manager(request.user)})


@login_required(login_url='frontend:login')
def documents(request):
    files = visible_files(request.user).select_related('category', 'uploaded_by').order_by('-added_date')
    search = request.GET.get('q', '').strip()
    if search:
        files = files.filter(Q(name__icontains=search) | Q(category__name__icontains=search))
    category = request.GET.get('category', '')
    if category.isdigit():
        files = files.filter(category_id=int(category))
    return render(request, 'frontend/app.html', {'page': 'documents', 'files': files,
        'categories': Category.objects.order_by('name'), 'query': search, 'category_filter': category,
        'manager': is_manager(request.user)})


@login_required(login_url='frontend:login')
def upload(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        name = request.POST.get('name', '').strip()
        if not file or not name:
            messages.error(request, 'A name and a file are required.')
        elif file.size > 10 * 1024 * 1024:
            messages.error(request, 'The file must be 10 MB or smaller.')
        elif not file.name.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.docx', '.xlsx', '.txt')):
            messages.error(request, 'Unsupported file type. Use PDF, images, DOCX, XLSX or TXT.')
        else:
            try:
                obj = File.objects.create(name=name, file=file, uploaded_by=request.user,
                    file_type=request.POST.get('file_type') if request.POST.get('file_type') in ('private', 'public') else 'private')
                FileActivityLog.objects.create(file=obj, user=request.user, action='upload', notes='Uploaded through web portal')
                messages.success(request, 'Document uploaded successfully. Approval may be required before sharing.')
                return redirect('frontend:documents')
            except (ValidationError, IntegrityError, ValueError):
                messages.error(request, 'Upload could not be completed. Check the name and file.')
    return render(request, 'frontend/app.html', {'page': 'upload', 'manager': is_manager(request.user)})


@login_required(login_url='frontend:login')
def download(request, pk):
    obj = get_object_or_404(visible_files(request.user), pk=pk)
    if not obj.file:
        raise Http404('File not found')
    try:
        handle = obj.file.open('rb')
    except OSError:
        raise Http404('File is unavailable')
    FileActivityLog.objects.create(file=obj, user=request.user, action='download')
    return FileResponse(handle, as_attachment=True, filename=obj.file.name.rsplit('/', 1)[-1])


@login_required(login_url='frontend:login')
@require_POST
def delete_document(request, pk):
    obj = get_object_or_404(File, pk=pk)
    if obj.uploaded_by_id != request.user.pk and not is_manager(request.user):
        return HttpResponseForbidden('Not permitted')
    obj.delete()
    messages.success(request, 'Document deleted.')
    return redirect('frontend:documents')


@login_required(login_url='frontend:login')
def approvals(request):
    if not is_manager(request.user):
        return HttpResponseForbidden('Approvals require manager permissions.')
    records = FileApproval.objects.select_related('file', 'approver').order_by('-request_date')
    unapproved = File.objects.filter(is_approved=False).order_by('-added_date')
    return render(request, 'frontend/app.html', {'page': 'approvals', 'approvals': records,
        'unapproved': unapproved, 'manager': True})


@login_required(login_url='frontend:login')
@require_POST
def approve_document(request, pk):
    if not is_manager(request.user):
        return HttpResponseForbidden('Not permitted')
    obj = get_object_or_404(File, pk=pk)
    if obj.uploaded_by_id == request.user.pk:
        return HttpResponseForbidden('You cannot review your own document.')
    if request.POST.get('decision') not in ('approve', 'reject'):
        return HttpResponseForbidden('Invalid approval decision.')
    approved = request.POST.get('decision') == 'approve'
    obj.is_approved = approved
    obj.save(update_fields=['is_approved'])
    FileApproval.objects.create(file=obj, approver=request.user, status='approved' if approved else 'rejected', decision_date=timezone.now())
    FileActivityLog.objects.create(file=obj, user=request.user, action='approve' if approved else 'reject')
    messages.success(request, 'Document decision saved.')
    return redirect('frontend:approvals')


@login_required(login_url='frontend:login')
def access_requests(request):
    if request.method == 'POST':
        file = get_object_or_404(File, pk=request.POST.get('file_id'))
        if file.uploaded_by_id == request.user.pk:
            messages.error(request, 'You already own this document.')
        elif AccessRequest.objects.filter(requester=request.user, file=file, is_approved__isnull=True).exists():
            messages.error(request, 'You already have a pending request.')
        else:
            AccessRequest.objects.create(requester=request.user, file=file)
            messages.success(request, 'Access request submitted.')
        return redirect('frontend:access')
    requests = AccessRequest.objects.select_related('file', 'requester').order_by('-created_at')
    if not is_manager(request.user):
        requests = requests.filter(requester=request.user)
    eligible = File.objects.exclude(uploaded_by=request.user).filter(file_type='private')
    return render(request, 'frontend/app.html', {'page': 'access', 'requests': requests,
        'eligible': eligible, 'manager': is_manager(request.user)})


@login_required(login_url='frontend:login')
@require_POST
def review_access(request, pk):
    if not is_manager(request.user):
        return HttpResponseForbidden('Not permitted')
    obj = get_object_or_404(AccessRequest, pk=pk)
    obj.is_approved = request.POST.get('decision') == 'approve'
    obj.reviewed_by = request.user
    obj.reviewed_at = timezone.now()
    obj.save()
    messages.success(request, 'Access request reviewed.')
    return redirect('frontend:access')


@login_required(login_url='frontend:login')
def activity(request):
    logs = FileActivityLog.objects.select_related('file', 'user').order_by('-timestamp')
    if not is_manager(request.user):
        logs = logs.filter(user=request.user)
    return render(request, 'frontend/app.html', {'page': 'activity', 'logs': logs[:150], 'manager': is_manager(request.user)})


@login_required(login_url='frontend:login')
def reports(request):
    if not is_manager(request.user):
        return HttpResponseForbidden('Reports require manager permissions.')
    from django.db.models import Count
    counts = list(FileActivityLog.objects.values('action').annotate(total=Count('id')).order_by('-total'))
    return render(request, 'frontend/app.html', {'page': 'reports', 'counts': counts,
        'total_files': File.objects.count(), 'total_users': User.objects.count(),
        'pending': File.objects.filter(is_approved=False).count(), 'manager': True})


@login_required(login_url='frontend:login')
def profile(request):
    return render(request, 'frontend/app.html', {'page': 'profile', 'manager': is_manager(request.user)})


@login_required(login_url='frontend:login')
def edit_profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('frontend:profile')
    return render(request, 'frontend/app.html', {
        'page': 'edit_profile', 'form': form, 'manager': is_manager(request.user),
    })


@login_required(login_url='frontend:login')
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password changed successfully.')
        return redirect('frontend:profile')
    return render(request, 'frontend/app.html', {
        'page': 'change_password', 'form': form, 'manager': is_manager(request.user),
    })


@require_POST
def signout(request):
    logout(request)
    return redirect('frontend:login')
