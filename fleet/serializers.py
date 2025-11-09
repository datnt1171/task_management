from rest_framework import serializers
from .models import Trip, Stop

class StopSerializer(serializers.ModelSerializer):
    """Serializer for Stop model"""
    # Read-only fields
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)

    class Meta:
        model = Stop
        fields = [
            'id',
            'trip',
            'order',
            'location',
            'odometer',
            'toll_station',
            'created_at',
            'created_by',
            'created_by_name',
            'updated_at',
            'updated_by',
            'updated_by_name',
        ]
        read_only_fields = ['id', 'created_at', 'created_by', 'updated_at', 'updated_by']

    def create(self, validated_data):
        """Override create to set created_by and updated_by"""
        user = self.context['request'].user
        validated_data['created_by'] = user
        validated_data['updated_by'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Override update to set updated_by"""
        validated_data['updated_by'] = self.context['request'].user
        return super().update(instance, validated_data)

    def validate(self, data):
        """
        Validate that odometer reading increases for each subsequent stop
        """
        trip = data.get('trip', getattr(self.instance, 'trip', None))
        order = data.get('order', getattr(self.instance, 'order', None))
        odometer = data.get('odometer', getattr(self.instance, 'odometer', None))

        # Validate odometer increases
        if trip and odometer is not None and order is not None:
            # Check previous stop
            previous_stops = Stop.objects.filter(trip=trip, order__lt=order)
            if self.instance:
                previous_stops = previous_stops.exclude(pk=self.instance.pk)
            
            previous_stop = previous_stops.order_by('-order').first()
            if previous_stop and odometer <= previous_stop.odometer:
                raise serializers.ValidationError({
                    'odometer': f'Odometer reading must be greater than previous stop ({previous_stop.odometer} km).'
                })

            # Check next stop
            next_stops = Stop.objects.filter(trip=trip, order__gt=order)
            if self.instance:
                next_stops = next_stops.exclude(pk=self.instance.pk)
            
            next_stop = next_stops.order_by('order').first()
            if next_stop and odometer >= next_stop.odometer:
                raise serializers.ValidationError({
                    'odometer': f'Odometer reading must be less than next stop ({next_stop.odometer} km).'
                })

        return data
    

class TripSerializer(serializers.ModelSerializer):
    """Serializer for Trip model"""
    # Read-only fields that are auto-populated
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    driver_name = serializers.CharField(source='driver.get_full_name', read_only=True)
    stops = StopSerializer(many=True, read_only=True)
    
    # Optional: include stop count
    stops_count = serializers.IntegerField(source='stops.count', read_only=True)

    class Meta:
        model = Trip
        fields = [
            'id',
            'license_plate',
            'driver',
            'driver_name',
            'date',
            'stops_count',
            'created_at',
            'created_by',
            'created_by_name',
            'updated_at',
            'updated_by',
            'updated_by_name',
            'stops',
        ]
        read_only_fields = ['id', 'created_at', 'created_by', 'updated_at', 'updated_by']

    def create(self, validated_data):
        """Override create to set created_by and updated_by"""
        user = self.context['request'].user
        validated_data['created_by'] = user
        validated_data['updated_by'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Override update to set updated_by"""
        validated_data['updated_by'] = self.context['request'].user
        return super().update(instance, validated_data)
    

class TripLogSerializer(serializers.Serializer):
    trip_id = serializers.UUIDField()
    date = serializers.DateField()
    license_plate = serializers.CharField()
    start_loc = serializers.CharField()
    end_loc = serializers.CharField()
    start_odometer = serializers.IntegerField()
    end_odometer = serializers.IntegerField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    toll_station = serializers.CharField()
    username = serializers.CharField()
    distance = serializers.IntegerField()
    duration = serializers.FloatField()