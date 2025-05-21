from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Document(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="uploaded_documents")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to="documents/versions/")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("document", "version_number")
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.document.title} - v{self.version_number}"


class DocumentSigner(models.Model):
    """
    Who is allowed to sign a document version.
    """
    version = models.ForeignKey(DocumentVersion, on_delete=models.CASCADE, related_name="allowed_signers")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField(default=1)  # If signing should be sequential
    required = models.BooleanField(default=True)         # Optional signing logic

    class Meta:
        unique_together = ("version", "user")
        ordering = ["order"]

    def __str__(self):
        return f"{self.user} allowed to sign {self.version}"


class DocumentSignature(models.Model):
    version = models.ForeignKey(DocumentVersion, on_delete=models.CASCADE, related_name="signatures")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    signed_at = models.DateTimeField(auto_now_add=True)
    signature_file = models.ImageField(upload_to="signatures/")  # base64 or PNG
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ("version", "user")
        ordering = ["signed_at"]

    def __str__(self):
        return f"{self.user} signed {self.version} at {self.signed_at.strftime('%Y-%m-%d %H:%M')}"