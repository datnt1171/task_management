from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from django.db import models
from .models import Trip, Stop
from .serializers import TripSerializer, StopSerializer, TripLogSerializer
from datetime import datetime

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
        
        user = self.request.user
        # Filter to only trips created by or driven by current user (unless assistant)
        if user.role.name == "assistant" or user.is_staff:
            # Assistants can view all trips
            return queryset
        
        # Non-assistants only see trips they created or drove
        return queryset.filter(
            models.Q(driver=self.request.user) | 
            models.Q(created_by=self.request.user)
        )


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


class TripLogView(APIView):
    
    @extend_schema(
        responses=TripLogSerializer(many=True),
    )
    def get(self, request):
        now = datetime.now()
        month = request.query_params.get('month', now.month)
        year = request.query_params.get('year', now.year)
        license_plate = request.query_params.get('license_plate')
        driver = request.query_params.get('driver')

        # Build the WHERE conditions
        where_conditions = ["end_loc IS NOT NULL"]
        query_params = []
        
        # Add month and year filters
        where_conditions.append("EXTRACT(MONTH FROM date) = %s")
        query_params.append(month)
        where_conditions.append("EXTRACT(YEAR FROM date) = %s")
        query_params.append(year)
        
        # Add license_plate filter (comma-separated list)
        if license_plate:
            plates = [plate.strip() for plate in license_plate.split(',') if plate.strip()]
            if plates:
                placeholders = ','.join(['%s'] * len(plates))
                where_conditions.append(f"license_plate IN ({placeholders})")
                query_params.extend(plates)
        
        # Add driver filter (comma-separated list)
        if driver:
            drivers = [d.strip() for d in driver.split(',') if d.strip()]
            if drivers:
                placeholders = ','.join(['%s'] * len(drivers))
                where_conditions.append(f"username IN ({placeholders})")
                query_params.extend(drivers)
        
        where_clause = " AND ".join(where_conditions)

        with connection.cursor() as cursor:
            cursor.execute(f"""
                WITH trip_data AS (
                    SELECT 
                        ft.id AS trip_id, 
                        ft."date", 
                        ft.license_plate, 
                        fst."order" AS stop_order, 
                        fst."location", 
                        fst.odometer, 
                        fst.created_at, 
                        fst.toll_station, 
                        uu.username
                    FROM fleet_stop fst
                    JOIN fleet_trip ft ON fst.trip_id = ft.id
                    JOIN user_user uu ON ft.driver_id = uu.id
                ),
                trip_segments AS (
                    SELECT
                        trip_id,
                        date,
                        license_plate,
                        location AS start_loc,
                        LEAD(location) OVER (PARTITION BY trip_id ORDER BY stop_order) AS end_loc,
                        odometer AS start_odometer,
                        LEAD(odometer) OVER (PARTITION BY trip_id ORDER BY stop_order) AS end_odometer,
                        created_at AS start_time,
                        LEAD(created_at) OVER (PARTITION BY trip_id ORDER BY stop_order) AS end_time,
                        LEAD(toll_station) OVER (PARTITION BY trip_id ORDER BY stop_order) AS toll_station,
                        username
                    FROM trip_data
                )
                SELECT
                    trip_id,
                    date,
                    license_plate,
                    start_loc,
                    end_loc,
                    start_odometer,
                    end_odometer,
                    start_time,
                    end_time,
                    toll_station,
                    username,
                    (end_odometer - start_odometer) AS distance,
                    (end_time - start_time) AS duration
                FROM trip_segments
                WHERE {where_clause}
                ORDER BY date, license_plate, username, start_time;
            """, query_params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(results, status=status.HTTP_200_OK)
    