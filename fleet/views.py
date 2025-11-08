from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from .models import Trip, Stop
from .serializers import TripSerializer, StopSerializer


class TripViewSet(viewsets.ModelViewSet):
    
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    
    filterset_fields = {
        'license_plate': ['exact', 'icontains'],
        'driver': ['exact'],
        'date': ['exact', 'gte', 'lte'],
    }
    
    search_fields = ['license_plate', 'driver__first_name', 'driver__last_name']
    
    ordering_fields = ['date', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.select_related('driver', 'created_by', 'updated_by')
        queryset = queryset.prefetch_related('stops')
        
        # Filter to only trips created by or driven by current user
        queryset = queryset.filter(
            models.Q(driver=self.request.user) | 
            models.Q(created_by=self.request.user)
        )
        
        return queryset


class StopViewSet(viewsets.ModelViewSet):

    queryset = Stop.objects.all()
    serializer_class = StopSerializer
    
    # Filtering fields
    filterset_fields = {
        'trip': ['exact'],
        'location': ['exact', 'icontains'],
        'order': ['exact', 'gte', 'lte'],
    }
    
    # Search fields
    search_fields = ['location', 'toll_station']
    
    # Ordering fields
    ordering_fields = ['order', 'created_at', 'odometer']
    ordering = ['order']  # Default ordering

    def get_queryset(self):
        """
        Optimize queries with select_related
        """
        queryset = super().get_queryset()
        queryset = queryset.select_related('trip', 'created_by', 'updated_by')
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Override create to automatically set order if not provided
        """
        if 'order' not in request.data and 'trip' in request.data:
            # Auto-calculate next order number
            trip_id = request.data['trip']
            last_stop = Stop.objects.filter(trip_id=trip_id).order_by('-order').first()
            next_order = (last_stop.order + 1) if last_stop else 1
            
            # Create mutable copy of request data
            data = request.data.copy()
            data['order'] = next_order
            
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
        return super().create(request, *args, **kwargs)
    
    def perform_destroy(self, instance):
        """
        Override destroy to reorder remaining stops after deletion
        """
        trip = instance.trip
        deleted_order = instance.order
        
        # Delete the stop
        instance.delete()
        
        # Reorder all stops with order > deleted_order
        stops_to_reorder = Stop.objects.filter(
            trip=trip,
            order__gt=deleted_order
        ).order_by('order')
        
        # Decrement order for each subsequent stop
        for stop in stops_to_reorder:
            stop.order -= 1
            stop.save(update_fields=['order'])