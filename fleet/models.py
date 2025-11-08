from django.db import models
import uuid
from user.models import User

class Trip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    license_plate = models.CharField(max_length=200)
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='driven_trips')
    date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_trips')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_trips')

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['license_plate', 'driver', 'date'], 
                name='unique_driver_license_plate_date'
            )
        ]


class Stop(models.Model):
    """Each stop/checkpoint during the trip"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='stops')
    order = models.PositiveIntegerField()
    location = models.CharField(max_length=200) # factory_code
    odometer = models.IntegerField()
    toll_station = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_stops')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_stops')
    
    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(
                fields=['trip', 'order'], 
                name='unique_trip_order'
            )
        ]
