import uuid
from django.db import models
from user.models import User
from django.core.validators import FileExtensionValidator


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    version_number = models.PositiveIntegerField()
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='documents'
    )
    file = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    file_size = models.PositiveIntegerField(null=True, blank=True)  # In bytes
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('category', 'version_number')

    def save(self, *args, **kwargs):
        # Automatically set file_size when saving
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class SignatureRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='signature_requests'
    )
    signer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='signature_requests'
    )
    page_number = models.PositiveIntegerField(default=1)  # Page in PDF where signature is placed
    x_position = models.FloatField()  # X-coordinate of signature box (in points or pixels, depending on frontend)
    y_position = models.FloatField()  # Y-coordinate of signature box
    width = models.FloatField()  # Width of signature box
    height = models.FloatField()  # Height of signature box
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('document', 'signer', 'page_number', 'x_position', 'y_position')  # Prevent duplicate signature requests

    def __str__(self):
        return f"Signature request for {self.document.title} by {self.signer.username}"


class SignatureLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='signature_logs'
    )
    signer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='signature_logs'
    )
    signature_file = models.FileField(
        upload_to='signatures/%Y/%m/%d/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg'])]
    )
    signed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # For audit trail
    signature_request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )

    def __str__(self):
        return f"{self.signer.username} signed {self.document.title} at {self.signed_at}"