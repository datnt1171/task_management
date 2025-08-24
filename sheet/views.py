from rest_framework import viewsets, generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import FinishingSheet, StepTemplate, FormularTemplate
from .serializers import FinishingSheetSerializer, StepTemplateSerializer, FormularTemplateSerializer

class StepTemplateListView(generics.ListAPIView):
    queryset = StepTemplate.objects.all()
    serializer_class = StepTemplateSerializer


class FormularTemplateListView(generics.ListAPIView):
    queryset = FormularTemplate.objects.all()
    serializer_class = FormularTemplateSerializer


class FinishingSheetViewSet(viewsets.ModelViewSet):
    queryset = FinishingSheet.objects.all()
    serializer_class = FinishingSheetSerializer
    
    # Add filtering, searching, and ordering
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['task', 'created_by']
    search_fields = ['finishing_code', 'name']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = FinishingSheet.objects.select_related(
            'task', 'created_by', 'updated_by'
        ).prefetch_related(
            'rows__step_template',
            'rows__formular_template', 
            'rows__created_by',
            'rows__updated_by',
            'rows__products__created_by',
            'rows__products__updated_by'
        )
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
            
        return queryset