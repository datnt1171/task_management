from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import FinishingSheet
from .serializers import FinishingSheetSerializer


class FinishingSheetViewSet(viewsets.ModelViewSet):
    queryset = FinishingSheet.objects.all()
    serializer_class = FinishingSheetSerializer
    
    # Add filtering, searching, and ordering
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['task', 'created_by']
    search_fields = ['finishing_code']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']  # Default ordering
    
    def get_queryset(self):
        """
        Optionally restricts the returned finishing sheets,
        by filtering against query parameters in the URL.
        """
        queryset = FinishingSheet.objects.all()
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
            
        return queryset
    
    def perform_create(self, serializer):
        """
        Automatically set the created_by field to the current user
        """
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
        serializer.save()