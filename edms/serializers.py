from rest_framework import serializers
from .models import Document, DocumentVersion, DocumentSigner, DocumentSignature
from django.contrib.auth import get_user_model

User = get_user_model()


class DocumentSignatureSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = DocumentSignature
        fields = ['id', 'user', 'signed_at', 'signature_file', 'comment']


class DocumentSignerSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = DocumentSigner
        fields = ['id', 'user', 'order', 'required']


class DocumentVersionSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField()
    signatures = DocumentSignatureSerializer(many=True, read_only=True)
    allowed_signers = DocumentSignerSerializer(many=True, read_only=True)

    class Meta:
        model = DocumentVersion
        fields = ['id', 'version_number', 'file', 'uploaded_by', 'uploaded_at', 'notes', 'signatures', 'allowed_signers']


class DocumentListSerializer(serializers.ModelSerializer):
    versions = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'title', 'description', 'created_by', 'created_at', 'versions']

    def get_versions(self, obj):
        latest = obj.versions.order_by('-version_number').first()
        return DocumentVersionSerializer(latest).data if latest else None


class DocumentDetailSerializer(serializers.ModelSerializer):
    versions = DocumentVersionSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Document
        fields = ['id', 'title', 'description', 'created_by', 'created_at', 'versions']


class SignDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentSignature
        fields = ['version', 'signature_file', 'comment']

    def validate(self, data):
        user = self.context['request'].user
        version = data['version']

        # Check if user is allowed signer
        if not DocumentSigner.objects.filter(version=version, user=user).exists():
            raise serializers.ValidationError("You are not allowed to sign this document.")

        # Check if already signed
        if DocumentSignature.objects.filter(version=version, user=user).exists():
            raise serializers.ValidationError("You have already signed this document.")

        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
