from rest_framework import serializers
from .models import Category, Document, SignatureRequest, SignatureLog
from user.models import User


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'code']


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'title', 'description', 'version_number', 'file', 'file_size', 'created_at']


class DocumentVersionSerializer(serializers.ModelSerializer):
    signature_logs = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Document
        fields = ['id', 'title', 'version_number', 'file', 'signature_logs', 'created_at']


class SignatureRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignatureRequest
        fields = ['signer', 'page_number', 'x_position', 'y_position', 'width', 'height']


class SignatureLogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignatureLog
        fields = ['signature_file']
