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
    supervisor = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'department', 'role', 'supervisor']

    def get_supervisor(self, obj):
        if obj.supervisor:
            return {
                'id': obj.supervisor.id,
                'username': obj.supervisor.username,
                'first_name': obj.supervisor.first_name,
                'last_name': obj.supervisor.last_name,
            }
        return None

class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']
        