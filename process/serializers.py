from rest_framework import serializers
from .models import Process, ProcessField, Action

class ProcessFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessField
        fields = ['id', 'name', 'description', 'field_type', 'order', 'required', 'options']


class ProcessDetailSerializer(serializers.ModelSerializer):
    fields = ProcessFieldSerializer(many=True, read_only=True)

    class Meta:
        model = Process
        fields = ['id', 'name', 'description', 'version', 'fields']


class ProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Process
        fields = ['id', 'name', 'description', 'version']
        

class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = ['id','name','description','action_type']