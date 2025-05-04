from rest_framework import serializers
from task.models import Process, ProcessField

class ProcessFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessField
        fields = ['id', 'name', 'field_type', 'required']


class ProcessSerializer(serializers.ModelSerializer):
    fields = ProcessFieldSerializer(many=True, read_only=True)

    class Meta:
        model = Process
        fields = ['id', 'name', 'fields']