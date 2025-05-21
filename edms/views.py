from rest_framework import generics, permissions
from .models import Document, DocumentSignature
from .serializers import (
    DocumentListSerializer,
    DocumentDetailSerializer,
    SignDocumentSerializer
)


class DocumentListView(generics.ListAPIView):
    queryset = Document.objects.all().prefetch_related('versions')
    serializer_class = DocumentListSerializer
    permission_classes = [permissions.IsAuthenticated]


class DocumentDetailView(generics.RetrieveAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentDetailSerializer
    permission_classes = [permissions.IsAuthenticated]


class SignDocumentView(generics.CreateAPIView):
    serializer_class = SignDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
