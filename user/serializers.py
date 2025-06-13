from rest_framework import serializers
from .models import User, Role, Department
from drf_spectacular.utils import extend_schema_field

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name']
        

class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class UserDetailSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer()
    role = RoleSerializer()
    supervisor = UserListSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'department', 'role', 'supervisor']
        