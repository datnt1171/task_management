from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Category, Document, SignatureRequest, SignatureLog
from .serializers import (
    CategorySerializer, DocumentSerializer, DocumentVersionSerializer,
    SignatureRequestCreateSerializer, SignatureLogCreateSerializer
)


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class DocumentListByCategoryView(generics.ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        category = get_object_or_404(Category, pk=self.kwargs['category_id'])
        return category.documents.order_by('-version_number')


class DocumentVersionListView(generics.ListAPIView):
    serializer_class = DocumentVersionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        document = get_object_or_404(Document, pk=self.kwargs['document_id'])
        return Document.objects.filter(title=document.title, category=document.category).order_by('-version_number')


class SignatureRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, document_id):
        document = get_object_or_404(Document, pk=document_id)
        serializer = SignatureRequestCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(document=document)
            return Response({'detail': 'Signature request created.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignDocumentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, document_id):
        document = get_object_or_404(Document, pk=document_id)
        try:
            sig_req = SignatureRequest.objects.get(document=document, signer=request.user)
        except SignatureRequest.DoesNotExist:
            return Response({'detail': 'You are not authorized to sign this document.'}, status=status.HTTP_403_FORBIDDEN)

        if SignatureLog.objects.filter(document=document, signer=request.user).exists():
            return Response({'detail': 'You have already signed this document.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SignatureLogCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                document=document,
                signer=request.user,
                signature_request=sig_req,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response({'detail': 'Document signed successfully.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
