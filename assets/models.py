from django.contrib.auth.models import AbstractUser, BaseUserManager  # ✅ ADDED BaseUserManager
from django.db import models
from django.conf import settings


# ----------------------------------------------------------
# Custom User Manager
# ----------------------------------------------------------
class UserManager(BaseUserManager):  # ✅ ADDED
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')  # ✅ Automatically set admin role
        return self.create_user(username, email, password, **extra_fields)


# ----------------------------------------------------------
# User Model
# ----------------------------------------------------------
class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("editor", "Editor"),
        ("viewer", "Viewer"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="viewer")

    objects = UserManager()  # ✅ ADDED custom manager

    def __str__(self):
        return f"{self.username} ({self.role})"

    # Role permissions helpers
    def can_upload(self):
        return self.role in ["admin", "editor"]

    def can_edit(self, asset):
        return self.role == "admin" or (self.role == "editor" and asset.uploaded_by == self)

    def can_view(self):
        return True


# ----------------------------------------------------------
# Category Model
# ----------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# ----------------------------------------------------------
# Tag Model
# ----------------------------------------------------------
class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# ----------------------------------------------------------
# Asset Model
# ----------------------------------------------------------
class Asset(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="assets/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_assets"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_assets"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="assets")
    metadata = models.JSONField(blank=True, null=True)
    version = models.PositiveIntegerField(default=1)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children"
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def latest_version(self):
        """Return the latest approved version for this asset."""
        return self.versions.filter(status="approved").order_by("-version").first()



# ----------------------------------------------------------
# Asset Version Model
# ----------------------------------------------------------
class AssetVersion(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="versions")
    file = models.FileField(upload_to="assets/versions/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    comment = models.TextField(blank=True, null=True)

    # NEW FIELDS for editable metadata
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versioned_assets"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="versioned_assets")

    class Meta:
        ordering = ["-version"]

    def __str__(self):
        return f"{self.asset.title} (v{self.version}) - {self.status}"
