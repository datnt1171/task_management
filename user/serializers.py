from rest_framework import serializers
from .models import User, Role, Department, RolePermission, UserFactoryOnsite
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name']
        

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class UserDetailSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer()
    role = RoleSerializer()
    supervisor = UserSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 
                  'email', 'department', 'role', 'supervisor', 
                  'is_password_changed']
        
        
class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    re_new_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['re_new_password']:
            raise serializers.ValidationError({"non_field_errors": ["New passwords don't match."]})
        return data

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add user basic info
        token['user_id'] = str(user.id)
        token['username'] = user.username
        
        # Add organizational context
        token['department'] = user.department.name
        token['role'] = user.role.name
        token['business_function'] = user.business_function.name
        
        # Add permissions
        permissions = cls.get_user_permissions(user)
        token['permissions'] = permissions
        
        return token
    
    @classmethod
    def get_user_permissions(cls, user):
        """
        Get all permissions for the user based on their role, department, and business function
        Returns a structured permission object that can be easily consumed by frontend/other services
        """
        # Get all role permissions that match user's context
        role_permissions = RolePermission.objects.filter(
            role=user.role,
            department=user.department,
            business_function=user.business_function
        ).select_related('permission')
        
        no_dept_permissions = RolePermission.objects.filter(
            role=user.role,
            department=user.department,
            business_function__isnull=True
        ).select_related('permission')
        
        no_func_permissions = RolePermission.objects.filter(
            role=user.role,
            department__isnull=True,
            business_function=user.business_function
        ).select_related('permission')
        
        global_permissions = RolePermission.objects.filter(
            role=user.role,
            department__isnull=True,
            business_function__isnull=True
        ).select_related('permission')
        
        # Combine permissions
        all_permissions = list(role_permissions) + list(no_dept_permissions) + list(no_func_permissions) + list(global_permissions)
        
        # Structure permissions for easy consumption
        permissions = []
        
        for rp in all_permissions:
            perm = rp.permission
            entry = f"{perm.action}.{perm.service}.{perm.resource}"
            if entry not in permissions:
                permissions.append(entry)
        
        return permissions
    

class UserFactoryOnsiteSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = UserFactoryOnsite
        fields = ['id', 'user', 'factory', 'year', 'month']
        