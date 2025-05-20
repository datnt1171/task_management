from rest_framework import serializers
from .models import User, Role, Department


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name']
        

class UserProfileSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer()
    role = RoleSerializer()
    manager = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'department', 'role', 'manager']

    def get_manager(self, obj):
        if obj.manager:
            return {
                'id': obj.manager.id,
                'username': obj.manager.username,
                'first_name': obj.manager.first_name,
                'last_name': obj.manager.last_name,
            }
        return None

class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']
        