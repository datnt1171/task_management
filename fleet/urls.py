from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'trips', views.TripViewSet, basename='trip')
router.register(r'stops', views.StopViewSet, basename='stop')

urlpatterns = [
    path('', include(router.urls)),
    path('trip-logs/', views.TripLogView.as_view(), name='trip-logs')
]