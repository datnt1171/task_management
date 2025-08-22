from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from .models import FinishingSheet
from .serializers import FinishingSheetSerializer


class FinishingSheetViewSet(viewsets.ModelViewSet):
    queryset = FinishingSheet.objects.all()
    serializer_class = FinishingSheetSerializer
    permission_classes = [IsAuthenticated]
    
    # Add filtering, searching, and ordering
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['finishing_code', 'created_by']
    search_fields = ['task', 'finishing_code']
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
        """
        You might want to track who updated the record
        """
        # If you have an updated_by field, uncomment the line below
        # serializer.save(updated_by=self.request.user)
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def my_sheets(self, request):
        """
        Custom action to get finishing sheets created by the current user
        URL: /api/finishing-sheets/my_sheets/
        """
        user_sheets = self.get_queryset().filter(created_by=request.user)
        serializer = self.get_serializer(user_sheets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_finishing_code(self, request):
        """
        Custom action to get finishing sheets by finishing code
        URL: /api/finishing-sheets/by_finishing_code/?code=YOUR_CODE
        """
        finishing_code = request.query_params.get('code')
        if not finishing_code:
            return Response(
                {'error': 'finishing_code parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sheets = self.get_queryset().filter(finishing_code=finishing_code)
        serializer = self.get_serializer(sheets, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Custom action to duplicate a finishing sheet
        URL: /api/finishing-sheets/{id}/duplicate/
        """
        original_sheet = self.get_object()
        
        # Create a copy
        new_sheet = FinishingSheet.objects.create(
            task=f"Copy of {original_sheet.task}",
            finishing_code=original_sheet.finishing_code,
            created_by=request.user
        )
        
        serializer = self.get_serializer(new_sheet)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def list(self, request, *args, **kwargs):
        """
        Override list method to add custom response format or logic if needed
        """
        response = super().list(request, *args, **kwargs)
        
        # Add metadata to the response
        response.data = {
            'count': len(response.data),
            'results': response.data
        }
        
        return response