from rest_framework.permissions import BasePermission

class HasJWTPermission(BasePermission):
    """
    Check if user has required permission in JWT token
    Superusers bypass all permission checks
    """
    
    def __init__(self, required_permission=None):
        self.required_permission = required_permission
    
    def has_permission(self, request, view):
        # Superusers bypass all permission checks
        if request.user.is_superuser:
            return True
            
        # Get required permission from view attribute or constructor
        required_perm = getattr(view, 'required_permission', None) or self.required_permission
        if not required_perm:
            return True  # No specific permission required
        
        # Get permissions from JWT token
        user_permissions = getattr(request.user, 'token_permissions', [])
        return required_perm in user_permissions

# Custom authentication class to extract permissions from JWT
from rest_framework_simplejwt.authentication import JWTAuthentication

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        
        # Superusers don't need token permissions
        if user.is_superuser:
            user.token_permissions = []
            return user
        
        # validated_token contains all custom claims from get_token()
        user.token_permissions = validated_token.get('permissions', [])
        user.token_department = validated_token.get('department')
        user.token_role = validated_token.get('role')
        user.token_business_function = validated_token.get('business_function')
        
        return user