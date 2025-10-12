from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register('devices', FCMDeviceAuthorizedViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('send/', views.send_notification_to_self, name='send-notification'),
]