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
        

class UserSerializer(serializers.ModelSerializer):
    
    department = DepartmentSerializer()
    role = RoleSerializer()

    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'department', 'role']
        