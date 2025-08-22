from rest_framework import serializers
from .models import FinishingSheet

class FinishingSheetSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = FinishingSheet
        fields = ('id', 'task', 'created_at', 'created_by', 'updated_at', 'finishing_code')