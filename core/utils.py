import os
import mimetypes
from rest_framework import serializers
from core.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE

class FileValidator:
    """Comprehensive file validator for Django REST Framework"""
    
    # MIME type mapping for allowed extensions
    ALLOWED_MIME_TYPES = {
        '.jpg': ['image/jpeg'],
        '.jpeg': ['image/jpeg'],
        '.png': ['image/png'],
        '.pdf': ['application/pdf'],
        '.doc': ['application/msword'],
        '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        '.xls': ['application/vnd.ms-excel'],
        '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    }
    
    def __init__(self, allowed_extensions=ALLOWED_EXTENSIONS, max_size_mb=MAX_FILE_SIZE):
        """
        Initialize file validator
        
        Args:
            allowed_extensions (list): List of allowed file extensions
            max_size_mb (int): Maximum file size in MB
        """
        self.allowed_extensions = allowed_extensions
        self.max_file_size = max_size_mb
    
    def __call__(self, file):
        """Make the class callable for use as a validator"""
        if not file:
            return
        
        self.validate_extension(file)
        self.validate_size(file)
        self.validate_mime_type(file)
    
    def validate_extension(self, file):
        """Validate file extension"""
        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension not in self.allowed_extensions:
            allowed_str = ', '.join(self.allowed_extensions)
            raise serializers.ValidationError(
                f"File extension '{file_extension}' is not allowed. "
                f"Allowed extensions: {allowed_str}"
            )
    
    def validate_size(self, file):
        """Validate file size"""
        if file.size > self.max_file_size:
            size_mb = self.max_file_size / (1024 * 1024)
            current_size_mb = file.size / (1024 * 1024)
            raise serializers.ValidationError(
                f"File size exceeds maximum allowed size of {size_mb}MB. "
                f"Current file size: {current_size_mb:.2f}MB"
            )
    
    def validate_mime_type(self, file):
        """Validate MIME type against file extension"""
        file_extension = os.path.splitext(file.name)[1].lower()
        expected_mime_types = self.ALLOWED_MIME_TYPES.get(file_extension, [])
        
        if not expected_mime_types:
            return  # Skip if extension not in our mapping
        
        # Get MIME type from file content
        file_mime_type = getattr(file, 'content_type', None)
        
        # Fallback to guessing from filename if content_type not available
        if not file_mime_type:
            guessed_type, _ = mimetypes.guess_type(file.name)
            file_mime_type = guessed_type
        
        if file_mime_type not in expected_mime_types:
            raise serializers.ValidationError(
                f"File content doesn't match extension. "
                f"Expected MIME type: {', '.join(expected_mime_types)}, "
                f"but got: {file_mime_type}"
            )